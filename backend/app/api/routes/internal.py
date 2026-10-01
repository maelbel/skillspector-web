"""Endpoints for the platform, not for users: Vercel Cron calls them on the hosted version."""

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app import retention, uploads
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
