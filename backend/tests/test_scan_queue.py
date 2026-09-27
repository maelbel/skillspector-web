from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import scanner
from app.api.routes import scan as scan_routes
from app.core.config import get_settings
from app.main import app


@pytest.fixture
def client(temp_db, monkeypatch):
    monkeypatch.setattr(scan_routes, "schedule", lambda job: None)
    return TestClient(app)


def test_scan_is_queued_below_the_cap(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_queued_scans", 2)
    monkeypatch.setattr(scanner, "_tasks", {object()})

    response = client.post("/scan", json={"target": "https://example.com/skill.zip"})

    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_scan_is_rejected_when_the_queue_is_full(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_queued_scans", 2)
    monkeypatch.setattr(scanner, "_tasks", {object(), object()})

    response = client.post("/scan", json={"target": "https://example.com/skill.zip"})

    assert response.status_code == 503
    assert scanner.list_jobs(10, 0)[1] == 0
