import time

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app import auth, db
from app.api.routes.users import ActivityEntry
from app.auth.deps import AdminViewer

router = APIRouter(prefix="/admin", tags=["admin"])

_WEEK_SECONDS = 7 * 86400


class UserStats(BaseModel):
    total: int
    admins: int
    suspended: int
    new: int


class ScanStats(BaseModel):
    total: int
    recent: int
    do_not_install: int
    caution: int
    safe: int
    failed: int
    active: int


class Overview(BaseModel):
    auth: str
    email_enabled: bool
    signup_allowed: bool
    # "new" and "recent" count the last 7 days.
    users: UserStats
    scans: ScanStats
    recent_activity: list[ActivityEntry]


class ActivityPage(BaseModel):
    items: list[ActivityEntry]
    total: int


@router.get("/overview", response_model=Overview)
def read_overview(viewer: AdminViewer) -> Overview:
    stats = db.overview_stats(since=time.time() - _WEEK_SECONDS)
    activity, _ = db.list_audit(8, 0)
    return Overview(
        auth=auth.auth_mode(),
        email_enabled=auth.email_enabled(),
        signup_allowed=auth.signup_allowed(),
        users=UserStats(**stats["users"]),
        scans=ScanStats(**stats["scans"]),
        recent_activity=[ActivityEntry(**entry) for entry in activity],
    )


@router.get("/activity", response_model=ActivityPage)
def read_activity(
    viewer: AdminViewer,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ActivityPage:
    rows, total = db.list_audit(limit, offset)
    return ActivityPage(items=[ActivityEntry(**row) for row in rows], total=total)
