from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from app import auth, db, rate_limit
from app.auth.deps import CurrentViewer, bearer_token
from app.core.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    created_at: float


class SessionResponse(BaseModel):
    auth: str
    user: UserResponse | None
    # Accounts are on but none exists yet: the first visitor creates the admin.
    needs_setup: bool
    signup_allowed: bool


class CredentialsRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    token: str
    expires_at: float
    user: UserResponse


def _rate_limit_login(request: Request) -> None:
    settings = get_settings()
    key = f"login:{rate_limit.client_key(request)}"
    if not rate_limit.check(key, settings.login_rate_limit, settings.login_rate_limit_window_seconds):
        raise HTTPException(status_code=429, detail="Too many attempts from this address — try again shortly")


def _require_accounts() -> None:
    if auth.auth_mode() != "accounts":
        raise HTTPException(status_code=404, detail="Accounts aren't enabled on this server")


def _signed_in(user: dict) -> TokenResponse:
    token, expires_at = auth.start_session(user["id"])
    return TokenResponse(token=token, expires_at=expires_at, user=UserResponse(**auth.public_user(user)))


def _auth_error(exc: auth.AuthError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/session", response_model=SessionResponse)
def read_session(authorization: str | None = Header(default=None)) -> SessionResponse:
    mode = auth.auth_mode()
    if mode == "none":
        return SessionResponse(auth=mode, user=None, needs_setup=False, signup_allowed=False)
    token = bearer_token(authorization)
    user = auth.user_for_token(token) if token else None
    return SessionResponse(
        auth=mode,
        user=UserResponse(**auth.public_user(user)) if user else None,
        needs_setup=db.count_users() == 0,
        signup_allowed=auth.signup_allowed(),
    )


@router.post("/setup", response_model=TokenResponse, dependencies=[Depends(_require_accounts), Depends(_rate_limit_login)])
def first_run_setup(req: CredentialsRequest) -> TokenResponse:
    """Create the first account, as admin. Refused once any account exists."""
    try:
        return _signed_in(auth.create_first_admin(req.email, req.password))
    except auth.AuthError as exc:
        raise _auth_error(exc) from exc


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(_require_accounts), Depends(_rate_limit_login)])
def login(req: CredentialsRequest) -> TokenResponse:
    try:
        return _signed_in(auth.authenticate(req.email, req.password))
    except auth.AuthError as exc:
        raise _auth_error(exc) from exc


@router.post("/signup", response_model=TokenResponse, dependencies=[Depends(_require_accounts), Depends(_rate_limit_login)])
def signup(req: CredentialsRequest) -> TokenResponse:
    if not auth.signup_allowed():
        raise HTTPException(status_code=403, detail="Ask an admin of this server for an account")
    try:
        return _signed_in(auth.create_user(req.email, req.password))
    except auth.AuthError as exc:
        raise _auth_error(exc) from exc


class ResetRequest(BaseModel):
    token: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/reset", response_model=TokenResponse, dependencies=[Depends(_require_accounts), Depends(_rate_limit_login)])
def reset_password(req: ResetRequest) -> TokenResponse:
    """Set a new password from a one-time reset link, and sign in."""
    try:
        return _signed_in(auth.reset_password(req.token, req.password))
    except auth.AuthError as exc:
        raise _auth_error(exc) from exc


@router.post("/password", status_code=204, dependencies=[Depends(_require_accounts), Depends(_rate_limit_login)])
def change_password(req: ChangePasswordRequest, viewer: CurrentViewer, authorization: str | None = Header(default=None)) -> None:
    try:
        auth.change_password(viewer.user_id, req.current_password, req.new_password, current_token=bearer_token(authorization))
    except auth.AuthError as exc:
        raise _auth_error(exc) from exc


@router.post("/logout", status_code=204)
def logout(authorization: str | None = Header(default=None)) -> None:
    token = bearer_token(authorization)
    if token and auth.auth_mode() == "accounts":
        auth.end_session(token)
