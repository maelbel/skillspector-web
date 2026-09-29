from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app import auth, db, rate_limit
from app.auth import passwords
from app.core.config import Settings, get_settings
from app.core.mode import Mode, ModeConfigError, check_mode
from app.main import app

PASSWORD = "correct horse battery"


@pytest.fixture(autouse=True)
def _fast_hashing(monkeypatch):
    # Real-strength scrypt takes ~0.3 s a hash; these tests hash dozens of times.
    monkeypatch.setattr(passwords, "_N", 2**10)
    passwords.dummy_hash.cache_clear()
    yield
    passwords.dummy_hash.cache_clear()


@pytest.fixture
def client(temp_db, fake_runner, monkeypatch):
    monkeypatch.setattr(get_settings(), "auth", "accounts")
    monkeypatch.setattr(get_settings(), "allow_signup", None)
    monkeypatch.setattr(rate_limit, "_hits", rate_limit.OrderedDict())
    return TestClient(app)


@pytest.fixture
def open_client(temp_db, fake_runner, monkeypatch):
    monkeypatch.setattr(get_settings(), "auth", "none")
    monkeypatch.setattr(rate_limit, "_hits", rate_limit.OrderedDict())
    return TestClient(app)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _setup_admin(client) -> str:
    response = client.post("/auth/setup", json={"email": "Admin@Example.com", "password": PASSWORD})
    assert response.status_code == 200
    return response.json()["token"]


def _add_user(client, admin: str, email: str, role: str = "user") -> str:
    response = client.post("/admin/users", json={"email": email, "password": PASSWORD, "role": role}, headers=_bearer(admin))
    assert response.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200
    return login.json()["token"]


def _scan(client, token: str) -> str:
    response = client.post("/scan", json={"target": "https://github.com/acme/skill"}, headers=_bearer(token))
    assert response.status_code == 200
    return response.json()["id"]


# Without accounts


def test_without_accounts_everything_is_open(open_client):
    session = open_client.get("/auth/session").json()
    assert session == {"auth": "none", "user": None, "needs_setup": False, "signup_allowed": False}

    scan_id = open_client.post("/scan", json={"target": "https://github.com/acme/skill"}).json()["id"]
    assert open_client.get(f"/scan/{scan_id}").status_code == 200
    assert open_client.put("/settings", json={"scan_retention_days": 3}).status_code == 200


def test_without_accounts_account_routes_are_off(open_client):
    assert open_client.post("/auth/login", json={"email": "a@b.c", "password": PASSWORD}).status_code == 404
    assert open_client.post("/auth/setup", json={"email": "a@b.c", "password": PASSWORD}).status_code == 404
    assert open_client.get("/admin/users").status_code == 404


def test_no_admin_token_is_checked_any_more(open_client, monkeypatch):
    monkeypatch.setenv("SKILLSPECTOR_WEB_ADMIN_TOKEN", "left-over")

    assert open_client.put("/settings", json={"scan_retention_days": 3}).status_code == 200


# First-run setup and sign-in


def test_a_fresh_server_asks_for_its_first_admin(client):
    assert client.get("/auth/session").json() == {"auth": "accounts", "user": None, "needs_setup": True, "signup_allowed": False}

    token = _setup_admin(client)

    session = client.get("/auth/session", headers=_bearer(token)).json()
    assert session["needs_setup"] is False
    assert session["user"]["email"] == "admin@example.com"
    assert session["user"]["role"] == "admin"


def test_setup_only_works_once(client):
    _setup_admin(client)

    response = client.post("/auth/setup", json={"email": "intruder@example.com", "password": PASSWORD})

    assert response.status_code == 409
    assert db.count_users() == 1


def test_sign_in_and_out(client):
    _setup_admin(client)

    token = client.post("/auth/login", json={"email": " ADMIN@example.com ", "password": PASSWORD}).json()["token"]
    assert client.get("/scan", headers=_bearer(token)).status_code == 200

    assert client.post("/auth/logout", headers=_bearer(token)).status_code == 204
    assert client.get("/scan", headers=_bearer(token)).status_code == 401


@pytest.mark.parametrize(("email", "password"), [("admin@example.com", "wrong password"), ("nobody@example.com", PASSWORD)])
def test_wrong_credentials_get_the_same_answer(client, email, password):
    _setup_admin(client)

    response = client.post("/auth/login", json={"email": email, "password": password})

    assert response.status_code == 401
    assert response.json()["detail"] == "Wrong email or password"


def test_sign_in_attempts_are_rate_limited(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "login_rate_limit", 2)
    for _ in range(2):
        client.post("/auth/login", json={"email": "a@b.c", "password": "x" * 12})

    assert client.post("/auth/login", json={"email": "a@b.c", "password": "x" * 12}).status_code == 429


def test_weak_passwords_and_bad_emails_are_refused(client):
    assert client.post("/auth/setup", json={"email": "admin@example.com", "password": "short"}).status_code == 400
    assert client.post("/auth/setup", json={"email": "not-an-email", "password": PASSWORD}).status_code == 400
    assert db.count_users() == 0


def test_an_expired_session_is_refused(client, monkeypatch):
    token = _setup_admin(client)
    real_time = time.time
    monkeypatch.setattr(time, "time", lambda: real_time() + get_settings().session_days * 86400 + 1)

    assert client.get("/scan", headers=_bearer(token)).status_code == 401


def test_only_session_hashes_are_stored(client):
    token = _setup_admin(client)

    assert db.get_session_user(token, now=time.time()) is None  # The raw token isn't a key.
    assert auth.user_for_token(token) is not None


# Signed-in access


def test_every_scan_route_needs_a_session_with_accounts(client):
    _setup_admin(client)

    assert client.post("/scan", json={"target": "https://github.com/acme/skill"}).status_code == 401
    assert client.get("/scan").status_code == 401
    assert client.get("/scan/anything").status_code == 401
    assert client.get("/scan/anything/logs").status_code == 401
    assert client.delete("/scan/anything").status_code == 401
    assert client.put("/settings", json={"scan_retention_days": 3}).status_code == 401
    assert client.post("/admin/claude-login/start").status_code == 401


def test_users_only_see_and_delete_their_own_scans(client):
    admin = _setup_admin(client)
    alice = _add_user(client, admin, "alice@example.com")
    bob = _add_user(client, admin, "bob@example.com")
    alices_scan = _scan(client, alice)

    assert [s["id"] for s in client.get("/scan", headers=_bearer(alice)).json()["items"]] == [alices_scan]
    assert client.get("/scan", headers=_bearer(bob)).json() == {"items": [], "total": 0}
    for method, path in [("get", f"/scan/{alices_scan}"), ("get", f"/scan/{alices_scan}/logs"), ("delete", f"/scan/{alices_scan}")]:
        assert getattr(client, method)(path, headers=_bearer(bob)).status_code == 404
    assert db.get_scan(alices_scan) is not None

    assert client.delete(f"/scan/{alices_scan}", headers=_bearer(alice)).status_code == 204


def test_admins_see_every_scan_including_ones_from_before_accounts(client):
    db.insert_scan(id="legacy", target="t", status="done", created_at=1.0, provider=None)
    admin = _setup_admin(client)
    alice = _add_user(client, admin, "alice@example.com")
    alices_scan = _scan(client, alice)

    ids = {s["id"] for s in client.get("/scan", headers=_bearer(admin)).json()["items"]}
    assert ids == {"legacy", alices_scan}
    assert client.get("/scan/legacy", headers=_bearer(alice)).status_code == 404


def test_only_admins_manage_the_server(client):
    admin = _setup_admin(client)
    alice = _add_user(client, admin, "alice@example.com")

    assert client.put("/settings", json={"scan_retention_days": 3}, headers=_bearer(alice)).status_code == 403
    assert client.post("/admin/claude-login/start", headers=_bearer(alice)).status_code == 403
    assert client.get("/admin/users", headers=_bearer(alice)).status_code == 403
    assert client.post("/admin/users", json={"email": "x@y.z", "password": PASSWORD}, headers=_bearer(alice)).status_code == 403
    assert client.put("/settings", json={"scan_retention_days": 3}, headers=_bearer(admin)).status_code == 200


# Managing users


def test_admins_add_list_and_remove_users(client):
    admin = _setup_admin(client)
    alice = _add_user(client, admin, "alice@example.com")
    alice_id = client.get("/auth/session", headers=_bearer(alice)).json()["user"]["id"]

    users = client.get("/admin/users", headers=_bearer(admin)).json()
    assert [(u["email"], u["role"]) for u in users] == [("admin@example.com", "admin"), ("alice@example.com", "user")]
    assert "password_hash" not in users[0]

    assert client.delete(f"/admin/users/{alice_id}", headers=_bearer(admin)).status_code == 204
    assert client.get("/scan", headers=_bearer(alice)).status_code == 401  # Their sessions end too.


def test_duplicate_emails_are_refused(client):
    admin = _setup_admin(client)
    _add_user(client, admin, "alice@example.com")

    response = client.post("/admin/users", json={"email": "ALICE@example.com", "password": PASSWORD}, headers=_bearer(admin))

    assert response.status_code == 409


def test_admins_cannot_lock_themselves_out(client):
    admin = _setup_admin(client)
    admin_id = client.get("/auth/session", headers=_bearer(admin)).json()["user"]["id"]

    assert client.delete(f"/admin/users/{admin_id}", headers=_bearer(admin)).status_code == 409


def test_the_last_admin_cannot_be_removed(client):
    admin = _setup_admin(client)
    other_admin = _add_user(client, admin, "second@example.com", role="admin")
    first_id = client.get("/auth/session", headers=_bearer(admin)).json()["user"]["id"]
    second_id = client.get("/auth/session", headers=_bearer(other_admin)).json()["user"]["id"]

    assert client.delete(f"/admin/users/{second_id}", headers=_bearer(admin)).status_code == 204
    _add_user(client, admin, "third@example.com", role="admin")
    assert client.delete(f"/admin/users/{first_id}", headers=_bearer(admin)).status_code == 409  # Self.


# Sign-up


def test_sign_up_is_off_when_self_hosted(client):
    _setup_admin(client)

    response = client.post("/auth/signup", json={"email": "new@example.com", "password": PASSWORD})

    assert response.status_code == 403


def test_sign_up_when_allowed(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "allow_signup", True)
    _setup_admin(client)

    response = client.post("/auth/signup", json={"email": "new@example.com", "password": PASSWORD})

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "user"


# Modes


@pytest.mark.parametrize(
    ("mode", "auth_setting", "signup", "expected_auth", "expected_signup"),
    [
        (Mode.SELF_HOSTED, None, None, "none", False),
        (Mode.SELF_HOSTED, "accounts", None, "accounts", False),
        (Mode.HOSTED, None, None, "accounts", True),
        (Mode.HOSTED, None, False, "accounts", False),
    ],
)
def test_auth_follows_the_mode_unless_overridden(mode, auth_setting, signup, expected_auth, expected_signup):
    settings = Settings(_env_file=None, mode=mode, auth=auth_setting, allow_signup=signup)

    assert auth.auth_mode(settings) == expected_auth
    assert auth.signup_allowed(settings) is expected_signup


def test_hosted_mode_refuses_to_run_without_accounts():
    settings = Settings(_env_file=None, mode=Mode.HOSTED, auth="none", database_url="postgresql://db/x", sandbox_snapshot_id="s")

    with pytest.raises(ModeConfigError, match="AUTH=none"):
        check_mode(settings)


def test_passwords_hash_and_verify():
    encoded = passwords.hash_password(PASSWORD)

    assert encoded.startswith("scrypt$")
    assert PASSWORD not in encoded
    assert passwords.verify_password(PASSWORD, encoded)
    assert not passwords.verify_password("something else", encoded)
    assert not passwords.verify_password(PASSWORD, "garbage")
