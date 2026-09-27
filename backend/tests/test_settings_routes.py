from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import rate_limit
from app.core.config import get_settings
from app.main import app


@pytest.fixture
def client(temp_db, monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_token", "token")
    monkeypatch.setattr(rate_limit, "_hits", rate_limit.OrderedDict())
    return TestClient(app)


def test_settings_are_readable_without_a_token(client):
    response = client.get("/settings")

    assert response.status_code == 200
    assert response.json() == {"scan_retention_days": None}


def test_updating_settings_requires_the_admin_token(client):
    response = client.put("/settings", json={"scan_retention_days": 7})

    assert response.status_code == 401
    assert client.get("/settings").json() == {"scan_retention_days": None}


def test_admin_can_update_retention(client):
    response = client.put("/settings", json={"scan_retention_days": 7}, headers={"X-Admin-Token": "token"})

    assert response.status_code == 200
    assert client.get("/settings").json() == {"scan_retention_days": 7}


@pytest.mark.parametrize("days", [0, -1])
def test_retention_must_be_positive(client, days):
    response = client.put("/settings", json={"scan_retention_days": days}, headers={"X-Admin-Token": "token"})

    assert response.status_code == 422


def test_admin_routes_require_the_admin_token(client):
    assert client.post("/admin/claude-login/start").status_code == 401
    assert client.post("/admin/claude-login/complete", json={"code": "x"}).status_code == 401
