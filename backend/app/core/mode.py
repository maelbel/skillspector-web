"""Deployment modes.

One codebase serves two deployments: ``self_hosted`` (the default: one long-lived process with
SQLite, an in-process scan queue and in-memory logs) and ``hosted`` (Vercel). Each pluggable piece
picks its implementation from the mode as its hosted version lands.
"""

from __future__ import annotations

from enum import StrEnum


class Mode(StrEnum):
    SELF_HOSTED = "self_hosted"
    HOSTED = "hosted"


# Hosted-mode pieces that don't exist yet, with the issue tracking each. Remove an entry when its
# hosted implementation lands; until this is empty, `hosted` refuses to start rather than half-work.
HOSTED_NOT_IMPLEMENTED: dict[str, str] = {
    "scan storage": "#41",
    "durable job runner": "#42",
    "shared log and progress store": "#43",
    "sandboxed scan execution": "#44",
    "user accounts": "#45",
    "per-user Claude connection": "#46",
    "shared rate limiting": "#47",
    "scheduled retention": "#48",
}


class ModeConfigError(RuntimeError):
    """The configured mode can't run with the current code or settings."""


def check_mode(mode: Mode) -> None:
    """Fail fast at startup when the mode is missing something it needs."""
    if mode is Mode.HOSTED and HOSTED_NOT_IMPLEMENTED:
        missing = ", ".join(f"{piece} ({issue})" for piece, issue in HOSTED_NOT_IMPLEMENTED.items())
        raise ModeConfigError(
            f"SKILLSPECTOR_WEB_MODE=hosted isn't usable yet. Still missing: {missing}. "
            "Use SKILLSPECTOR_WEB_MODE=self_hosted (the default)."
        )
