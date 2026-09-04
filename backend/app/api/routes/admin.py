from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.claude_login import complete_claude_login, start_claude_login
from app.core.config import get_settings


def _require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.admin_token:
        raise HTTPException(status_code=404, detail="admin actions are not enabled")
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="invalid admin token")


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(_require_admin)])


class ClaudeLoginStartResponse(BaseModel):
    url: str


class ClaudeLoginCompleteRequest(BaseModel):
    code: str


class ClaudeLoginCompleteResponse(BaseModel):
    success: bool
    output: str


@router.post("/claude-login/start", response_model=ClaudeLoginStartResponse)
async def claude_login_start() -> ClaudeLoginStartResponse:
    try:
        url = await start_claude_login()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ClaudeLoginStartResponse(url=url)


@router.post("/claude-login/complete", response_model=ClaudeLoginCompleteResponse)
async def claude_login_complete(req: ClaudeLoginCompleteRequest) -> ClaudeLoginCompleteResponse:
    try:
        success, output = await complete_claude_login(req.code)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ClaudeLoginCompleteResponse(success=success, output=output)
