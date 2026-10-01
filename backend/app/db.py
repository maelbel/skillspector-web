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
    *,
    id: str,
    target: str,
    status: str,
    created_at: float,
    provider: str | None,
    owner_id: str | None = None,
    llm_model: str | None = None,
    baseline: str | None = None,
) -> None:
    _store_or_raise().insert_scan(
        id=id,
        target=target,
        status=status,
        created_at=created_at,
        provider=provider,
        owner_id=owner_id,
        llm_model=llm_model,
        baseline=baseline,
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


def count_active_scans(*, owner_id: str | None = None) -> int:
    """Scans still pending or running; with owner_id, only that user's."""
    return _store_or_raise().count_active_scans(owner_id=owner_id)


def ai_token_totals(*, since: float, owner_id: str | None = None) -> dict[str, int]:
    """AI tokens of scans created since then that are still in history; with owner_id, only that user's."""
    return _store_or_raise().ai_token_totals(since=since, owner_id=owner_id)


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


def list_users(*, query: str | None = None) -> list[dict[str, Any]]:
    return _store_or_raise().list_users(query=query)


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


def set_password_hash(user_id: str, password_hash: str) -> None:
    _store_or_raise().set_password_hash(user_id, password_hash)


def delete_sessions_for_user(user_id: str, *, keep_token_hash: str | None = None) -> None:
    _store_or_raise().delete_sessions_for_user(user_id, keep_token_hash=keep_token_hash)


def create_password_reset(*, token_hash: str, user_id: str, created_at: float, expires_at: float) -> None:
    _store_or_raise().create_password_reset(
        token_hash=token_hash, user_id=user_id, created_at=created_at, expires_at=expires_at
    )


def consume_password_reset(token_hash: str, *, now: float) -> str | None:
    return _store_or_raise().consume_password_reset(token_hash, now=now)


def update_user(user_id: str, *, role: str | None = None, status: str | None = None) -> None:
    _store_or_raise().update_user(user_id, role=role, status=status)


def record_login(user_id: str, at: float) -> None:
    _store_or_raise().record_login(user_id, at)


def count_active_admins() -> int:
    return _store_or_raise().count_active_admins()


def get_allow_signup() -> bool | None:
    return _store_or_raise().get_allow_signup()


def set_allow_signup(value: bool | None) -> None:
    _store_or_raise().set_allow_signup(value)


def get_scan_limits() -> dict[str, Any]:
    return _store_or_raise().get_scan_limits()


def set_scan_limits(*, scans_paused: bool | None, daily_scan_quota: int | None, concurrent_scan_quota: int | None) -> None:
    _store_or_raise().set_scan_limits(
        scans_paused=scans_paused, daily_scan_quota=daily_scan_quota, concurrent_scan_quota=concurrent_scan_quota
    )


def add_audit(
    *,
    created_at: float,
    actor_id: str | None,
    actor_email: str | None,
    action: str,
    target_id: str | None = None,
    target_email: str | None = None,
    detail: str | None = None,
) -> None:
    _store_or_raise().add_audit(
        created_at=created_at,
        actor_id=actor_id,
        actor_email=actor_email,
        action=action,
        target_id=target_id,
        target_email=target_email,
        detail=detail,
    )


def list_audit(limit: int, offset: int, *, target_id: str | None = None) -> tuple[list[dict[str, Any]], int]:
    return _store_or_raise().list_audit(limit, offset, target_id=target_id)


def overview_stats(*, since: float) -> dict[str, Any]:
    return _store_or_raise().overview_stats(since=since)


def set_llm_credential(*, user_id: str, provider: str, encrypted_key: str, key_hint: str, now: float) -> None:
    _store_or_raise().set_llm_credential(
        user_id=user_id, provider=provider, encrypted_key=encrypted_key, key_hint=key_hint, now=now
    )


def get_llm_credential(user_id: str) -> dict[str, Any] | None:
    return _store_or_raise().get_llm_credential(user_id)


def delete_llm_credential(user_id: str) -> bool:
    return _store_or_raise().delete_llm_credential(user_id)


def put_scan_secret(*, scan_id: str, encrypted_key: str, now: float) -> None:
    _store_or_raise().put_scan_secret(scan_id=scan_id, encrypted_key=encrypted_key, now=now)


def get_scan_secret(scan_id: str) -> str | None:
    return _store_or_raise().get_scan_secret(scan_id)


def delete_scan_secret(scan_id: str) -> None:
    _store_or_raise().delete_scan_secret(scan_id)


def count_rate_limit_hits(key: str, *, window_seconds: float, now: float) -> int:
    return _store_or_raise().count_rate_limit_hits(key, window_seconds=window_seconds, now=now)


def rate_limit_hit(key: str, *, limit: int, window_seconds: float, now: float) -> float | None:
    return _store_or_raise().rate_limit_hit(key, limit=limit, window_seconds=window_seconds, now=now)
