from __future__ import annotations

from app.core.config import Settings


def test_env_local_is_read_and_overrides_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("SKILLSPECTOR_WEB_ADMIN_TOKEN=from-env\nSKILLSPECTOR_WEB_MAX_CONCURRENT_SCANS=3\n")
    (tmp_path / ".env.local").write_text("SKILLSPECTOR_WEB_ADMIN_TOKEN=from-env-local\n")

    settings = Settings()

    assert settings.admin_token == "from-env-local"
    assert settings.max_concurrent_scans == 3


def test_env_local_alone_is_enough(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.local").write_text("SKILLSPECTOR_WEB_ADMIN_TOKEN=wizard-token\n")

    assert Settings().admin_token == "wizard-token"
