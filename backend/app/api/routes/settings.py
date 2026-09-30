from fastapi import APIRouter
from pydantic import BaseModel, field_validator

from app import auth, db, retention
from app.auth.deps import AdminViewer

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    scan_retention_days: float | None
    # Whether visitors may create their own account; always false without accounts.
    allow_signup: bool


class UpdateSettingsRequest(BaseModel):
    """Only the fields sent are changed."""

    scan_retention_days: float | None = None
    allow_signup: bool | None = None

    @field_validator("scan_retention_days")
    @classmethod
    def validate_positive(cls, value: float | None) -> float | None:
        if value is not None and value <= 0:
            raise ValueError("scan_retention_days must be positive, or null to keep scans forever")
        return value


def _current() -> SettingsResponse:
    return SettingsResponse(scan_retention_days=retention.get_retention_days(), allow_signup=auth.signup_allowed())


@router.get("", response_model=SettingsResponse)
async def read_settings() -> SettingsResponse:
    return _current()


@router.put("", response_model=SettingsResponse)
async def update_settings(req: UpdateSettingsRequest, viewer: AdminViewer) -> SettingsResponse:
    sent = req.model_fields_set
    if "scan_retention_days" in sent and req.scan_retention_days != retention.get_retention_days():
        retention.set_retention_days(req.scan_retention_days)
        days = req.scan_retention_days
        auth.audit(viewer.user, "settings.retention_changed", detail="keep forever" if days is None else f"{days:g} days")
    if "allow_signup" in sent and req.allow_signup is not None and req.allow_signup != auth.signup_allowed():
        db.set_allow_signup(req.allow_signup)
        auth.audit(viewer.user, "settings.signup_changed", detail="on" if req.allow_signup else "off")
    return _current()
