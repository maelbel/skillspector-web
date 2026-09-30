from __future__ import annotations

import time
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from app.storage.base import SUMMARY_COLUMNS, ScanRow, risk_columns

# Serialises migrations when several instances start at once (any constant works, it just has to
# be the same everywhere).
_MIGRATION_LOCK_ID = 71_182_031

# Append-only: never edit an entry once released, add a new version instead. Mirrors the SQLite
# schema, with Postgres types (JSONB report, DOUBLE PRECISION timestamps).
MIGRATIONS: list[tuple[int, list[str]]] = [
    (
        1,
        [
            """
            CREATE TABLE IF NOT EXISTS scans (
                id TEXT PRIMARY KEY,
                target TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at DOUBLE PRECISION NOT NULL,
                finished_at DOUBLE PRECISION,
                result JSONB,
                error TEXT,
                provider TEXT,
                risk_score DOUBLE PRECISION,
                severity TEXT,
                recommendation TEXT
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_scans_created_at ON scans (created_at DESC)",
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                scan_retention_days DOUBLE PRECISION
            )
            """,
        ],
    ),
    (
        2,
        [
            """
            CREATE TABLE scan_log_lines (
                id BIGSERIAL PRIMARY KEY,
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
                created_at DOUBLE PRECISION NOT NULL
            )
            """,
            """
            CREATE TABLE sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at DOUBLE PRECISION NOT NULL,
                expires_at DOUBLE PRECISION NOT NULL
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
                created_at DOUBLE PRECISION NOT NULL,
                expires_at DOUBLE PRECISION NOT NULL,
                used_at DOUBLE PRECISION
            )
            """,
            "CREATE INDEX idx_password_resets_user ON password_resets (user_id)",
        ],
    ),
]


class PostgresStore:
    def __init__(self, url: str, *, default_retention_days: float | None) -> None:
        # Small pool: on Vercel each instance holds its own, and Fluid Compute shares an instance
        # across concurrent requests.
        self._pool = ConnectionPool(
            url,
            min_size=1,
            max_size=5,
            kwargs={"autocommit": True, "row_factory": dict_row},
            open=True,
        )
        self._migrate()
        self._execute(
            "INSERT INTO app_settings (id, scan_retention_days) VALUES (1, %s) ON CONFLICT (id) DO NOTHING",
            (default_retention_days,),
        )

    def _migrate(self) -> None:
        with self._pool.connection() as conn, conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (_MIGRATION_LOCK_ID,))
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations"
                " (version INTEGER PRIMARY KEY, applied_at DOUBLE PRECISION NOT NULL)"
            )
            applied = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations")}
            for version, statements in MIGRATIONS:
                if version in applied:
                    continue
                for statement in statements:
                    conn.execute(statement)
                conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (%s, %s)",
                    (version, time.time()),
                )

    def _execute(self, query: str, params: tuple[Any, ...] = ()) -> int:
        with self._pool.connection() as conn:
            return conn.execute(query, params).rowcount

    def close(self) -> None:
        self._pool.close()

    def insert_scan(
        self, *, id: str, target: str, status: str, created_at: float, provider: str | None, owner_id: str | None = None
    ) -> None:
        self._execute(
            "INSERT INTO scans (id, target, status, created_at, provider, owner_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (id, target, status, created_at, provider, owner_id),
        )

    def update_scan(
        self,
        *,
        id: str,
        status: str,
        finished_at: float | None,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> None:
        self._execute(
            """
            UPDATE scans
            SET status = %s, finished_at = %s, result = %s, error = %s,
                risk_score = %s, severity = %s, recommendation = %s
            WHERE id = %s
            """,
            (
                status,
                finished_at,
                Jsonb(result) if result is not None else None,
                error,
                *risk_columns(result),
                id,
            ),
        )

    def fail_unfinished_scans(self, *, error: str, finished_at: float) -> int:
        return self._execute(
            "UPDATE scans SET status = 'error', error = %s, finished_at = %s WHERE status IN ('pending', 'running')",
            (error, finished_at),
        )

    def count_active_scans(self) -> int:
        with self._pool.connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS active FROM scans WHERE status IN ('pending', 'running')").fetchone()
        return row["active"]

    def get_scan(self, id: str) -> ScanRow | None:
        with self._pool.connection() as conn:
            return conn.execute("SELECT * FROM scans WHERE id = %s", (id,)).fetchone()

    def delete_scan(self, id: str) -> bool:
        with self._pool.connection() as conn, conn.transaction():
            deleted = conn.execute("DELETE FROM scans WHERE id = %s", (id,)).rowcount
            conn.execute("DELETE FROM scan_log_lines WHERE scan_id = %s", (id,))
        return deleted > 0

    def delete_scans_older_than(self, cutoff: float) -> int:
        # Pending/running scans are still owned by a live job; deleting them would lose the result.
        with self._pool.connection() as conn, conn.transaction():
            deleted = conn.execute(
                "DELETE FROM scans WHERE created_at < %s AND status NOT IN ('pending', 'running')",
                (cutoff,),
            ).rowcount
            conn.execute("DELETE FROM scan_log_lines WHERE scan_id NOT IN (SELECT id FROM scans)")
        return deleted

    def get_retention_days(self) -> float | None:
        with self._pool.connection() as conn:
            row = conn.execute("SELECT scan_retention_days FROM app_settings WHERE id = 1").fetchone()
        return row["scan_retention_days"] if row else None

    def set_retention_days(self, value: float | None) -> None:
        self._execute("UPDATE app_settings SET scan_retention_days = %s WHERE id = 1", (value,))

    def list_scans(self, limit: int, offset: int, *, owner_id: str | None = None) -> tuple[list[ScanRow], int]:
        where, params = ("WHERE owner_id = %s", (owner_id,)) if owner_id is not None else ("", ())
        with self._pool.connection() as conn:
            rows = conn.execute(
                f"SELECT {SUMMARY_COLUMNS} FROM scans {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (*params, limit, offset),
            ).fetchall()
            total = conn.execute(f"SELECT COUNT(*) AS total FROM scans {where}", params).fetchone()["total"]
        return rows, total

    def append_log_line(self, scan_id: str, line: str, *, keep: int) -> None:
        with self._pool.connection() as conn, conn.transaction():
            conn.execute("INSERT INTO scan_log_lines (scan_id, line) VALUES (%s, %s)", (scan_id, line))
            # Keep only the newest `keep` lines of this scan.
            conn.execute(
                """
                DELETE FROM scan_log_lines
                WHERE scan_id = %s AND id <= (
                    SELECT id FROM scan_log_lines WHERE scan_id = %s ORDER BY id DESC LIMIT 1 OFFSET %s
                )
                """,
                (scan_id, scan_id, keep),
            )

    def get_log_lines(self, scan_id: str) -> list[str]:
        with self._pool.connection() as conn:
            rows = conn.execute("SELECT line FROM scan_log_lines WHERE scan_id = %s ORDER BY id", (scan_id,)).fetchall()
        return [row["line"] for row in rows]

    def increment_progress(self, scan_id: str) -> None:
        self._execute("UPDATE scans SET completed_steps = completed_steps + 1 WHERE id = %s", (scan_id,))

    def get_progress(self, scan_id: str) -> int:
        with self._pool.connection() as conn:
            row = conn.execute("SELECT completed_steps FROM scans WHERE id = %s", (scan_id,)).fetchone()
        return row["completed_steps"] if row else 0

    def clear_logs(self, scan_id: str) -> None:
        with self._pool.connection() as conn, conn.transaction():
            conn.execute("DELETE FROM scan_log_lines WHERE scan_id = %s", (scan_id,))
            conn.execute("UPDATE scans SET completed_steps = 0 WHERE id = %s", (scan_id,))

    # Accounts (app/auth). Emails are stored lower-cased by the caller.

    def create_user(self, *, id: str, email: str, password_hash: str, role: str, created_at: float) -> None:
        self._execute(
            "INSERT INTO users (id, email, password_hash, role, created_at) VALUES (%s, %s, %s, %s, %s)",
            (id, email, password_hash, role, created_at),
        )

    def create_first_user(self, *, id: str, email: str, password_hash: str, role: str, created_at: float) -> bool:
        """Create the account only if none exists yet; False when another request got there first."""
        with self._pool.connection() as conn, conn.transaction():
            # Serialise concurrent first-run setups so only one of them creates the admin.
            conn.execute("LOCK TABLE users IN EXCLUSIVE MODE")
            if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
                return False
            conn.execute(
                "INSERT INTO users (id, email, password_hash, role, created_at) VALUES (%s, %s, %s, %s, %s)",
                (id, email, password_hash, role, created_at),
            )
        return True

    def get_user(self, id: str) -> dict[str, Any] | None:
        with self._pool.connection() as conn:
            return conn.execute("SELECT * FROM users WHERE id = %s", (id,)).fetchone()

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with self._pool.connection() as conn:
            return conn.execute("SELECT * FROM users WHERE email = %s", (email,)).fetchone()

    def list_users(self) -> list[dict[str, Any]]:
        with self._pool.connection() as conn:
            return conn.execute("SELECT id, email, role, created_at FROM users ORDER BY created_at").fetchall()

    def count_users(self) -> int:
        with self._pool.connection() as conn:
            return conn.execute("SELECT COUNT(*) AS users FROM users").fetchone()["users"]

    def delete_user(self, id: str) -> bool:
        with self._pool.connection() as conn, conn.transaction():
            deleted = conn.execute("DELETE FROM users WHERE id = %s", (id,)).rowcount
            conn.execute("DELETE FROM sessions WHERE user_id = %s", (id,))
        return deleted > 0

    def create_session(self, *, token_hash: str, user_id: str, created_at: float, expires_at: float) -> None:
        self._execute(
            "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (%s, %s, %s, %s)",
            (token_hash, user_id, created_at, expires_at),
        )

    def get_session_user(self, token_hash: str, *, now: float) -> dict[str, Any] | None:
        with self._pool.connection() as conn:
            return conn.execute(
                """
                SELECT users.id, users.email, users.role, users.created_at
                FROM sessions JOIN users ON users.id = sessions.user_id
                WHERE sessions.token_hash = %s AND sessions.expires_at > %s
                """,
                (token_hash, now),
            ).fetchone()

    def delete_session(self, token_hash: str) -> None:
        self._execute("DELETE FROM sessions WHERE token_hash = %s", (token_hash,))

    def delete_expired_sessions(self, now: float) -> int:
        return self._execute("DELETE FROM sessions WHERE expires_at <= %s", (now,))

    def set_password_hash(self, user_id: str, password_hash: str) -> None:
        self._execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))

    def delete_sessions_for_user(self, user_id: str, *, keep_token_hash: str | None = None) -> None:
        self._execute(
            "DELETE FROM sessions WHERE user_id = %s AND token_hash IS DISTINCT FROM %s", (user_id, keep_token_hash)
        )

    def create_password_reset(self, *, token_hash: str, user_id: str, created_at: float, expires_at: float) -> None:
        # Only the newest link works: issuing one cancels the user's earlier links.
        with self._pool.connection() as conn, conn.transaction():
            conn.execute("DELETE FROM password_resets WHERE user_id = %s", (user_id,))
            conn.execute(
                "INSERT INTO password_resets (token_hash, user_id, created_at, expires_at) VALUES (%s, %s, %s, %s)",
                (token_hash, user_id, created_at, expires_at),
            )

    def consume_password_reset(self, token_hash: str, *, now: float) -> str | None:
        """Mark an unused, unexpired reset as used and return its user id, in one statement."""
        with self._pool.connection() as conn:
            row = conn.execute(
                """
                UPDATE password_resets SET used_at = %s
                WHERE token_hash = %s AND used_at IS NULL AND expires_at > %s
                RETURNING user_id
                """,
                (now, token_hash, now),
            ).fetchone()
        return row["user_id"] if row else None
