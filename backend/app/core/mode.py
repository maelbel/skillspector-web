"""Deployment modes.

One codebase serves two deployments: ``self_hosted`` (the default: one long-lived process with
SQLite, an in-process scan queue and in-memory logs) and ``hosted`` (Vercel). Each pluggable piece
picks its implementation from the mode as its hosted version lands.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings


class Mode(StrEnum):
    SELF_HOSTED = "self_hosted"
    HOSTED = "hosted"


# Hosted-mode pieces that don't exist yet, with the issue tracking each. Remove an entry when its
# hosted implementation lands; until this is empty, `hosted` refuses to start rather than half-work.
HOSTED_NOT_IMPLEMENTED: dict[str, str] = {
    "user accounts": "#45",
    "per-user Claude connection": "#46",
    "shared rate limiting": "#47",
    "scheduled retention": "#48",
}


class ModeConfigError(RuntimeError):
    """The configured mode can't run with the current code or settings."""


def check_mode(settings: Settings) -> None:
    """Fail fast at startup when the mode is missing something it needs."""
    if settings.mode is not Mode.HOSTED:
        return

    problems = []
    if not settings.database_url:
        # Vercel has no persistent, shared filesystem for the SQLite file.
        problems.append("set SKILLSPECTOR_WEB_DATABASE_URL to a Postgres database")
    if settings.scan_executor == "local":
        # Untrusted targets must be fetched and analysed in a sandbox, not in the app.
        problems.append("SKILLSPECTOR_WEB_SCAN_EXECUTOR=local isn't allowed; leave it unset")
    elif not settings.sandbox_snapshot_id:
        problems.append("set SKILLSPECTOR_WEB_SANDBOX_SNAPSHOT_ID (build one with `python -m app.sandbox_snapshot`)")
    if settings.log_store == "memory":
        # Scans run in another instance than the one serving their logs.
        problems.append("SKILLSPECTOR_WEB_LOG_STORE=memory can't work across instances; leave it unset")
    if HOSTED_NOT_IMPLEMENTED:
        missing = ", ".join(f"{piece} ({issue})" for piece, issue in HOSTED_NOT_IMPLEMENTED.items())
        problems.append(f"still missing: {missing}")
    if problems:
        raise ModeConfigError(
            f"SKILLSPECTOR_WEB_MODE=hosted isn't usable yet: {'; '.join(problems)}. "
            "Use SKILLSPECTOR_WEB_MODE=self_hosted (the default)."
        )
