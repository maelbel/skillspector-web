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


class ModeConfigError(RuntimeError):
    """The configured mode can't run with the current code or settings."""


def check_mode(settings: Settings) -> None:
    """Fail fast at startup when the mode is missing something it needs."""
    if settings.mode is not Mode.HOSTED:
        return

    from app.sandbox_snapshot import snapshot_id_for

    problems = []
    if not settings.database_url:
        # Vercel has no persistent, shared filesystem for the SQLite file.
        problems.append("set SKILLSPECTOR_WEB_DATABASE_URL to a Postgres database")
    if settings.scan_executor == "local":
        # Untrusted targets must be fetched and analysed in a sandbox, not in the app.
        problems.append("SKILLSPECTOR_WEB_SCAN_EXECUTOR=local isn't allowed; leave it unset")
    elif not snapshot_id_for(settings):
        problems.append("build a sandbox snapshot with `python -m app.sandbox_snapshot`, or set SKILLSPECTOR_WEB_SANDBOX_SNAPSHOT_ID")
    if settings.auth == "none":
        problems.append("SKILLSPECTOR_WEB_AUTH=none isn't allowed on a public service; leave it unset")
    from app import secrets_box

    if not secrets_box.is_configured(settings):
        problems.append("set SKILLSPECTOR_WEB_SECRET_KEY (generate one with `python -m app.secrets_box`)")
    if settings.log_store == "memory":
        # Scans run in another instance than the one serving their logs.
        problems.append("SKILLSPECTOR_WEB_LOG_STORE=memory can't work across instances; leave it unset")
    if settings.rate_limit_store == "memory":
        # Each instance would count on its own, multiplying every limit.
        problems.append("SKILLSPECTOR_WEB_RATE_LIMIT_STORE=memory can't hold limits across instances; leave it unset")
    if not settings.cron_secret:
        # No background loop runs on Vercel: retention sweeps only when Vercel Cron calls in.
        problems.append("set CRON_SECRET so Vercel Cron can run the retention sweep")
    if problems:
        raise ModeConfigError(
            f"SKILLSPECTOR_WEB_MODE=hosted can't start: {'; '.join(problems)}. "
            "Use SKILLSPECTOR_WEB_MODE=self_hosted (the default)."
        )
