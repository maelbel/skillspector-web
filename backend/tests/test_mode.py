from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import main
from app.core.config import Settings
from app.core.mode import HOSTED_NOT_IMPLEMENTED, Mode, ModeConfigError, check_mode


def test_mode_defaults_to_self_hosted(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SKILLSPECTOR_WEB_MODE", raising=False)

    assert Settings().mode is Mode.SELF_HOSTED


def test_mode_is_read_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SKILLSPECTOR_WEB_MODE", "hosted")

    assert Settings().mode is Mode.HOSTED


def test_unknown_mode_is_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SKILLSPECTOR_WEB_MODE", "cloud")

    with pytest.raises(ValidationError):
        Settings()


def test_self_hosted_always_starts():
    check_mode(Mode.SELF_HOSTED)


def test_hosted_refuses_to_start_and_names_what_is_missing():
    with pytest.raises(ModeConfigError) as excinfo:
        check_mode(Mode.HOSTED)

    message = str(excinfo.value)
    for piece, issue in HOSTED_NOT_IMPLEMENTED.items():
        assert f"{piece} ({issue})" in message
    assert "self_hosted" in message


def test_hosted_starts_once_every_piece_exists(monkeypatch):
    monkeypatch.setattr("app.core.mode.HOSTED_NOT_IMPLEMENTED", {})

    check_mode(Mode.HOSTED)


def test_health_reports_the_mode(monkeypatch):
    monkeypatch.setattr(main, "is_claude_cli_available", lambda: False)
    monkeypatch.setattr(main, "is_llm_available", lambda: (False, None))

    response = TestClient(main.app).get("/health")

    assert response.status_code == 200
    assert response.json()["mode"] == "self_hosted"
