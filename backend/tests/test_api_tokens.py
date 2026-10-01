from __future__ import annotations

import logging
import time

import pytest
from fastapi.testclient import TestClient

from app import db
from app.auth import passwords
from app.core.config import get_settings
from app.main import app

PASSWORD = "correct horse battery"
SCAN = {"target": "https://github.com/acme/skill"}


@pytest.fixture(autouse=True)
def _fast_hashing(monkeypatch):
    monkeypatch.setattr(passwords, "_N", 2**10)
    passwords.dummy_hash.cache_clear()
    yield
    passwords.dummy_hash.cache_clear()


@pytest.fixture
def client(temp_db, fake_runner, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "auth", "accounts")
    monkeypatch.setattr(settings, "allow_signup", None)
    monkeypatch.setattr(settings, "daily_scan_quota", None)
    monkeypatch.setattr(settings, "concurrent_scan_quota", None)
    client = TestClient(app)
    client.scheduled = fake_runner.submitted
    return client


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _sessions(client) -> tuple[str, str]:
    """The admin's session and alice's."""
    admin = client.post("/auth/setup", json={"email": "admin@example.com", "password": PASSWORD}).json()["token"]
    client.post("/admin/users", json={"email": "alice@example.com", "password": PASSWORD}, headers=_bearer(admin))
    alice = client.post("/auth/login", json={"email": "alice@example.com", "password": PASSWORD}).json()["token"]
    return admin, alice


def _token(client, session: str, name: str = "CI", **options) -> dict:
    response = client.post("/account/tokens", json={"name": name, **options}, headers=_bearer(session))
    assert response.status_code == 201, response.text
    return response.json()


def _finish(scan_id: str) -> None:
    result = {"risk_assessment": {"score": 12, "severity": "LOW", "recommendation": "SAFE"}, "issues": []}
    db.update_scan(id=scan_id, status="done", finished_at=time.time(), result=result, error=None)


def test_a_script_starts_a_scan_and_reads_its_report_with_only_a_token(client):
    _, alice = _sessions(client)
    token = _token(client, alice)["token"]
    assert token.startswith("sst_")

    started = client.post("/scan", json=SCAN, headers=_bearer(token))
    assert started.status_code == 200
    scan_id = started.json()["id"]
    assert client.get(f"/scan/{scan_id}", headers=_bearer(token)).json()["status"] == "pending"
    _finish(scan_id)

    report = client.get(f"/scan/{scan_id}", headers=_bearer(token)).json()
    assert report["status"] == "done" and report["result"]["risk_assessment"]["recommendation"] == "SAFE"
    assert client.get(f"/scan/{scan_id}/export", params={"format": "sarif"}, headers=_bearer(token)).status_code == 200
    assert client.post(f"/scan/{scan_id}/rescan", headers=_bearer(token)).status_code == 200
    # As alice: her scan, in her history.
    assert db.get_scan(scan_id)["owner_id"] == client.get("/auth/session", headers=_bearer(alice)).json()["user"]["id"]
    assert [item["id"] for item in client.get("/scan", headers=_bearer(token)).json()["items"]][-1] == scan_id


@pytest.mark.parametrize("change", ["revoked", "expired", "suspended"])
def test_a_revoked_or_expired_token_gets_a_401(client, change):
    admin, alice = _sessions(client)
    created = _token(client, alice)
    assert client.get("/scan", headers=_bearer(created["token"])).status_code == 200

    if change == "revoked":
        assert client.delete(f"/account/tokens/{created['id']}", headers=_bearer(alice)).status_code == 204
    elif change == "expired":
        # Its expiry passed: the store has no setter for it, tokens are never extended.
        store = db._store_or_raise()
        if hasattr(store, "_conn"):
            store._conn.execute("UPDATE api_tokens SET expires_at = ? WHERE id = ?", (time.time() - 1, created["id"]))
            store._conn.commit()
        else:
            store._execute("UPDATE api_tokens SET expires_at = %s WHERE id = %s", (time.time() - 1, created["id"]))
    else:
        alice_id = client.get("/auth/session", headers=_bearer(alice)).json()["user"]["id"]
        client.patch(f"/admin/users/{alice_id}", json={"status": "suspended"}, headers=_bearer(admin))

    refused = client.get("/scan", headers=_bearer(created["token"]))
    assert refused.status_code == 401
    assert refused.json()["detail"] == "This API token is invalid, expired or revoked"
    assert client.post("/scan", json=SCAN, headers=_bearer(created["token"])).status_code == 401


def test_an_unknown_token_gets_a_401(client):
    _sessions(client)

    assert client.get("/scan", headers=_bearer("sst_not-a-token")).status_code == 401


def test_a_token_is_shown_once_and_never_again(client, caplog):
    admin, alice = _sessions(client)
    caplog.set_level(logging.DEBUG)
    created = _token(client, alice)
    token = created["token"]
    client.post("/scan", json=SCAN, headers=_bearer(token))

    alice_id = client.get("/auth/session", headers=_bearer(alice)).json()["user"]["id"]
    responses = [
        client.get("/account/tokens", headers=_bearer(alice)),
        client.get(f"/admin/users/{alice_id}/tokens", headers=_bearer(admin)),
        client.get(f"/admin/users/{alice_id}", headers=_bearer(admin)),
        client.get("/scan", headers=_bearer(token)),
    ]
    assert all(response.status_code == 200 for response in responses)
    assert not any(token in response.text for response in responses)
    (listed,) = responses[0].json()
    assert listed["prefix"] == token[:10] and listed["name"] == "CI" and listed["scopes"] == ["scan"]
    assert "token" not in listed
    # Not in the database either: only its hash.
    store = db._store_or_raise()
    if hasattr(store, "_conn"):
        dump = "\n".join(store._conn.iterdump())
        assert token not in dump
    assert not any(token in record.getMessage() for record in caplog.records)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/account/tokens"),
        ("post", "/account/tokens"),
        ("get", "/account/usage"),
        ("get", "/admin/users"),
        ("put", "/settings"),
    ],
)
def test_a_token_only_starts_and_reads_scans(client, method, path):
    admin, _ = _sessions(client)
    # Even an admin's token.
    token = _token(client, admin)["token"]

    response = getattr(client, method)(path, headers=_bearer(token), **({"json": {"name": "x"}} if method in ("post", "put") else {}))

    assert response.status_code == 403
    assert "only start and read scans" in response.json()["detail"]


def test_a_token_cant_delete_or_share_a_scan(client):
    _, alice = _sessions(client)
    token = _token(client, alice)["token"]
    scan_id = client.post("/scan", json=SCAN, headers=_bearer(token)).json()["id"]
    _finish(scan_id)

    assert client.delete(f"/scan/{scan_id}", headers=_bearer(token)).status_code == 403
    assert client.post(f"/scan/{scan_id}/share", headers=_bearer(token)).status_code == 403
    assert db.get_scan(scan_id) is not None


def test_a_token_counts_towards_its_owners_quota(client):
    admin, alice = _sessions(client)
    client.put("/settings", json={"daily_scan_quota": 2, "concurrent_scan_quota": None}, headers=_bearer(admin))
    token = _token(client, alice)["token"]

    assert client.post("/scan", json=SCAN, headers=_bearer(alice)).status_code == 200
    assert client.post("/scan", json=SCAN, headers=_bearer(token)).status_code == 200
    assert client.post("/scan", json=SCAN, headers=_bearer(token)).status_code == 429


def test_creating_using_and_revoking_are_in_the_activity_log(client):
    _, alice = _sessions(client)
    created = _token(client, alice, name="Nightly CI")
    for _ in range(3):
        client.get("/scan", headers=_bearer(created["token"]))
    client.delete(f"/account/tokens/{created['id']}", headers=_bearer(alice))

    entries, _ = db.list_audit(20, 0)
    tokens = [(entry["action"], entry["actor_email"], entry["detail"]) for entry in entries if entry["action"].startswith("token.")]
    # Used three times, logged once: its first use that day.
    assert tokens == [
        ("token.revoked", "alice@example.com", "Nightly CI"),
        ("token.used", "alice@example.com", "Nightly CI"),
        ("token.created", "alice@example.com", "Nightly CI"),
    ]


def test_an_admin_sees_and_revokes_any_users_tokens(client):
    admin, alice = _sessions(client)
    created = _token(client, alice)
    alice_id = client.get("/auth/session", headers=_bearer(alice)).json()["user"]["id"]

    assert [token["id"] for token in client.get(f"/admin/users/{alice_id}/tokens", headers=_bearer(admin)).json()] == [created["id"]]
    assert client.get(f"/admin/users/{alice_id}/tokens", headers=_bearer(alice)).status_code == 403
    assert client.delete(f"/admin/users/{alice_id}/tokens/{created['id']}", headers=_bearer(admin)).status_code == 204

    assert client.get("/scan", headers=_bearer(created["token"])).status_code == 401
    (revoked,) = [entry for entry in db.list_audit(20, 0)[0] if entry["action"] == "token.revoked"]
    assert (revoked["actor_email"], revoked["target_email"]) == ("admin@example.com", "alice@example.com")


def test_a_user_cant_revoke_someone_elses_token(client):
    admin, alice = _sessions(client)
    admins = _token(client, admin)

    assert client.delete(f"/account/tokens/{admins['id']}", headers=_bearer(alice)).status_code == 404
    assert client.get("/scan", headers=_bearer(admins["token"])).status_code == 200


@pytest.mark.parametrize(
    ("body", "message"),
    [({"name": "  "}, "Give the token a name"), ({"name": "x" * 81}, "at most 80 characters")],
)
def test_a_token_needs_a_name(client, body, message):
    _, alice = _sessions(client)

    response = client.post("/account/tokens", json=body, headers=_bearer(alice))

    assert response.status_code == 400
    assert message in response.json()["detail"]


def test_a_token_expires_when_asked_or_never(client):
    _, alice = _sessions(client)

    assert _token(client, alice, expires_in_days=30)["expires_at"] == pytest.approx(time.time() + 30 * 86400, abs=60)
    assert _token(client, alice, name="forever", expires_in_days=None)["expires_at"] is None
