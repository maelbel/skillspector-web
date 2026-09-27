from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app import rate_limit
from app.core.config import get_settings
from app.core.security import require_admin


@pytest.fixture(autouse=True)
def admin_token(monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_token", "s3cret-tøken")
    monkeypatch.setattr(rate_limit, "_hits", rate_limit.OrderedDict())


def _request() -> Request:
    return Request({"type": "http", "headers": [], "client": ("203.0.113.7", 1234)})


def test_accepts_the_configured_token():
    require_admin(_request(), x_admin_token="s3cret-tøken")


@pytest.mark.parametrize("token", [None, "", "wrong", "s3cret-tøken-but-longer", "✗"])
def test_rejects_missing_or_wrong_tokens(token):
    with pytest.raises(HTTPException) as exc:
        require_admin(_request(), x_admin_token=token)
    assert exc.value.status_code == 401


def test_admin_actions_disabled_without_a_configured_token(monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_token", None)
    with pytest.raises(HTTPException) as exc:
        require_admin(_request(), x_admin_token="anything")
    assert exc.value.status_code == 404
