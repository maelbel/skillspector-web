from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app


@pytest.fixture
def client(temp_db, fake_runner, monkeypatch):
    client = TestClient(app)
    client.scheduled = fake_runner.submitted
    return client


def _insert(id: str, created_at: float, status: str = "done") -> None:
    db.insert_scan(id=id, target=f"https://example.com/{id}", status=status, created_at=created_at, provider=None)


def test_start_scan_queues_a_pending_job(client):
    response = client.post("/scan", json={"target": "  https://example.com/skill.zip  "})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert [job.id for job in client.scheduled] == [body["id"]]
    assert client.scheduled[0].target == "https://example.com/skill.zip"


def test_a_github_file_link_is_scanned_as_the_raw_file(client):
    response = client.post("/scan", json={"target": "https://github.com/anthropics/skills/blob/main/skills/pdf/SKILL.md"})

    raw = "https://raw.githubusercontent.com/anthropics/skills/main/skills/pdf/SKILL.md"
    assert client.scheduled[0].target == raw
    # The history shows what was scanned.
    assert client.get(f"/scan/{response.json()['id']}").json()["target"] == raw


@pytest.mark.parametrize("target", ["", "   ", "file:///etc/passwd", "/local/path", "ftp://example.com/x"])
def test_start_scan_rejects_non_http_targets(client, target):
    response = client.post("/scan", json={"target": target})

    assert response.status_code == 422
    assert client.scheduled == []


def test_start_scan_requires_an_api_key_for_hosted_providers(client):
    response = client.post("/scan", json={"target": "https://example.com/x", "llm": {"provider": "openai"}})

    assert response.status_code == 422


def test_start_scan_is_rate_limited_per_client(client):
    statuses = [client.post("/scan", json={"target": "https://example.com/x"}).status_code for _ in range(6)]

    assert statuses == [200] * 5 + [429]


def test_history_is_newest_first_and_paginated(client):
    for i in range(3):
        _insert(f"scan-{i}", created_at=float(i))

    response = client.get("/scan", params={"limit": 2, "offset": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert [item["id"] for item in body["items"]] == ["scan-2", "scan-1"]


def test_read_scan_returns_the_stored_job(client):
    _insert("abc", created_at=1.0, status="running")

    response = client.get("/scan/abc")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_a_failed_ai_review_is_reported_on_the_scan_and_in_history(client):
    _insert("ai", created_at=1.0)
    report = {"risk_assessment": {}, "metadata": {"llm_requested": True, "llm_calls_succeeded": 0, "llm_error": "bad key"}}
    db.update_scan(id="ai", status="done", finished_at=2.0, result=report, error=None)

    assert client.get("/scan/ai").json()["ai_review"] == "failed"
    assert client.get("/scan").json()["items"][0]["ai_review"] == "failed"


def test_unknown_scan_is_404_for_read_and_delete(client):
    assert client.get("/scan/missing").status_code == 404
    assert client.delete("/scan/missing").status_code == 404


def test_delete_scan_removes_it(client):
    _insert("abc", created_at=1.0)

    assert client.delete("/scan/abc").status_code == 204
    assert db.get_scan("abc") is None


def test_logs_for_unknown_scan_are_not_found(client):
    assert client.get("/scan/missing/logs").status_code == 404
