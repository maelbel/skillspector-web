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
    transitive_depth: int | None = None,
    upload: str | None = None,
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
        transitive_depth=transitive_depth,
        upload=upload,
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


def list_scans(
    limit: int,
    offset: int,
    *,
    owner_id: str | None = None,
    target: str | None = None,
    sort: str = "created_at",
    order: str = "desc",
) -> tuple[list[ScanRow], int]:
    return _store_or_raise().list_scans(limit, offset, owner_id=owner_id, target=target, sort=sort, order=order)


def previous_scan(*, target: str, owner_id: str | None, before: float, with_ai_review: bool) -> ScanRow | None:
    """The latest scan of target that finished before then, by the same owner and of the same kind."""
    return _store_or_raise().previous_scan(target=target, owner_id=owner_id, before=before, with_ai_review=with_ai_review)


def set_share_token(scan_id: str, token: str | None) -> None:
    """Share the scan's result at this token, or stop sharing it (None)."""
    _store_or_raise().set_share_token(scan_id, token)


def get_shared_scan(token: str) -> ScanRow | None:
    return _store_or_raise().get_shared_scan(token)


def set_badge(scan_id: str, on: bool) -> None:
    """Put a shared scan on its target's status badge, or take it off."""
    _store_or_raise().set_badge(scan_id, on)


def badge_scan(target: str) -> ScanRow | None:
    """The scan a target's badge shows: the latest one its owner put on it."""
    return _store_or_raise().badge_scan(target)


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


def create_api_token(
    *, id: str, user_id: str, name: str, token_hash: str, prefix: str, scopes: str, created_at: float, expires_at: float | None
) -> None:
    _store_or_raise().create_api_token(
        id=id, user_id=user_id, name=name, token_hash=token_hash, prefix=prefix, scopes=scopes, created_at=created_at, expires_at=expires_at
    )


def list_api_tokens(user_id: str) -> list[dict[str, Any]]:
    """A user's tokens, newest first, without their hashes."""
    return _store_or_raise().list_api_tokens(user_id)


def get_api_token_user(token_hash: str, *, now: float) -> dict[str, Any] | None:
    """The active user a token that hasn't expired belongs to, with token_id, token_name,
    token_scopes and token_last_used_at."""
    return _store_or_raise().get_api_token_user(token_hash, now=now)


def mark_api_token_used(token_id: str, at: float) -> None:
    _store_or_raise().mark_api_token_used(token_id, at)


def delete_api_token(token_id: str, *, user_id: str) -> dict[str, Any] | None:
    """Revoke one of a user's tokens; the token as it was, or None if they have no such token."""
    return _store_or_raise().delete_api_token(token_id, user_id=user_id)


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


def add_monitor_event(*, created_at: float, kind: str, message: str | None = None, scan_id: str | None = None, count: int = 1) -> None:
    _store_or_raise().add_monitor_event(created_at=created_at, kind=kind, message=message, scan_id=scan_id, count=count)


def monitor_counts(*, since: float) -> dict[str, int]:
    """Each monitoring event kind's count since then."""
    return _store_or_raise().monitor_counts(since=since)


def scan_outcomes(*, since: float) -> dict[str, int]:
    """Scans started, and finished and failed, since then."""
    return _store_or_raise().scan_outcomes(since=since)


def last_monitor_event(*kinds: str, message: str | None = None) -> dict[str, Any] | None:
    """The latest event of these kinds; with a message, only one with it (an alert's rule)."""
    return _store_or_raise().last_monitor_event(tuple(kinds), message)


def delete_monitor_events_older_than(cutoff: float) -> int:
    return _store_or_raise().delete_monitor_events_older_than(cutoff)


def list_monitor_events(limit: int, offset: int, kinds: tuple[str, ...] = ()) -> tuple[list[dict[str, Any]], int]:
    """A page of monitoring events, newest first: of these kinds, or every kind."""
    return _store_or_raise().list_monitor_events(limit, offset, kinds)


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
