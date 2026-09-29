from __future__ import annotations

from typing import Any, Protocol

# A scan as a plain dict keyed by column name, with `result` already decoded from JSON.
ScanRow = dict[str, Any]

# Columns `list_scans` returns: everything except the (large) result.
SUMMARY_COLUMNS = "id, target, status, created_at, finished_at, error, risk_score, severity, recommendation"


class ScanStore(Protocol):
    """Where scans and app settings live. SQLite by default; Postgres when a database URL is set."""

    def close(self) -> None: ...

    def insert_scan(self, *, id: str, target: str, status: str, created_at: float, provider: str | None) -> None: ...

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

    def get_scan(self, id: str) -> ScanRow | None: ...

    def delete_scan(self, id: str) -> bool: ...

    def delete_scans_older_than(self, cutoff: float) -> int: ...

    def get_retention_days(self) -> float | None: ...

    def set_retention_days(self, value: float | None) -> None: ...

    def list_scans(self, limit: int, offset: int) -> tuple[list[ScanRow], int]: ...


def risk_columns(result: dict[str, Any] | None) -> tuple[Any, Any, Any]:
    """The summary columns denormalised from a report, so history can list scans without it."""
    risk = (result or {}).get("risk_assessment") or {}
    return risk.get("score"), risk.get("severity"), risk.get("recommendation")
