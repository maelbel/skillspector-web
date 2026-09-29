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


def _settings(mode: Mode, database_url: str | None = None) -> Settings:
    return Settings(_env_file=None, mode=mode, database_url=database_url)


def test_self_hosted_always_starts():
    check_mode(_settings(Mode.SELF_HOSTED))


def test_hosted_refuses_to_start_and_names_what_is_missing():
    with pytest.raises(ModeConfigError) as excinfo:
        check_mode(_settings(Mode.HOSTED, "postgresql://db/skillspector"))

    message = str(excinfo.value)
    for piece, issue in HOSTED_NOT_IMPLEMENTED.items():
        assert f"{piece} ({issue})" in message
    assert "DATABASE_URL" not in message
    assert "self_hosted" in message


def test_hosted_requires_a_database_url(monkeypatch):
    monkeypatch.setattr("app.core.mode.HOSTED_NOT_IMPLEMENTED", {})

    with pytest.raises(ModeConfigError, match="SKILLSPECTOR_WEB_DATABASE_URL"):
        check_mode(_settings(Mode.HOSTED))


def test_hosted_starts_once_every_piece_exists(monkeypatch):
    monkeypatch.setattr("app.core.mode.HOSTED_NOT_IMPLEMENTED", {})

    check_mode(_settings(Mode.HOSTED, "postgresql://db/skillspector"))


def test_health_reports_the_mode(monkeypatch):
    monkeypatch.setattr(main, "is_claude_cli_available", lambda: False)
    monkeypatch.setattr(main, "is_llm_available", lambda: (False, None))

    response = TestClient(main.app).get("/health")

    assert response.status_code == 200
    assert response.json()["mode"] == "self_hosted"
