from fastapi import Header, HTTPException, Request

from app import rate_limit
from app.core.config import get_settings


def require_admin(request: Request, x_admin_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.admin_token:
        raise HTTPException(status_code=404, detail="admin actions are not enabled")

    key = f"admin:{rate_limit.client_key(request)}"
    if not rate_limit.check(key, settings.admin_rate_limit, settings.admin_rate_limit_window_seconds):
        raise HTTPException(status_code=429, detail="Too many admin attempts from this address — try again shortly")

    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="invalid admin token")
