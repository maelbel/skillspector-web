import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import claude_key, db, quotas
from app.auth import AuthError
from app.auth.deps import CurrentViewer

router = APIRouter(prefix="/account", tags=["account"])


class ClaudeKeyStatus(BaseModel):
    provider: str
    # The last characters of the key, e.g. "…a1b2"; the key itself is never returned.
    hint: str
    updated_at: float


class ConnectClaudeRequest(BaseModel):
    api_key: str


# How far back the account page adds up AI tokens.
AI_USAGE_DAYS = 30


class AIUsage(BaseModel):
    """AI tokens over the last AI_USAGE_DAYS days, from scans still in history."""

    days: int
    scans: int
    input_tokens: int
    output_tokens: int
    cached_tokens: int


def ai_usage(owner_id: str | None) -> AIUsage:
    totals = db.ai_token_totals(since=time.time() - AI_USAGE_DAYS * 86400, owner_id=owner_id)
    return AIUsage(days=AI_USAGE_DAYS, **totals)


class UsageResponse(BaseModel):
    scans_paused: bool
    # False for admins, and without accounts: no quota applies to them.
    quotas_apply: bool
    # Scans started in the last 24 hours, including deleted ones.
    scans_today: int
    daily_scan_quota: int | None
    active_scans: int
    concurrent_scan_quota: int | None
    # Everyone's, without accounts.
    ai_usage: AIUsage


def _signed_in_user(viewer) -> dict:
    if viewer.user is None or not claude_key.available():
        raise HTTPException(status_code=404, detail="Saving a Claude key isn't available on this server")
    return viewer.user


@router.get("/claude", response_model=ClaudeKeyStatus | None)
def read_claude_key(viewer: CurrentViewer) -> ClaudeKeyStatus | None:
    status = claude_key.status(_signed_in_user(viewer)["id"])
    return ClaudeKeyStatus(**status) if status else None


@router.put("/claude", response_model=ClaudeKeyStatus)
def connect_claude(req: ConnectClaudeRequest, viewer: CurrentViewer) -> ClaudeKeyStatus:
    """Check the key with Anthropic, then save it encrypted, replacing any earlier one."""
    try:
        return ClaudeKeyStatus(**claude_key.connect(_signed_in_user(viewer), req.api_key))
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.delete("/claude", status_code=204)
def disconnect_claude(viewer: CurrentViewer) -> None:
    claude_key.disconnect(_signed_in_user(viewer))


@router.get("/usage", response_model=UsageResponse)
def read_usage(viewer: CurrentViewer) -> UsageResponse:
    usage = quotas.usage(viewer)
    return UsageResponse(
        scans_paused=usage.limits.paused,
        quotas_apply=usage.applies,
        scans_today=usage.scans_today,
        daily_scan_quota=usage.limits.daily,
        active_scans=usage.active_scans,
        concurrent_scan_quota=usage.limits.concurrent,
        ai_usage=ai_usage(viewer.user_id),
    )
