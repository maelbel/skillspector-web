"""Optional user accounts.

SKILLSPECTOR_WEB_AUTH picks the mode: `none` (the self-hosted default: no sign-in, everyone may use
every page, including /admin) or `accounts` (sign-in required, scans belong to the user who ran
them, and an `admin` role replaces the old admin token). Hosted mode always uses accounts.
"""

from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Any, Literal

from app import db
from app.auth.passwords import (
    MIN_PASSWORD_LENGTH,
    dummy_hash,
    hash_password,
    verify_password,
)
from app.core.config import Settings, get_settings
from app.core.mode import Mode

AuthMode = Literal["none", "accounts"]
Role = Literal["admin", "user"]


def auth_mode(settings: Settings | None = None) -> AuthMode:
    """SKILLSPECTOR_WEB_AUTH when set, otherwise the mode's default."""
    settings = settings or get_settings()
    if settings.auth:
        return settings.auth
    return "accounts" if settings.mode is Mode.HOSTED else "none"


def signup_allowed(settings: Settings | None = None) -> bool:
    """Whether anyone may create an account. Off when self-hosted: the admin adds users."""
    settings = settings or get_settings()
    if auth_mode(settings) != "accounts":
        return False
    if settings.allow_signup is not None:
        return settings.allow_signup
    return settings.mode is Mode.HOSTED


class AuthError(Exception):
    """A sign-in or account request that can't be honoured; the message is shown to the user."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def normalize_email(email: str) -> str:
    email = email.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@") or len(email) > 254:
        raise AuthError("Enter a valid email address")
    return email


def check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Use at least {MIN_PASSWORD_LENGTH} characters for the password")


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {"id": user["id"], "email": user["email"], "role": user["role"], "created_at": user["created_at"]}


def _new_user_fields(email: str, password: str, role: Role) -> dict[str, Any]:
    email = normalize_email(email)
    check_password(password)
    return {
        "id": uuid.uuid4().hex,
        "email": email,
        "password_hash": hash_password(password),
        "role": role,
        "created_at": time.time(),
    }


def create_first_admin(email: str, password: str) -> dict[str, Any]:
    fields = _new_user_fields(email, password, "admin")
    if not db.create_first_user(**fields):
        raise AuthError("This server already has an admin", status_code=409)
    return fields


def create_user(email: str, password: str, role: Role = "user") -> dict[str, Any]:
    fields = _new_user_fields(email, password, role)
    if db.get_user_by_email(fields["email"]):
        raise AuthError("An account with this email already exists", status_code=409)
    db.create_user(**fields)
    return fields


def authenticate(email: str, password: str) -> dict[str, Any]:
    try:
        email = normalize_email(email)
    except AuthError:
        email = ""
    user = db.get_user_by_email(email) if email else None
    # Verify against a dummy hash for unknown emails, so timing doesn't reveal which exist.
    if not verify_password(password, user["password_hash"] if user else dummy_hash()) or user is None:
        raise AuthError("Wrong email or password", status_code=401)
    return user


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(user_id: str) -> tuple[str, float]:
    """A new session token and when it expires. Only the token's hash is stored, so a leaked
    database can't be replayed."""
    now = time.time()
    db.delete_expired_sessions(now)
    token = secrets.token_urlsafe(32)
    expires_at = now + get_settings().session_days * 86400
    db.create_session(token_hash=_token_hash(token), user_id=user_id, created_at=now, expires_at=expires_at)
    return token, expires_at


def user_for_token(token: str) -> dict[str, Any] | None:
    return db.get_session_user(_token_hash(token), now=time.time())


def end_session(token: str) -> None:
    db.delete_session(_token_hash(token))


@dataclass(frozen=True)
class Viewer:
    """Who is making a request, and what that lets them see."""

    user: dict[str, Any] | None
    is_admin: bool

    @property
    def user_id(self) -> str | None:
        return self.user["id"] if self.user else None

    def can_see(self, scan: dict[str, Any]) -> bool:
        return self.is_admin or (self.user is not None and scan.get("owner_id") == self.user["id"])


# Without accounts every visitor has full access, as before accounts existed.
ANONYMOUS_ADMIN = Viewer(user=None, is_admin=True)
