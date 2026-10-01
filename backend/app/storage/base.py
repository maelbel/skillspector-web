from __future__ import annotations

from typing import Any, Protocol

from app.ai_review import ai_review_status
from app.ai_usage import token_totals

# A scan as a plain dict keyed by column name, with `result` already decoded from JSON.
ScanRow = dict[str, Any]

# Columns `list_scans` returns: everything except the (large) result.
SUMMARY_COLUMNS = "id, target, status, created_at, finished_at, error, risk_score, severity, recommendation, ai_review, owner_id"


class ScanStore(Protocol):
    """Where scans and app settings live. SQLite by default; Postgres when a database URL is set."""

    def close(self) -> None: ...

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
    ) -> None: ...

    def update_scan(
        self,
        *,
        id: str,
        status: str,
        finished_at: float | None,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> None: ...

    def fail_unfinished_scans(self, *, error: str, finished_at: float) -> int: ...

    def count_active_scans(self, *, owner_id: str | None = None) -> int:
        """Scans pending or running; with owner_id, only that user's."""
        ...

    def ai_token_totals(self, *, since: float, owner_id: str | None = None) -> dict[str, int]:
        """AI tokens of scans created since then, still in history; with owner_id, only that user's.
        Keys: scans (with AI usage recorded), input_tokens, output_tokens, cached_tokens."""
        ...

    def get_scan(self, id: str) -> ScanRow | None: ...

    def delete_scan(self, id: str) -> bool: ...

    def delete_scans_older_than(self, cutoff: float) -> int: ...

    def get_retention_days(self) -> float | None: ...

    def set_retention_days(self, value: float | None) -> None: ...

    def list_scans(self, limit: int, offset: int, *, owner_id: str | None = None) -> tuple[list[ScanRow], int]:
        """Newest first. With owner_id, only that user's scans."""
        ...

    # Scan logs and progress, for the database log store (app/scan_logs.py).

    def append_log_line(self, scan_id: str, line: str, *, keep: int) -> None: ...

    def get_log_lines(self, scan_id: str) -> list[str]: ...

    def increment_progress(self, scan_id: str) -> None: ...

    def get_progress(self, scan_id: str) -> int: ...

    def clear_logs(self, scan_id: str) -> None: ...

    # Accounts and sessions (app/auth).

    def create_user(self, *, id: str, email: str, password_hash: str, role: str, created_at: float) -> None: ...

    def create_first_user(self, *, id: str, email: str, password_hash: str, role: str, created_at: float) -> bool: ...

    def get_user(self, id: str) -> dict[str, Any] | None: ...

    def get_user_by_email(self, email: str) -> dict[str, Any] | None: ...

    def list_users(self, *, query: str | None = None) -> list[dict[str, Any]]:
        """Users with their scan counts, oldest first; `query` filters by email."""
        ...

    def count_users(self) -> int: ...

    def delete_user(self, id: str) -> bool: ...

    def create_session(self, *, token_hash: str, user_id: str, created_at: float, expires_at: float) -> None: ...

    def get_session_user(self, token_hash: str, *, now: float) -> dict[str, Any] | None: ...

    def delete_session(self, token_hash: str) -> None: ...

    def delete_expired_sessions(self, now: float) -> int: ...

    def set_password_hash(self, user_id: str, password_hash: str) -> None: ...

    def delete_sessions_for_user(self, user_id: str, *, keep_token_hash: str | None = None) -> None: ...

    def create_password_reset(self, *, token_hash: str, user_id: str, created_at: float, expires_at: float) -> None: ...

    def consume_password_reset(self, token_hash: str, *, now: float) -> str | None: ...

    # Backoffice.

    def update_user(self, user_id: str, *, role: str | None = None, status: str | None = None) -> None: ...

    def record_login(self, user_id: str, at: float) -> None: ...

    def count_active_admins(self) -> int: ...

    def get_allow_signup(self) -> bool | None:
        """The admin's sign-up setting, or None when it was never changed."""
        ...

    def set_allow_signup(self, value: bool | None) -> None: ...

    def get_scan_limits(self) -> dict[str, Any]:
        """The admin's scan settings: `scans_paused`, `daily_scan_quota` and `concurrent_scan_quota`,
        each None when never changed. A quota of 0 means no limit."""
        ...

    def set_scan_limits(
        self, *, scans_paused: bool | None, daily_scan_quota: int | None, concurrent_scan_quota: int | None
    ) -> None: ...

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
    ) -> None: ...

    def list_audit(self, limit: int, offset: int, *, target_id: str | None = None) -> tuple[list[dict[str, Any]], int]: ...

    def overview_stats(self, *, since: float) -> dict[str, Any]: ...

    # Stored AI provider keys and per-scan one-off keys, both encrypted by the caller.

    def set_llm_credential(
        self, *, user_id: str, provider: str, encrypted_key: str, key_hint: str, now: float
    ) -> None: ...

    def get_llm_credential(self, user_id: str) -> dict[str, Any] | None: ...

    def delete_llm_credential(self, user_id: str) -> bool: ...

    def put_scan_secret(self, *, scan_id: str, encrypted_key: str, now: float) -> None: ...

    def get_scan_secret(self, scan_id: str) -> str | None: ...

    def delete_scan_secret(self, scan_id: str) -> None: ...



def summary_columns(result: dict[str, Any] | None) -> tuple[Any, ...]:
    """The summary columns denormalised from a report, so history and usage don't need to load it."""
    risk = (result or {}).get("risk_assessment") or {}
    return risk.get("score"), risk.get("severity"), risk.get("recommendation"), ai_review_status(result), *token_totals(result)

    def count_rate_limit_hits(self, key: str, *, window_seconds: float, now: float) -> int:
        """Hits recorded for key within the window."""

    def rate_limit_hit(self, key: str, *, limit: int, window_seconds: float, now: float) -> float | None:
        """Record a hit for key if fewer than `limit` fell within the window; None when recorded,
        otherwise seconds until one frees up. Expired hits of every key are dropped on the way."""
