"""Endpoints for the platform, not for users: Vercel Cron calls them on the hosted version."""

import hmac
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app import monitoring, retention, uploads
from app.core.config import get_settings

router = APIRouter(prefix="/internal", tags=["internal"])


def _require_cron(authorization: str | None = Header(default=None)) -> None:
    """Vercel Cron sends CRON_SECRET as a bearer token. Without one configured the endpoints don't
    exist, so a self-hosted server doesn't expose them."""
    secret = get_settings().cron_secret
    if not secret:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not Found")
    if not hmac.compare_digest((authorization or "").encode(), f"Bearer {secret}".encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Only Vercel Cron may call this endpoint")


@router.post("/retention", dependencies=[Depends(_require_cron)])
async def sweep_retention() -> dict:
    swept = {"deleted": retention.sweep_once()}
    if uploads.store_kind() == "blob":
        # Uploads no scan will read: its queueing failed, or the scan was deleted first.
        swept["stale_uploads"] = await uploads.sweep_stale_blobs()
    return swept


class WebEvent(BaseModel):
    # Only what the web app sees and the API doesn't: scan submissions BotID refused.
    kind: Literal["bot_refused"]
    # Refusals since the web app's last report (server/utils/botId.ts batches them).
    count: int = Field(default=1, ge=1, le=10_000)


@router.post("/events", status_code=204, dependencies=[Depends(_require_cron)])
def record_web_event(event: WebEvent) -> None:
    """A monitoring event from the web app (app/monitoring.py), which may raise an alert."""
    monitoring.record(monitoring.BOT_REFUSED, count=event.count)
