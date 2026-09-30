"""Scan quotas, and the switch that pauses new scans.

Signed-in users other than admins get a number of scans per rolling 24 hours, and a number that
may be pending or running at once. The defaults come from the settings: no limits self-hosted,
HOSTED_DAILY_QUOTA and HOSTED_CONCURRENT_QUOTA when hosted. Admins change them, and pause new scans
for everyone, from the backoffice, without a redeploy.

Daily scans are counted in the database (`rate_limit_hits`) whatever the rate-limit store, so the
count survives restarts and is shared by every instance, and deleting a scan doesn't give it back.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import HTTPException

from app import db, rate_limit
from app.core.config import get_settings
from app.core.mode import Mode

if TYPE_CHECKING:
    from app.auth import Viewer

HOSTED_DAILY_QUOTA = 10
HOSTED_CONCURRENT_QUOTA = 2

_DAY_SECONDS = 86400.0


@dataclass(frozen=True)
class ScanLimits:
    paused: bool
    # None: no limit.
    daily: int | None
    concurrent: int | None


def _limit(stored: int | None, configured: int | None, hosted_default: int) -> int | None:
    if stored is None:
        stored = configured
    if stored is None:
        stored = hosted_default if get_settings().mode is Mode.HOSTED else 0
    return stored or None


def current() -> ScanLimits:
    settings = get_settings()
    stored = db.get_scan_limits()
    return ScanLimits(
        paused=bool(stored["scans_paused"]),
        daily=_limit(stored["daily_scan_quota"], settings.daily_scan_quota, HOSTED_DAILY_QUOTA),
        concurrent=_limit(stored["concurrent_scan_quota"], settings.concurrent_scan_quota, HOSTED_CONCURRENT_QUOTA),
    )


def save(limits: ScanLimits) -> None:
    db.set_scan_limits(
        scans_paused=limits.paused,
        daily_scan_quota=limits.daily or 0,
        concurrent_scan_quota=limits.concurrent or 0,
    )


def applies_to(viewer: Viewer) -> bool:
    """Admins run the server, and without accounts there's no one to count against."""
    return viewer.user_id is not None and not viewer.is_admin


def _daily_key(user_id: str) -> str:
    return f"quota:day:{user_id}"


@dataclass(frozen=True)
class Usage:
    limits: ScanLimits
    applies: bool
    scans_today: int
    active_scans: int


def usage(viewer: Viewer) -> Usage:
    limits = current()
    if not applies_to(viewer):
        return Usage(limits=limits, applies=False, scans_today=0, active_scans=0)
    return Usage(
        limits=limits,
        applies=True,
        scans_today=db.count_rate_limit_hits(_daily_key(viewer.user_id), window_seconds=_DAY_SECONDS, now=time.time()),
        active_scans=db.count_active_scans(owner_id=viewer.user_id),
    )


def ensure_not_paused(limits: ScanLimits) -> None:
    if limits.paused:
        raise HTTPException(status_code=503, detail="New scans are paused on this server — try again later")


def enforce(viewer: Viewer, limits: ScanLimits) -> None:
    """Refuse a scan beyond the viewer's quotas, or count it towards today's."""
    if not applies_to(viewer):
        return
    if limits.concurrent is not None and db.count_active_scans(owner_id=viewer.user_id) >= limits.concurrent:
        running = f"{limits.concurrent} scan{'s' if limits.concurrent != 1 else ''}"
        raise HTTPException(status_code=429, detail=f"You already have {running} in progress — wait for one to finish")
    if limits.daily is not None:
        retry_after = db.rate_limit_hit(
            _daily_key(viewer.user_id), limit=limits.daily, window_seconds=_DAY_SECONDS, now=time.time()
        )
        if retry_after is not None:
            plural = "s" if limits.daily != 1 else ""
            rate_limit.refuse(retry_after, f"You've used your {limits.daily} scan{plural} for the last 24 hours")
