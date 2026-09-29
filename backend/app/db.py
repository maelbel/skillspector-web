"""The scan store the rest of the app talks to. Which engine backs it is picked once, in init_db."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.storage import ScanRow, ScanStore, create_store

_store: ScanStore | None = None


def _store_or_raise() -> ScanStore:
    if _store is None:
        raise RuntimeError("db.init_db() must be called before using the scan store")
    return _store


def init_db() -> None:
    global _store
    close_db()
    _store = create_store(get_settings())


def close_db() -> None:
    global _store
    if _store is not None:
        _store.close()
        _store = None


def insert_scan(*, id: str, target: str, status: str, created_at: float, provider: str | None) -> None:
    _store_or_raise().insert_scan(id=id, target=target, status=status, created_at=created_at, provider=provider)


def update_scan(
    *,
    id: str,
    status: str,
    finished_at: float | None,
    result: dict[str, Any] | None,
    error: str | None,
) -> None:
    _store_or_raise().update_scan(id=id, status=status, finished_at=finished_at, result=result, error=error)


def fail_unfinished_scans(*, error: str, finished_at: float) -> int:
    return _store_or_raise().fail_unfinished_scans(error=error, finished_at=finished_at)


def get_scan(id: str) -> ScanRow | None:
    return _store_or_raise().get_scan(id)


def delete_scan(id: str) -> bool:
    return _store_or_raise().delete_scan(id)


def delete_scans_older_than(cutoff: float) -> int:
    return _store_or_raise().delete_scans_older_than(cutoff)


def get_retention_days() -> float | None:
    return _store_or_raise().get_retention_days()


def set_retention_days(value: float | None) -> None:
    _store_or_raise().set_retention_days(value)


def list_scans(limit: int, offset: int) -> tuple[list[ScanRow], int]:
    return _store_or_raise().list_scans(limit, offset)
