from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import claude_key
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
