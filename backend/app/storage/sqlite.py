from __future__ import annotations

import functools
import json
import sqlite3
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.storage.base import SUMMARY_COLUMNS, ScanRow, risk_columns

# Append-only: never edit an entry once released, add a new version instead. Version 1 uses
# IF NOT EXISTS so databases created before migrations existed adopt it unchanged.
MIGRATIONS: list[tuple[int, list[str]]] = [
    (
        1,
        [
            """
            CREATE TABLE IF NOT EXISTS scans (
                id TEXT PRIMARY KEY,
                target TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at REAL NOT NULL,
                finished_at REAL,
                result TEXT,
                error TEXT,
                provider TEXT,
                risk_score REAL,
                severity TEXT,
                recommendation TEXT
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_scans_created_at ON scans (created_at DESC)",
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                scan_retention_days REAL
            )
            """,
        ],
    ),
    (
        2,
        [
            """
            CREATE TABLE scan_log_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id TEXT NOT NULL,
                line TEXT NOT NULL
            )
            """,
            "CREATE INDEX idx_scan_log_lines_scan ON scan_log_lines (scan_id, id)",
            "ALTER TABLE scans ADD COLUMN completed_steps INTEGER NOT NULL DEFAULT 0",
        ],
    ),
    (
        3,
        [
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """,
            """
            CREATE TABLE sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            )
            """,
            "CREATE INDEX idx_sessions_user ON sessions (user_id)",
            "ALTER TABLE scans ADD COLUMN owner_id TEXT",
            "CREATE INDEX idx_scans_owner ON scans (owner_id, created_at DESC)",
        ],
    ),
]

def _locked[T](method: Callable[..., T]) -> Callable[..., T]:
    """Serialise access: the one connection is shared with skillspector's worker threads, which
    write log lines while a scan runs."""

    @functools.wraps(method)
    def wrapper(self: SQLiteStore, *args: Any, **kwargs: Any) -> T:
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper


def _to_row(row: sqlite3.Row) -> ScanRow:
    scan = dict(row)
    if scan.get("result") is not None:
        scan["result"] = json.loads(scan["result"])
    return scan


class SQLiteStore:
    def __init__(self, path: str, *, default_retention_days: float | None) -> None:
        db_path = Path(path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._migrate()
        self._conn.execute(
            "INSERT OR IGNORE INTO app_settings (id, scan_retention_days) VALUES (1, ?)",
            (default_retention_days,),
        )
        self._conn.commit()

    def _migrate(self) -> None:
        conn = self._conn
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at REAL NOT NULL)")
        applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
        for version, statements in MIGRATIONS:
            if version in applied:
                continue
            with conn:
                for statement in statements:
                    conn.execute(statement)
                conn.execute("INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)", (version, time.time()))

    @_locked
    def close(self) -> None:
        self._conn.close()

    @_locked
    def insert_scan(
        self, *, id: str, target: str, status: str, created_at: float, provider: str | None, owner_id: str | None = None
    ) -> None:
        self._conn.execute(
            "INSERT INTO scans (id, target, status, created_at, provider, owner_id) VALUES (?, ?, ?, ?, ?, ?)",
            (id, target, status, created_at, provider, owner_id),
        )
        self._conn.commit()

    @_locked
    def update_scan(
        self,
        *,
        id: str,
        status: str,
        finished_at: float | None,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> None:
        self._conn.execute(
            """
            UPDATE scans
            SET status = ?, finished_at = ?, result = ?, error = ?,
                risk_score = ?, severity = ?, recommendation = ?
            WHERE id = ?
            """,
            (
                status,
                finished_at,
                json.dumps(result) if result is not None else None,
                error,
                *risk_columns(result),
                id,
            ),
        )
        self._conn.commit()

    @_locked
    def fail_unfinished_scans(self, *, error: str, finished_at: float) -> int:
        cursor = self._conn.execute(
            "UPDATE scans SET status = 'error', error = ?, finished_at = ? WHERE status IN ('pending', 'running')",
            (error, finished_at),
        )
        self._conn.commit()
        return cursor.rowcount

    @_locked
    def count_active_scans(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM scans WHERE status IN ('pending', 'running')").fetchone()[0]

    @_locked
    def get_scan(self, id: str) -> ScanRow | None:
        row = self._conn.execute("SELECT * FROM scans WHERE id = ?", (id,)).fetchone()
        return _to_row(row) if row is not None else None

    @_locked
    def delete_scan(self, id: str) -> bool:
        cursor = self._conn.execute("DELETE FROM scans WHERE id = ?", (id,))
        self._conn.execute("DELETE FROM scan_log_lines WHERE scan_id = ?", (id,))
        self._conn.commit()
        return cursor.rowcount > 0

    @_locked
    def delete_scans_older_than(self, cutoff: float) -> int:
        # Pending/running scans are still owned by a live job; deleting them would lose the result.
        cursor = self._conn.execute(
            "DELETE FROM scans WHERE created_at < ? AND status NOT IN ('pending', 'running')",
            (cutoff,),
        )
        self._conn.execute("DELETE FROM scan_log_lines WHERE scan_id NOT IN (SELECT id FROM scans)")
        self._conn.commit()
        return cursor.rowcount

    @_locked
    def get_retention_days(self) -> float | None:
        row = self._conn.execute("SELECT scan_retention_days FROM app_settings WHERE id = 1").fetchone()
        return row["scan_retention_days"] if row else None

    @_locked
    def set_retention_days(self, value: float | None) -> None:
        self._conn.execute("UPDATE app_settings SET scan_retention_days = ? WHERE id = 1", (value,))
        self._conn.commit()

    @_locked
    def list_scans(self, limit: int, offset: int, *, owner_id: str | None = None) -> tuple[list[ScanRow], int]:
        where, params = ("WHERE owner_id = ?", (owner_id,)) if owner_id is not None else ("", ())
        rows = self._conn.execute(
            f"SELECT {SUMMARY_COLUMNS} FROM scans {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
        total = self._conn.execute(f"SELECT COUNT(*) FROM scans {where}", params).fetchone()[0]
        return [dict(row) for row in rows], total

    @_locked
    def append_log_line(self, scan_id: str, line: str, *, keep: int) -> None:
        self._conn.execute("INSERT INTO scan_log_lines (scan_id, line) VALUES (?, ?)", (scan_id, line))
        # Keep only the newest `keep` lines of this scan.
        self._conn.execute(
            """
            DELETE FROM scan_log_lines
            WHERE scan_id = ? AND id <= (
                SELECT id FROM scan_log_lines WHERE scan_id = ? ORDER BY id DESC LIMIT 1 OFFSET ?
            )
            """,
            (scan_id, scan_id, keep),
        )
        self._conn.commit()

    @_locked
    def get_log_lines(self, scan_id: str) -> list[str]:
        rows = self._conn.execute("SELECT line FROM scan_log_lines WHERE scan_id = ? ORDER BY id", (scan_id,))
        return [row["line"] for row in rows]

    @_locked
    def increment_progress(self, scan_id: str) -> None:
        self._conn.execute("UPDATE scans SET completed_steps = completed_steps + 1 WHERE id = ?", (scan_id,))
        self._conn.commit()

    @_locked
    def get_progress(self, scan_id: str) -> int:
        row = self._conn.execute("SELECT completed_steps FROM scans WHERE id = ?", (scan_id,)).fetchone()
        return row["completed_steps"] if row else 0

    @_locked
    def clear_logs(self, scan_id: str) -> None:
        self._conn.execute("DELETE FROM scan_log_lines WHERE scan_id = ?", (scan_id,))
        self._conn.execute("UPDATE scans SET completed_steps = 0 WHERE id = ?", (scan_id,))
        self._conn.commit()

    # Accounts (app/auth). Emails are stored lower-cased by the caller.

    @_locked
    def create_user(self, *, id: str, email: str, password_hash: str, role: str, created_at: float) -> None:
        self._conn.execute(
            "INSERT INTO users (id, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (id, email, password_hash, role, created_at),
        )
        self._conn.commit()

    @_locked
    def create_first_user(self, *, id: str, email: str, password_hash: str, role: str, created_at: float) -> bool:
        """Create the account only if none exists yet; False when another request got there first."""
        cursor = self._conn.execute(
            """
            INSERT INTO users (id, email, password_hash, role, created_at)
            SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM users)
            """,
            (id, email, password_hash, role, created_at),
        )
        self._conn.commit()
        return cursor.rowcount == 1

    @_locked
    def get_user(self, id: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()
        return dict(row) if row else None

    @_locked
    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None

    @_locked
    def list_users(self) -> list[dict[str, Any]]:
        rows = self._conn.execute("SELECT id, email, role, created_at FROM users ORDER BY created_at")
        return [dict(row) for row in rows]

    @_locked
    def count_users(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    @_locked
    def delete_user(self, id: str) -> bool:
        cursor = self._conn.execute("DELETE FROM users WHERE id = ?", (id,))
        self._conn.execute("DELETE FROM sessions WHERE user_id = ?", (id,))
        self._conn.commit()
        return cursor.rowcount > 0

    @_locked
    def create_session(self, *, token_hash: str, user_id: str, created_at: float, expires_at: float) -> None:
        self._conn.execute(
            "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token_hash, user_id, created_at, expires_at),
        )
        self._conn.commit()

    @_locked
    def get_session_user(self, token_hash: str, *, now: float) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT users.id, users.email, users.role, users.created_at
            FROM sessions JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at > ?
            """,
            (token_hash, now),
        ).fetchone()
        return dict(row) if row else None

    @_locked
    def delete_session(self, token_hash: str) -> None:
        self._conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
        self._conn.commit()

    @_locked
    def delete_expired_sessions(self, now: float) -> int:
        cursor = self._conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        self._conn.commit()
        return cursor.rowcount
