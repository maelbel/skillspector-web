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


def ensure_db() -> None:
    """init_db() unless it already ran, for entry points that skip the API's startup (queue workers)."""
    if _store is None:
        init_db()


def close_db() -> None:
    global _store
    if _store is not None:
        _store.close()
        _store = None


def insert_scan(
    *, id: str, target: str, status: str, created_at: float, provider: str | None, owner_id: str | None = None
) -> None:
    _store_or_raise().insert_scan(
        id=id, target=target, status=status, created_at=created_at, provider=provider, owner_id=owner_id
    )


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


def count_active_scans() -> int:
    """Scans still pending or running."""
    return _store_or_raise().count_active_scans()


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


def list_scans(limit: int, offset: int, *, owner_id: str | None = None) -> tuple[list[ScanRow], int]:
    return _store_or_raise().list_scans(limit, offset, owner_id=owner_id)


def append_log_line(scan_id: str, line: str, *, keep: int) -> None:
    _store_or_raise().append_log_line(scan_id, line, keep=keep)


def get_log_lines(scan_id: str) -> list[str]:
    return _store_or_raise().get_log_lines(scan_id)


def increment_progress(scan_id: str) -> None:
    _store_or_raise().increment_progress(scan_id)


def get_progress(scan_id: str) -> int:
    return _store_or_raise().get_progress(scan_id)


def clear_logs(scan_id: str) -> None:
    _store_or_raise().clear_logs(scan_id)


def create_user(*, id: str, email: str, password_hash: str, role: str, created_at: float) -> None:
    _store_or_raise().create_user(id=id, email=email, password_hash=password_hash, role=role, created_at=created_at)


def create_first_user(*, id: str, email: str, password_hash: str, role: str, created_at: float) -> bool:
    return _store_or_raise().create_first_user(
        id=id, email=email, password_hash=password_hash, role=role, created_at=created_at
    )


def get_user(id: str) -> dict[str, Any] | None:
    return _store_or_raise().get_user(id)


def get_user_by_email(email: str) -> dict[str, Any] | None:
    return _store_or_raise().get_user_by_email(email)


def list_users() -> list[dict[str, Any]]:
    return _store_or_raise().list_users()


def count_users() -> int:
    return _store_or_raise().count_users()


def delete_user(id: str) -> bool:
    return _store_or_raise().delete_user(id)


def create_session(*, token_hash: str, user_id: str, created_at: float, expires_at: float) -> None:
    _store_or_raise().create_session(token_hash=token_hash, user_id=user_id, created_at=created_at, expires_at=expires_at)


def get_session_user(token_hash: str, *, now: float) -> dict[str, Any] | None:
    return _store_or_raise().get_session_user(token_hash, now=now)


def delete_session(token_hash: str) -> None:
    _store_or_raise().delete_session(token_hash)


def delete_expired_sessions(now: float) -> int:
    return _store_or_raise().delete_expired_sessions(now)
