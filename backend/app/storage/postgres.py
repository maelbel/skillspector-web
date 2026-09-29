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

    def insert_scan(self, *, id: str, target: str, status: str, created_at: float, provider: str | None) -> None:
        self._execute(
            "INSERT INTO scans (id, target, status, created_at, provider) VALUES (%s, %s, %s, %s, %s)",
            (id, target, status, created_at, provider),
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
        return self._execute("DELETE FROM scans WHERE id = %s", (id,)) > 0

    def delete_scans_older_than(self, cutoff: float) -> int:
        # Pending/running scans are still owned by a live job; deleting them would lose the result.
        return self._execute(
            "DELETE FROM scans WHERE created_at < %s AND status NOT IN ('pending', 'running')",
            (cutoff,),
        )

    def get_retention_days(self) -> float | None:
        with self._pool.connection() as conn:
            row = conn.execute("SELECT scan_retention_days FROM app_settings WHERE id = 1").fetchone()
        return row["scan_retention_days"] if row else None

    def set_retention_days(self, value: float | None) -> None:
        self._execute("UPDATE app_settings SET scan_retention_days = %s WHERE id = 1", (value,))

    def list_scans(self, limit: int, offset: int) -> tuple[list[ScanRow], int]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                f"SELECT {SUMMARY_COLUMNS} FROM scans ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (limit, offset),
            ).fetchall()
            total = conn.execute("SELECT COUNT(*) AS total FROM scans").fetchone()["total"]
        return rows, total
