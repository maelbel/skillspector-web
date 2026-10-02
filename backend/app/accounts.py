"""Deleting an account, by its owner (Account page) or an admin: everything of theirs goes.

Their scans with their reports, logs and uploads; their sessions, password reset links, API tokens,
saved Claude key and code host connections (revoked at GitHub first); and their email and details
in the activity log, whose entries keep only ids that no longer lead to anyone. What's left is one
entry saying an account was deleted, by whom when an admin did it.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app import db, repo_connections, uploads
from app.auth import AuthError, audit, verify_password


async def delete_account(actor: dict[str, Any], user_id: str, *, password: str | None = None) -> None:
    """Delete the account user_id. Its owner deletes their own with their password; an admin
    deletes anyone else's. The last active admin's can't be deleted."""
    user = db.get_user(user_id)
    if user is None:
        raise AuthError("user not found", 404)
    own = user_id == actor["id"]
    if own and not verify_password(password or "", user["password_hash"]):
        raise AuthError("Wrong password", 403)
    if not own and password is not None:
        raise AuthError("Only the account's owner deletes it with a password", 400)
    if user["role"] == "admin" and user["status"] == "active" and db.count_active_admins() <= 1:
        raise AuthError("Keep at least one active admin: make someone else an admin first", 409)
    # While its token is still here to revoke.
    await asyncio.to_thread(repo_connections.disconnect, user)
    held = db.delete_user(user_id)
    if held is None:
        raise AuthError("user not found", 404)
    for ref in held:
        await uploads.delete(ref)
    # Nothing that names them: an admin's entry says who deleted an account, not whose.
    audit(None if own else actor, "account.deleted" if own else "user.deleted", {"id": user_id, "email": None})
