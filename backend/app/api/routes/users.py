from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app import auth, db
from app.api.routes.auth import UserResponse
from app.auth.deps import AdminViewer

router = APIRouter(prefix="/admin/users", tags=["admin"])


def _require_accounts() -> None:
    if auth.auth_mode() != "accounts":
        raise HTTPException(status_code=404, detail="Accounts aren't enabled on this server")


def _raise(exc: auth.AuthError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


class DirectoryUser(UserResponse):
    scan_count: int


class RecentScan(BaseModel):
    id: str
    target: str
    status: str
    created_at: float
    recommendation: str | None
    risk_score: float | None


class ActivityEntry(BaseModel):
    id: int
    created_at: float
    actor_id: str | None
    actor_email: str | None
    action: str
    target_id: str | None
    target_email: str | None
    detail: str | None


class UserDetail(BaseModel):
    user: DirectoryUser
    recent_scans: list[RecentScan]
    activity: list[ActivityEntry]


class CreateUserRequest(BaseModel):
    email: str
    password: str
    role: Literal["admin", "user"] = "user"


class UpdateUserRequest(BaseModel):
    role: Literal["admin", "user"] | None = None
    status: Literal["active", "suspended"] | None = None


class ResetLinkResponse(BaseModel):
    # Relative to the web app, e.g. /reset-password?token=…; the web proxy makes it absolute.
    path: str
    expires_at: float


def _user_or_404(user_id: str) -> dict:
    user = db.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    _, scan_count = db.list_scans(1, 0, owner_id=user_id)
    return {**auth.public_user(user), "scan_count": scan_count}


@router.get("", response_model=list[DirectoryUser], dependencies=[Depends(_require_accounts)])
def list_users(viewer: AdminViewer, query: str | None = Query(default=None, max_length=254)) -> list[DirectoryUser]:
    return [DirectoryUser(**user) for user in db.list_users(query=query.strip() if query else None)]


@router.get("/{user_id}", response_model=UserDetail, dependencies=[Depends(_require_accounts)])
def read_user(user_id: str, viewer: AdminViewer) -> UserDetail:
    user = _user_or_404(user_id)
    scans, _ = db.list_scans(5, 0, owner_id=user_id)
    activity, _ = db.list_audit(20, 0, target_id=user_id)
    return UserDetail(
        user=DirectoryUser(**user),
        recent_scans=[RecentScan(**scan) for scan in scans],
        activity=[ActivityEntry(**entry) for entry in activity],
    )


@router.post("", response_model=UserResponse, status_code=201, dependencies=[Depends(_require_accounts)])
def create_user(req: CreateUserRequest, viewer: AdminViewer) -> UserResponse:
    try:
        return UserResponse(**auth.public_user(auth.create_user(req.email, req.password, req.role, by=viewer.user)))
    except auth.AuthError as exc:
        raise _raise(exc) from exc


@router.patch("/{user_id}", response_model=UserResponse, dependencies=[Depends(_require_accounts)])
def update_user(user_id: str, req: UpdateUserRequest, viewer: AdminViewer) -> UserResponse:
    """Change a user's role, or suspend (signed out, can't sign in) or reactivate them."""
    try:
        return UserResponse(**auth.public_user(auth.update_user(viewer.user, user_id, role=req.role, status=req.status)))
    except auth.AuthError as exc:
        raise _raise(exc) from exc


@router.post("/{user_id}/reset", response_model=ResetLinkResponse, dependencies=[Depends(_require_accounts)])
def create_reset_link(user_id: str, viewer: AdminViewer) -> ResetLinkResponse:
    """A one-time link to choose a new password, for the admin to pass on; cancels earlier links."""
    user = _user_or_404(user_id)
    token, expires_at = auth.issue_password_reset(user_id)
    auth.audit(viewer.user, "password.reset_link_created", user)
    return ResetLinkResponse(path=auth.reset_link_path(token), expires_at=expires_at)


@router.post("/{user_id}/reset-email", status_code=204, dependencies=[Depends(_require_accounts)])
def send_reset_email(user_id: str, viewer: AdminViewer) -> None:
    if not auth.email_enabled():
        raise HTTPException(status_code=409, detail="Email isn't configured on this server")
    user = _user_or_404(user_id)
    try:
        auth.send_reset_email(user, by=viewer.user)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="The email couldn't be sent; check the SMTP settings") from exc


@router.delete("/{user_id}", status_code=204, dependencies=[Depends(_require_accounts)])
def delete_user(user_id: str, viewer: AdminViewer) -> None:
    try:
        auth.delete_user(viewer.user, user_id)
    except auth.AuthError as exc:
        raise _raise(exc) from exc
