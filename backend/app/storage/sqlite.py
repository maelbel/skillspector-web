from __future__ import annotations

import functools
import json
import sqlite3
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.storage.base import (
    SUMMARY_COLUMNS,
    ScanRow,
    badge_scan_query,
    last_monitor_event_query,
    list_monitor_events_query,
    monitor_queries,
    previous_scan_query,
    scan_filter,
    scan_order,
    summary_columns,
)

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
    (
        4,
        [
            """
            CREATE TABLE password_resets (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                used_at REAL
            )
            """,
            "CREATE INDEX idx_password_resets_user ON password_resets (user_id)",
        ],
    ),
    (
        5,
        [
            "ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'",
            "ALTER TABLE users ADD COLUMN last_login_at REAL",
            "ALTER TABLE app_settings ADD COLUMN allow_signup INTEGER",
            """
            CREATE TABLE audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at REAL NOT NULL,
                actor_id TEXT,
                actor_email TEXT,
                action TEXT NOT NULL,
                target_id TEXT,
                target_email TEXT,
                detail TEXT
            )
            """,
            "CREATE INDEX idx_audit_log_created ON audit_log (created_at DESC)",
        ],
    ),
    (
        6,
        [
            """
            CREATE TABLE llm_credentials (
                user_id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                encrypted_key TEXT NOT NULL,
                key_hint TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """,
            """
            CREATE TABLE scan_secrets (
                scan_id TEXT PRIMARY KEY,
                encrypted_key TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """,
            "ALTER TABLE scans ADD COLUMN llm_model TEXT",
        ],
    ),
    (
        7,
        [
            """
            CREATE TABLE rate_limit_hits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                hit_at REAL NOT NULL,
                expires_at REAL NOT NULL
            )
            """,
            "CREATE INDEX idx_rate_limit_hits_key ON rate_limit_hits (key, hit_at DESC)",
            "CREATE INDEX idx_rate_limit_hits_expires ON rate_limit_hits (expires_at)",
        ],
    ),
    (
        8,
        [
            # Scan quotas and the pause switch (app/quotas.py). A NULL quota follows the server's
            # configured default; 0 means no limit.
            "ALTER TABLE app_settings ADD COLUMN scans_paused INTEGER",
            "ALTER TABLE app_settings ADD COLUMN daily_scan_quota INTEGER",
            "ALTER TABLE app_settings ADD COLUMN concurrent_scan_quota INTEGER",
        ],
    ),
    (
        9,
        [
            # Whether the scan's AI review ran: complete, degraded or failed (app/ai_review.py).
            # NULL for static scans, and for scans finished before this column existed.
            "ALTER TABLE scans ADD COLUMN ai_review TEXT",
        ],
    ),
    (
        10,
        [
            # Tokens the scan's AI review used, as the provider reported them (app/ai_usage.py).
            # NULL for static scans, for counters a provider didn't report, and for scans
            # finished before these columns existed.
            "ALTER TABLE scans ADD COLUMN ai_input_tokens INTEGER",
            "ALTER TABLE scans ADD COLUMN ai_output_tokens INTEGER",
            "ALTER TABLE scans ADD COLUMN ai_cached_tokens INTEGER",
        ],
    ),
    (
        11,
        [
            # The baseline file a scan was started with (YAML or JSON text), so a queued scan can
            # apply it wherever it runs. NULL for scans without one.
            "ALTER TABLE scans ADD COLUMN baseline TEXT",
        ],
    ),
    (
        12,
        [
            # How many levels of a skill's external references the scan follows (skillspector's
            # --transitive-depth). NULL when it follows none.
            "ALTER TABLE scans ADD COLUMN transitive_depth INTEGER",
        ],
    ),
    (
        13,
        [
            # Where a scan's uploaded file is held until it ends (app/uploads.py): a local path, or
            # blob:<pathname>. NULL for scans of a link.
            "ALTER TABLE scans ADD COLUMN upload TEXT",
        ],
    ),
    (
        14,
        [
            # A target's scans, newest first: the history of one target, and the scan a rescan is
            # compared with (app/rescan.py).
            "CREATE INDEX IF NOT EXISTS scans_target_created_at ON scans (target, created_at)",
        ],
    ),
    (
        15,
        [
            # The read-only link a scan's owner shared its result with (app/api/routes/shared.py),
            # until they revoke it. NULL when it isn't shared.
            "ALTER TABLE scans ADD COLUMN share_token TEXT",
            "CREATE UNIQUE INDEX IF NOT EXISTS scans_share_token ON scans (share_token)",
        ],
    ),
    (
        16,
        [
            # The history's sorts (GET /scan?sort=…): everyone's scans for admins, one user's for
            # the others. Targets already have one (scans_target_created_at).
            "CREATE INDEX IF NOT EXISTS scans_created_at ON scans (created_at)",
            "CREATE INDEX IF NOT EXISTS scans_risk_score ON scans (risk_score)",
            "CREATE INDEX IF NOT EXISTS scans_status ON scans (status)",
            "CREATE INDEX IF NOT EXISTS scans_owner_created_at ON scans (owner_id, created_at)",
            "CREATE INDEX IF NOT EXISTS scans_owner_risk_score ON scans (owner_id, risk_score)",
        ],
    ),
    (
        17,
        [
            # Personal API tokens (app/auth/api_tokens.py): like sessions, only a token's hash is
            # stored. prefix is its first characters, to tell a user's tokens apart.
            """
            CREATE TABLE api_tokens (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                prefix TEXT NOT NULL,
                scopes TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL,
                last_used_at REAL
            )
            """,
            "CREATE INDEX idx_api_tokens_user ON api_tokens (user_id)",
        ],
    ),
    (
        18,
        [
            # Whether a shared scan's owner put it on its target's status badge
            # (app/api/routes/badge.py). Only a shared scan can be; revoking the link takes it off.
            "ALTER TABLE scans ADD COLUMN badge INTEGER NOT NULL DEFAULT 0",
        ],
    ),
    (
        19,
        [
            # What the health panel and alerts read (app/monitoring.py): failed scans, sandbox
            # errors, queue redeliveries, refused submissions, and the alerts sent. Kept 30 days.
            """
            CREATE TABLE monitor_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at REAL NOT NULL,
                kind TEXT NOT NULL,
                message TEXT,
                scan_id TEXT,
                count INTEGER NOT NULL DEFAULT 1
            )
            """,
            "CREATE INDEX idx_monitor_events_kind ON monitor_events (kind, created_at)",
            # Scans that finished within a window: the failure rate.
            "CREATE INDEX IF NOT EXISTS scans_finished_at ON scans (finished_at)",
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
        self,
        *,
        id: str,
        target: str,
        status: str,
        created_at: float,
        provider: str | None,
        owner_id: str | None = None,
        llm_model: str | None = None,
        baseline: str | None = None,
        transitive_depth: int | None = None,
        upload: str | None = None,
    ) -> None:
        self._conn.execute(
            "INSERT INTO scans (id, target, status, created_at, provider, owner_id, llm_model, baseline, transitive_depth, upload)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (id, target, status, created_at, provider, owner_id, llm_model, baseline, transitive_depth, upload),
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
                risk_score = ?, severity = ?, recommendation = ?, ai_review = ?,
                ai_input_tokens = ?, ai_output_tokens = ?, ai_cached_tokens = ?
            WHERE id = ?
            """,
            (
                status,
                finished_at,
                json.dumps(result) if result is not None else None,
                error,
                *summary_columns(result),
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
    def count_active_scans(self, *, owner_id: str | None = None) -> int:
        where, params = (" AND owner_id = ?", (owner_id,)) if owner_id is not None else ("", ())
        query = f"SELECT COUNT(*) FROM scans WHERE status IN ('pending', 'running'){where}"
        return self._conn.execute(query, params).fetchone()[0]

    @_locked
    def ai_token_totals(self, *, since: float, owner_id: str | None = None) -> dict[str, int]:
        where, params = (" AND owner_id = ?", (owner_id,)) if owner_id is not None else ("", ())
        row = self._conn.execute(
            f"""
            SELECT COUNT(ai_input_tokens) AS scans, COALESCE(SUM(ai_input_tokens), 0) AS input_tokens,
                   COALESCE(SUM(ai_output_tokens), 0) AS output_tokens, COALESCE(SUM(ai_cached_tokens), 0) AS cached_tokens
            FROM scans WHERE created_at >= ?{where}
            """,
            (since, *params),
        ).fetchone()
        return dict(row)

    @_locked
    def get_scan(self, id: str) -> ScanRow | None:
        row = self._conn.execute("SELECT * FROM scans WHERE id = ?", (id,)).fetchone()
        return _to_row(row) if row is not None else None

    @_locked
    def previous_scan(self, *, target: str, owner_id: str | None, before: float, with_ai_review: bool) -> ScanRow | None:
        query, params = previous_scan_query("?", target=target, owner_id=owner_id, before=before, with_ai_review=with_ai_review)
        row = self._conn.execute(query, params).fetchone()
        return _to_row(row) if row is not None else None

    @_locked
    def set_share_token(self, scan_id: str, token: str | None) -> None:
        # An unshared scan is off its badge too.
        self._conn.execute("UPDATE scans SET share_token = ?, badge = badge AND ? WHERE id = ?", (token, token is not None, scan_id))
        self._conn.commit()

    @_locked
    def get_shared_scan(self, token: str) -> ScanRow | None:
        row = self._conn.execute("SELECT * FROM scans WHERE share_token = ?", (token,)).fetchone()
        return _to_row(row) if row is not None else None

    @_locked
    def set_badge(self, scan_id: str, on: bool) -> None:
        self._conn.execute("UPDATE scans SET badge = ? WHERE id = ?", (on, scan_id))
        self._conn.commit()

    @_locked
    def badge_scan(self, target: str) -> ScanRow | None:
        row = self._conn.execute(badge_scan_query("?"), (target,)).fetchone()
        return _to_row(row) if row is not None else None

    @_locked
    def delete_scan(self, id: str) -> bool:
        cursor = self._conn.execute("DELETE FROM scans WHERE id = ?", (id,))
        self._conn.execute("DELETE FROM scan_log_lines WHERE scan_id = ?", (id,))
        self._conn.execute("DELETE FROM scan_secrets WHERE scan_id = ?", (id,))
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
        self._conn.execute("DELETE FROM scan_secrets WHERE scan_id NOT IN (SELECT id FROM scans)")
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
    def list_scans(
        self,
        limit: int,
        offset: int,
        *,
        owner_id: str | None = None,
        target: str | None = None,
        sort: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[ScanRow], int]:
        where, params = scan_filter("?", owner_id=owner_id, target=target)
        rows = self._conn.execute(
            f"SELECT {SUMMARY_COLUMNS} FROM scans {where} {scan_order(sort, order)} LIMIT ? OFFSET ?",
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
    def list_users(self, *, query: str | None = None) -> list[dict[str, Any]]:
        where, params = ("WHERE users.email LIKE ?", (f"%{query.lower()}%",)) if query else ("", ())
        rows = self._conn.execute(f"""
            SELECT users.id, users.email, users.role, users.status, users.created_at, users.last_login_at, COALESCE(counts.scans, 0) AS scan_count
            FROM users
            LEFT JOIN (SELECT owner_id, COUNT(*) AS scans FROM scans GROUP BY owner_id) AS counts
                ON counts.owner_id = users.id
            {where}
            ORDER BY users.created_at
""", params)
        return [dict(row) for row in rows]

    @_locked
    def count_users(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    @_locked
    def delete_user(self, id: str) -> bool:
        cursor = self._conn.execute("DELETE FROM users WHERE id = ?", (id,))
        self._conn.execute("DELETE FROM sessions WHERE user_id = ?", (id,))
        self._conn.execute("DELETE FROM llm_credentials WHERE user_id = ?", (id,))
        self._conn.execute("DELETE FROM api_tokens WHERE user_id = ?", (id,))
        self._conn.commit()
        return cursor.rowcount > 0

    @_locked
    def create_api_token(self, *, id: str, user_id: str, name: str, token_hash: str, prefix: str, scopes: str, created_at: float, expires_at: float | None) -> None:
        self._conn.execute(
            "INSERT INTO api_tokens (id, user_id, name, token_hash, prefix, scopes, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (id, user_id, name, token_hash, prefix, scopes, created_at, expires_at),
        )
        self._conn.commit()

    @_locked
    def list_api_tokens(self, user_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT id, user_id, name, prefix, scopes, created_at, expires_at, last_used_at FROM api_tokens WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    @_locked
    def get_api_token_user(self, token_hash: str, *, now: float) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT users.id, users.email, users.role, users.status, users.created_at, users.last_login_at,
                   api_tokens.id AS token_id, api_tokens.name AS token_name, api_tokens.scopes AS token_scopes,
                   api_tokens.last_used_at AS token_last_used_at
            FROM api_tokens JOIN users ON users.id = api_tokens.user_id
            WHERE api_tokens.token_hash = ? AND (api_tokens.expires_at IS NULL OR api_tokens.expires_at > ?)
              AND users.status = 'active'
            """,
            (token_hash, now),
        ).fetchone()
        return dict(row) if row else None

    @_locked
    def mark_api_token_used(self, token_id: str, at: float) -> None:
        self._conn.execute("UPDATE api_tokens SET last_used_at = ? WHERE id = ?", (at, token_id))
        self._conn.commit()

    @_locked
    def delete_api_token(self, token_id: str, *, user_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT id, user_id, name, prefix, scopes, created_at, expires_at, last_used_at FROM api_tokens WHERE id = ? AND user_id = ?", (token_id, user_id)
        ).fetchone()
        if row is None:
            return None
        self._conn.execute("DELETE FROM api_tokens WHERE id = ?", (token_id,))
        self._conn.commit()
        return dict(row)

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
            SELECT users.id, users.email, users.role, users.status, users.created_at, users.last_login_at
            FROM sessions JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at > ? AND users.status = 'active'
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

    @_locked
    def set_password_hash(self, user_id: str, password_hash: str) -> None:
        self._conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
        self._conn.commit()

    @_locked
    def delete_sessions_for_user(self, user_id: str, *, keep_token_hash: str | None = None) -> None:
        self._conn.execute(
            "DELETE FROM sessions WHERE user_id = ? AND token_hash IS NOT ?", (user_id, keep_token_hash)
        )
        self._conn.commit()

    @_locked
    def create_password_reset(self, *, token_hash: str, user_id: str, created_at: float, expires_at: float) -> None:
        # Only the newest link works: issuing one cancels the user's earlier links.
        self._conn.execute("DELETE FROM password_resets WHERE user_id = ?", (user_id,))
        self._conn.execute(
            "INSERT INTO password_resets (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token_hash, user_id, created_at, expires_at),
        )
        self._conn.commit()

    @_locked
    def consume_password_reset(self, token_hash: str, *, now: float) -> str | None:
        """Mark an unused, unexpired reset as used and return its user id, in one statement."""
        row = self._conn.execute(
            """
            UPDATE password_resets SET used_at = ?
            WHERE token_hash = ? AND used_at IS NULL AND expires_at > ?
            RETURNING user_id
            """,
            (now, token_hash, now),
        ).fetchone()
        self._conn.commit()
        return row["user_id"] if row else None

    @_locked
    def update_user(self, user_id: str, *, role: str | None = None, status: str | None = None) -> None:
        self._conn.execute(
            "UPDATE users SET role = COALESCE(?, role), status = COALESCE(?, status) WHERE id = ?",
            (role, status, user_id),
        )
        self._conn.commit()

    @_locked
    def record_login(self, user_id: str, at: float) -> None:
        self._conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (at, user_id))
        self._conn.commit()

    @_locked
    def count_active_admins(self) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'admin' AND status = 'active'"
        ).fetchone()[0]

    @_locked
    def get_allow_signup(self) -> bool | None:
        row = self._conn.execute("SELECT allow_signup FROM app_settings WHERE id = 1").fetchone()
        return None if row is None or row["allow_signup"] is None else bool(row["allow_signup"])

    @_locked
    def get_scan_limits(self) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT scans_paused, daily_scan_quota, concurrent_scan_quota FROM app_settings WHERE id = 1"
        ).fetchone()
        if row is None:
            return {"scans_paused": None, "daily_scan_quota": None, "concurrent_scan_quota": None}
        paused = row["scans_paused"]
        return {
            "scans_paused": None if paused is None else bool(paused),
            "daily_scan_quota": row["daily_scan_quota"],
            "concurrent_scan_quota": row["concurrent_scan_quota"],
        }

    @_locked
    def set_scan_limits(
        self, *, scans_paused: bool | None, daily_scan_quota: int | None, concurrent_scan_quota: int | None
    ) -> None:
        self._conn.execute(
            "UPDATE app_settings SET scans_paused = ?, daily_scan_quota = ?, concurrent_scan_quota = ? WHERE id = 1",
            (None if scans_paused is None else int(scans_paused), daily_scan_quota, concurrent_scan_quota),
        )
        self._conn.commit()

    @_locked
    def set_allow_signup(self, value: bool | None) -> None:
        self._conn.execute(
            "UPDATE app_settings SET allow_signup = ? WHERE id = 1", (None if value is None else int(value),)
        )
        self._conn.commit()

    @_locked
    def add_audit(
        self,
        *,
        created_at: float,
        actor_id: str | None,
        actor_email: str | None,
        action: str,
        target_id: str | None,
        target_email: str | None,
        detail: str | None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO audit_log (created_at, actor_id, actor_email, action, target_id, target_email, detail)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (created_at, actor_id, actor_email, action, target_id, target_email, detail),
        )
        self._conn.commit()

    @_locked
    def add_monitor_event(self, *, created_at: float, kind: str, message: str | None, scan_id: str | None, count: int) -> None:
        self._conn.execute(monitor_queries("?")["add"], (created_at, kind, message, scan_id, count))
        self._conn.commit()

    @_locked
    def monitor_counts(self, *, since: float) -> dict[str, int]:
        rows = self._conn.execute(monitor_queries("?")["counts"], (since,)).fetchall()
        return {row["kind"]: int(row["total"]) for row in rows}

    @_locked
    def scan_outcomes(self, *, since: float) -> dict[str, int]:
        row = self._conn.execute(monitor_queries("?")["outcomes"], (since, since, since)).fetchone()
        return {key: int(row[key]) for key in ("started", "finished", "failed")}

    @_locked
    def last_monitor_event(self, kinds: tuple[str, ...], message: str | None = None) -> dict[str, Any] | None:
        row = self._conn.execute(*last_monitor_event_query("?", kinds, message)).fetchone()
        return dict(row) if row is not None else None

    @_locked
    def delete_monitor_events_older_than(self, cutoff: float) -> int:
        cursor = self._conn.execute(monitor_queries("?")["prune"], (cutoff,))
        self._conn.commit()
        return cursor.rowcount

    @_locked
    def list_monitor_events(self, limit: int, offset: int, kinds: tuple[str, ...]) -> tuple[list[dict[str, Any]], int]:
        rows_query, count_query = list_monitor_events_query("?", kinds)
        rows = self._conn.execute(rows_query, (*kinds, limit, offset)).fetchall()
        total = self._conn.execute(count_query, kinds).fetchone()["total"]
        return [dict(row) for row in rows], int(total)

    @_locked
    def list_audit(self, limit: int, offset: int, *, target_id: str | None = None) -> tuple[list[dict[str, Any]], int]:
        where, params = ("WHERE target_id = ?", (target_id,)) if target_id else ("", ())
        rows = self._conn.execute(
            f"SELECT * FROM audit_log {where} ORDER BY id DESC LIMIT ? OFFSET ?", (*params, limit, offset)
        ).fetchall()
        total = self._conn.execute(f"SELECT COUNT(*) FROM audit_log {where}", params).fetchone()[0]
        return [dict(row) for row in rows], total

    @_locked
    def overview_stats(self, *, since: float) -> dict[str, Any]:
        users = self._conn.execute(
            """
            SELECT COUNT(*) AS total,
                   COALESCE(SUM(role = 'admin'), 0) AS admins,
                   COALESCE(SUM(status = 'suspended'), 0) AS suspended,
                   COALESCE(SUM(created_at >= ?), 0) AS new
            FROM users
            """,
            (since,),
        ).fetchone()
        scans = self._conn.execute(
            """
            SELECT COUNT(*) AS total,
                   COALESCE(SUM(created_at >= ?), 0) AS recent,
                   COALESCE(SUM(recommendation = 'DO_NOT_INSTALL'), 0) AS do_not_install,
                   COALESCE(SUM(recommendation = 'CAUTION'), 0) AS caution,
                   COALESCE(SUM(recommendation = 'SAFE'), 0) AS safe,
                   COALESCE(SUM(status = 'error'), 0) AS failed,
                   COALESCE(SUM(status IN ('pending', 'running')), 0) AS active
            FROM scans
            """,
            (since,),
        ).fetchone()
        return {"users": dict(users), "scans": dict(scans)}

    # Stored AI provider keys (encrypted by the caller; see app/secrets_box.py).

    @_locked
    def set_llm_credential(
        self, *, user_id: str, provider: str, encrypted_key: str, key_hint: str, now: float
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO llm_credentials (user_id, provider, encrypted_key, key_hint, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (user_id) DO UPDATE SET
                provider = excluded.provider, encrypted_key = excluded.encrypted_key,
                key_hint = excluded.key_hint, updated_at = excluded.updated_at
            """,
            (user_id, provider, encrypted_key, key_hint, now, now),
        )
        self._conn.commit()

    @_locked
    def get_llm_credential(self, user_id: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM llm_credentials WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    @_locked
    def delete_llm_credential(self, user_id: str) -> bool:
        cursor = self._conn.execute("DELETE FROM llm_credentials WHERE user_id = ?", (user_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    @_locked
    def put_scan_secret(self, *, scan_id: str, encrypted_key: str, now: float) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO scan_secrets (scan_id, encrypted_key, created_at) VALUES (?, ?, ?)",
            (scan_id, encrypted_key, now),
        )
        self._conn.commit()

    @_locked
    def get_scan_secret(self, scan_id: str) -> str | None:
        row = self._conn.execute("SELECT encrypted_key FROM scan_secrets WHERE scan_id = ?", (scan_id,)).fetchone()
        return row["encrypted_key"] if row else None

    @_locked
    def delete_scan_secret(self, scan_id: str) -> None:
        self._conn.execute("DELETE FROM scan_secrets WHERE scan_id = ?", (scan_id,))
        self._conn.commit()

    # Rate limits (app/rate_limit.py), when SKILLSPECTOR_WEB_RATE_LIMIT_STORE=database, and daily
    # scan quotas (app/quotas.py), always.

    @_locked
    def count_rate_limit_hits(self, key: str, *, window_seconds: float, now: float) -> int:
        query = "SELECT COUNT(*) FROM rate_limit_hits WHERE key = ? AND hit_at > ?"
        return self._conn.execute(query, (key, now - window_seconds)).fetchone()[0]

    @_locked
    def rate_limit_hit(self, key: str, *, limit: int, window_seconds: float, now: float) -> float | None:
        self._conn.execute("DELETE FROM rate_limit_hits WHERE expires_at <= ?", (now,))
        recent = self._conn.execute(
            "SELECT hit_at FROM rate_limit_hits WHERE key = ? AND hit_at > ? ORDER BY hit_at DESC LIMIT ?",
            (key, now - window_seconds, limit),
        ).fetchall()
        if len(recent) >= limit:
            self._conn.commit()
            return recent[-1]["hit_at"] + window_seconds - now
        self._conn.execute(
            "INSERT INTO rate_limit_hits (key, hit_at, expires_at) VALUES (?, ?, ?)",
            (key, now, now + window_seconds),
        )
        self._conn.commit()
        return None
