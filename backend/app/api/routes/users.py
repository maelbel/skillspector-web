from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import auth, db
from app.api.routes.auth import UserResponse
from app.auth.deps import AdminViewer

router = APIRouter(prefix="/admin/users", tags=["admin"])


def _require_accounts() -> None:
    if auth.auth_mode() != "accounts":
        raise HTTPException(status_code=404, detail="Accounts aren't enabled on this server")


class CreateUserRequest(BaseModel):
    email: str
    password: str
    role: Literal["admin", "user"] = "user"


@router.get("", response_model=list[UserResponse], dependencies=[Depends(_require_accounts)])
def list_users(viewer: AdminViewer) -> list[UserResponse]:
    return [UserResponse(**user) for user in db.list_users()]


@router.post("", response_model=UserResponse, status_code=201, dependencies=[Depends(_require_accounts)])
def create_user(req: CreateUserRequest, viewer: AdminViewer) -> UserResponse:
    try:
        return UserResponse(**auth.public_user(auth.create_user(req.email, req.password, req.role)))
    except auth.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.delete("/{user_id}", status_code=204, dependencies=[Depends(_require_accounts)])
def delete_user(user_id: str, viewer: AdminViewer) -> None:
    if user_id == viewer.user_id:
        raise HTTPException(status_code=409, detail="You can't delete your own account")
    user = db.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    if user["role"] == "admin" and sum(u["role"] == "admin" for u in db.list_users()) <= 1:
        raise HTTPException(status_code=409, detail="Keep at least one admin")
    # Their scans stay, visible to admins only.
    db.delete_user(user_id)
