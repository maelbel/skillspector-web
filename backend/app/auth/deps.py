"""FastAPI dependencies that resolve the request's Viewer."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException

from app.auth import ANONYMOUS_ADMIN, Viewer, auth_mode, user_for_token


def bearer_token(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return None


def current_viewer(authorization: str | None = Header(default=None)) -> Viewer:
    """Everyone is an admin without accounts; with accounts, a valid session is required."""
    if auth_mode() == "none":
        return ANONYMOUS_ADMIN
    token = bearer_token(authorization)
    user = user_for_token(token) if token else None
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    return Viewer(user=user, is_admin=user["role"] == "admin")


def require_admin(authorization: str | None = Header(default=None)) -> Viewer:
    viewer = current_viewer(authorization)
    if not viewer.is_admin:
        raise HTTPException(status_code=403, detail="Only an admin can do this")
    return viewer


CurrentViewer = Annotated[Viewer, Depends(current_viewer)]
AdminViewer = Annotated[Viewer, Depends(require_admin)]
