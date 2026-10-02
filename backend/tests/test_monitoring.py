from __future__ import annotations

import json
import time

import anyio
import pytest
from fastapi.testclient import TestClient

from app import db, monitoring, retention, scanner
from app.core.config import get_settings
from app.jobs import queue_worker
from app.main import app
from app.sandbox_executor import SnapshotMissingError
from app.scanner import Job

WEBHOOK = "https://hooks.example.com/alert"
SECRET = "cron-secret"


@pytest.fixture
def sent(monkeypatch):
    """Alerts POSTed to the webhook, as their JSON payloads."""
    payloads: list[dict] = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def urlopen(request, timeout):
        assert request.full_url == WEBHOOK
        payloads.append(json.loads(request.data))
        return Response()

    monkeypatch.setattr(monitoring.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(get_settings(), "alert_webhook_url", WEBHOOK)
    monkeypatch.setattr(get_settings(), "alert_email", None)
    return payloads


@pytest.fixture
def client(temp_db, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "auth", "none")
    monkeypatch.setattr(settings, "cron_secret", SECRET)
    return TestClient(app)


def _job(id: str, target: str = "https://github.com/acme/private-skill/tree/main/secret-plan") -> Job:
    job = Job(id=id, target=target, llm=None)
    db.insert_scan(id=job.id, target=job.target, status=job.status, created_at=job.created_at, provider=None)
    return job


def _fail_with(monkeypatch, error: Exception) -> None:
    def explode(*args, **kwargs):
        raise error

    monkeypatch.setattr(scanner, "_invoke_graph", explode)


def _succeed(monkeypatch) -> None:
    report = {"risk_assessment": {"score": 1, "severity": "LOW", "recommendation": "SAFE"}, "issues": []}
    monkeypatch.setattr(scanner, "_invoke_graph", lambda *args, **kwargs: report)


def test_alerts_carry_the_error_never_keys_users_or_targets():
    text = (
        "Fetching https://github.com/acme/private-skill/blob/main/SKILL.md for alice@example.com failed:"
        " key sk-ant-api03-abcdefghijklmnop rejected, token=sst_abc123, Authorization: Bearer eyJhbGciOi.x.y"
    )
    scrubbed = monitoring.scrub(text)
    assert "https://github.com/…" in scrubbed
    for leak in ("private-skill", "alice", "sk-ant", "sst_abc123", "eyJhbGciOi"):
        assert leak not in scrubbed
    assert monitoring.scrub("https://vercel.com") == "https://vercel.com"
    assert len(monitoring.scrub("x" * 2000)) == 500


def test_a_broken_snapshot_alerts_at_once_then_waits_out_the_cooldown(temp_db, sent, monkeypatch):
    monkeypatch.setattr(scanner, "executor_kind", lambda settings: "sandbox")

    def no_snapshot():
        raise SnapshotMissingError("No sandbox snapshot: build one with python -m app.sandbox_snapshot")

    monkeypatch.setattr(scanner, "_sandbox_executor", no_snapshot)

    anyio.run(scanner.run_job, _job("a"))

    assert db.get_scan("a")["status"] == "error"
    assert len(sent) == 1
    assert sent[0]["title"] == "Scans can't start their sandbox"
    assert "No sandbox snapshot" in sent[0]["message"]
    assert "private-skill" not in json.dumps(sent)
    # The same error again: the cooldown holds the alert back.
    anyio.run(scanner.run_job, _job("b"))
    assert len(sent) == 1
    assert monitoring.health()["sandbox_errors"] == 2


def test_a_failure_rate_alert_needs_enough_failures_and_a_high_share(temp_db, sent, monkeypatch):
    _succeed(monkeypatch)
    for index in range(4):
        anyio.run(scanner.run_job, _job(f"ok{index}"))
    _fail_with(monkeypatch, RuntimeError("clone failed"))
    for index in range(3):
        anyio.run(scanner.run_job, _job(f"bad{index}"))
    # 3 of 7 failed: under half.
    assert sent == []

    anyio.run(scanner.run_job, _job("bad3"))

    assert [payload["title"] for payload in sent] == ["Many scans are failing"]
    assert "4 of the 8 scans" in sent[0]["message"] and "clone failed" in sent[0]["message"]


def test_one_failed_scan_is_no_alert(temp_db, sent, monkeypatch):
    _fail_with(monkeypatch, RuntimeError("no such repository"))

    anyio.run(scanner.run_job, _job("a"))

    assert sent == []
    health = monitoring.health()
    assert (health["failed"], health["finished"]) == (1, 1)
    assert health["last_error"]["kind"] == "scan_failed" and health["last_error"]["scan_id"] == "a"


def test_queue_redeliveries_alert_past_a_few(temp_db, sent, monkeypatch):
    _succeed(monkeypatch)
    for index in range(3):
        _job(f"r{index}")
        db.update_scan(id=f"r{index}", status="running", finished_at=None, result=None, error=None)
        message = type("M", (), {"payload": {"scan_id": f"r{index}"}, "metadata": type("D", (), {"delivery_count": 2})()})()
        anyio.run(queue_worker.run_scan, message)

    assert [payload["title"] for payload in sent] == ["Scans are being redelivered by the queue"]
    assert monitoring.health()["redeliveries"] == 3


def test_botid_refusing_every_submission_alerts(client, sent):
    response = client.post("/internal/events", json={"kind": "bot_refused", "count": 12}, headers={"Authorization": f"Bearer {SECRET}"})

    assert response.status_code == 204
    assert [payload["title"] for payload in sent] == ["Every scan submission is being refused as a bot"]
    assert monitoring.health()["bot_refusals"] == 12


def test_refused_bots_are_no_alert_while_scans_still_start(client, sent):
    _job("a")

    client.post("/internal/events", json={"kind": "bot_refused", "count": 50}, headers={"Authorization": f"Bearer {SECRET}"})

    assert sent == []


def test_only_the_web_app_reports_events(client):
    assert client.post("/internal/events", json={"kind": "bot_refused"}).status_code == 401
    assert client.post("/internal/events", json={"kind": "scan_failed"}, headers={"Authorization": f"Bearer {SECRET}"}).status_code == 422


def test_the_overview_has_a_health_panel(client, sent, monkeypatch):
    _fail_with(monkeypatch, RuntimeError("clone failed"))
    anyio.run(scanner.run_job, _job("a"))

    health = client.get("/admin/overview").json()["health"]

    assert (health["hours"], health["failed"], health["sandbox_errors"]) == (24, 1, 0)
    assert health["last_error"]["message"] == "clone failed"
    assert health["alert_channels"] == ["webhook"]


def test_a_test_alert_reaches_the_webhook(client, sent, monkeypatch):
    assert client.post("/admin/alerts/test").json() == {"channels": ["webhook"]}
    assert sent[0]["title"] == "Test alert"

    monkeypatch.setattr(get_settings(), "alert_webhook_url", None)
    assert client.post("/admin/alerts/test").status_code == 409


def test_failures_are_logged_as_structured_lines(temp_db, capsys, monkeypatch):
    monkeypatch.setattr(get_settings(), "alert_webhook_url", None)
    _fail_with(monkeypatch, RuntimeError("clone failed"))

    anyio.run(scanner.run_job, _job("a"))

    events = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    kinds = [event["event"] for event in events]
    assert kinds == ["skillspector.scan_started", "skillspector.scan_failed"]
    assert events[1]["reason"] == "scan" and events[1]["message"] == "clone failed" and "duration_seconds" in events[1]


def test_events_are_kept_a_month(temp_db):
    db.add_monitor_event(created_at=time.time() - 31 * 86400, kind=monitoring.SCAN_FAILED)
    db.add_monitor_event(created_at=time.time(), kind=monitoring.SCAN_FAILED)

    retention.sweep_once()

    assert db.monitor_counts(since=0) == {monitoring.SCAN_FAILED: 1}


def test_the_monitoring_page_shows_each_rule_where_it_stands(client, sent, monkeypatch):
    monkeypatch.setattr(get_settings(), "smtp_host", None)
    _fail_with(monkeypatch, RuntimeError("clone failed"))
    for index in range(3):
        anyio.run(scanner.run_job, _job(f"bad{index}"))

    page = client.get("/admin/monitoring", params={"hours": 168}).json()

    assert page["health"]["hours"] == 168 and page["health"]["failed"] == 3
    rules = {rule["name"]: rule for rule in page["rules"]}
    failing = rules["failure_rate"]
    assert failing["tripped"] and failing["current"] == "3 of 3 finished scans failed in the last 30 minutes"
    assert failing["last_alert_at"] and failing["quiet_until"] > time.time()
    assert not rules["sandbox_error"]["tripped"] and rules["sandbox_error"]["last_alert_at"] is None
    # Self-hosted: no queue to redeliver, no BotID.
    assert (rules["queue_redeliveries"]["applies"], rules["bot_refusals"]["applies"]) == (False, False)
    assert rules["bot_refusals"]["current"] is None
    # The webhook by its host: its path is its secret.
    assert page["channels"] == {"webhook_host": "hooks.example.com", "emails": [], "email_ready": False}
    assert client.get("/admin/monitoring", params={"hours": 5}).status_code == 422


def test_the_events_page_lists_and_filters_what_monitoring_kept(client, sent, monkeypatch):
    _fail_with(monkeypatch, RuntimeError("clone failed"))
    for index in range(3):
        anyio.run(scanner.run_job, _job(f"bad{index}"))

    every = client.get("/admin/monitoring/events").json()
    assert every["total"] == 4
    assert every["items"][0]["kind"] == "alert_sent" and every["items"][0]["message"] == "failure_rate"

    failures = client.get("/admin/monitoring/events", params={"kind": "failures", "limit": 2}).json()
    assert failures["total"] == 3 and len(failures["items"]) == 2
    assert {item["kind"] for item in failures["items"]} == {"scan_failed"}
    assert failures["items"][0]["scan_id"] == "bad2"
