import time

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app import auth, db, monitoring
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


class HealthError(BaseModel):
    kind: str
    message: str | None
    at: float
    scan_id: str | None


class HealthAlert(BaseModel):
    rule: str | None
    at: float


class Health(BaseModel):
    """What went wrong over the last `hours` (app/monitoring.py)."""

    hours: int
    finished: int
    failed: int
    sandbox_errors: int
    redeliveries: int
    bot_refusals: int
    last_error: HealthError | None
    # Where alerts go: "webhook", "email"; empty when they aren't set up.
    alert_channels: list[str]
    last_alert: HealthAlert | None


class Overview(BaseModel):
    auth: str
    email_enabled: bool
    signup_allowed: bool
    # "new" and "recent" count the last 7 days.
    users: UserStats
    scans: ScanStats
    recent_activity: list[ActivityEntry]
    health: Health


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
        health=Health(**monitoring.health()),
    )


class AlertTestResponse(BaseModel):
    channels: list[str]


@router.post("/alerts/test", response_model=AlertTestResponse)
def send_test_alert(viewer: AdminViewer) -> AlertTestResponse:
    """Send a test alert to every channel set up, to check they're reached."""
    if not monitoring.channels():
        raise HTTPException(status_code=409, detail="Alerts aren't set up: set SKILLSPECTOR_WEB_ALERT_WEBHOOK_URL or SKILLSPECTOR_WEB_ALERT_EMAIL")
    sent = monitoring.send_alert("Test alert", "Alerts from this server reach you here.")
    if not sent:
        raise HTTPException(status_code=502, detail="The alert couldn't be sent: the server's log has why")
    return AlertTestResponse(channels=sent)


@router.get("/activity", response_model=ActivityPage)
def read_activity(
    viewer: AdminViewer,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ActivityPage:
    rows, total = db.list_audit(limit, offset)
    return ActivityPage(items=[ActivityEntry(**row) for row in rows], total=total)
