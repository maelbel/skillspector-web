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
    def insert_scan(self, *, id: str, target: str, status: str, created_at: float, provider: str | None) -> None:
        self._conn.execute(
            "INSERT INTO scans (id, target, status, created_at, provider) VALUES (?, ?, ?, ?, ?)",
            (id, target, status, created_at, provider),
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
    def list_scans(self, limit: int, offset: int) -> tuple[list[ScanRow], int]:
        rows = self._conn.execute(
            f"SELECT {SUMMARY_COLUMNS} FROM scans ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        total = self._conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
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
