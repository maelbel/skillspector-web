from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import get_settings

_connection: sqlite3.Connection | None = None


def _connection_or_raise() -> sqlite3.Connection:
    if _connection is None:
        raise RuntimeError("db.init_db() must be called before using the scan store")
    return _connection


def init_db() -> None:
    global _connection
    db_path = Path(get_settings().db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
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
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_created_at ON scans (created_at DESC)")
    conn.commit()
    _connection = conn


def insert_scan(
    *,
    id: str,
    target: str,
    status: str,
    created_at: float,
    provider: str | None,
) -> None:
    conn = _connection_or_raise()
    conn.execute(
        "INSERT INTO scans (id, target, status, created_at, provider) VALUES (?, ?, ?, ?, ?)",
        (id, target, status, created_at, provider),
    )
    conn.commit()


def update_scan(
    *,
    id: str,
    status: str,
    finished_at: float | None,
    result: dict[str, Any] | None,
    error: str | None,
) -> None:
    risk = (result or {}).get("risk_assessment") or {}
    conn = _connection_or_raise()
    conn.execute(
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
            risk.get("score"),
            risk.get("severity"),
            risk.get("recommendation"),
            id,
        ),
    )
    conn.commit()


def get_scan(id: str) -> sqlite3.Row | None:
    conn = _connection_or_raise()
    return conn.execute("SELECT * FROM scans WHERE id = ?", (id,)).fetchone()


def delete_scan(id: str) -> bool:
    conn = _connection_or_raise()
    cursor = conn.execute("DELETE FROM scans WHERE id = ?", (id,))
    conn.commit()
    return cursor.rowcount > 0


def list_scans(limit: int, offset: int) -> tuple[list[sqlite3.Row], int]:
    conn = _connection_or_raise()
    rows = conn.execute(
        """
        SELECT id, target, status, created_at, finished_at, error, risk_score, severity, recommendation
        FROM scans
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
    return rows, total
