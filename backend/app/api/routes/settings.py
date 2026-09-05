from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator

from app import retention
from app.core.security import require_admin

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    scan_retention_days: float | None


class UpdateSettingsRequest(BaseModel):
    scan_retention_days: float | None

    @field_validator("scan_retention_days")
    @classmethod
    def validate_positive(cls, value: float | None) -> float | None:
        if value is not None and value <= 0:
            raise ValueError("scan_retention_days must be positive, or null to keep scans forever")
        return value


@router.get("", response_model=SettingsResponse)
async def read_settings() -> SettingsResponse:
    return SettingsResponse(scan_retention_days=retention.get_retention_days())


@router.put("", response_model=SettingsResponse, dependencies=[Depends(require_admin)])
async def update_settings(req: UpdateSettingsRequest) -> SettingsResponse:
    retention.set_retention_days(req.scan_retention_days)
    return SettingsResponse(scan_retention_days=retention.get_retention_days())
