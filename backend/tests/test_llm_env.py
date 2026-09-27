from __future__ import annotations

import os

import pytest

from app.scanner import LLMConfig, _llm_env


@pytest.fixture(autouse=True)
def baseline_env(monkeypatch):
    monkeypatch.setenv("SKILLSPECTOR_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-placeholder")
    monkeypatch.setenv("SKILLSPECTOR_MODEL", "server-default-model")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://server-default.example")


def test_sets_the_scan_provider_key_model_and_base_url():
    config = LLMConfig(provider="openai", api_key="sk-user", base_url="https://user.example", model="gpt-x")

    with _llm_env(config):
        assert os.environ["SKILLSPECTOR_PROVIDER"] == "openai"
        assert os.environ["OPENAI_API_KEY"] == "sk-user"
        assert os.environ["OPENAI_BASE_URL"] == "https://user.example"
        assert os.environ["SKILLSPECTOR_MODEL"] == "gpt-x"


def test_clears_server_defaults_the_scan_did_not_set():
    with _llm_env(LLMConfig(provider="openai", api_key="sk-user")):
        assert "SKILLSPECTOR_MODEL" not in os.environ
        assert "OPENAI_BASE_URL" not in os.environ


def test_restores_the_previous_environment_even_on_error():
    with pytest.raises(RuntimeError), _llm_env(LLMConfig(provider="openai", api_key="sk-user", model="gpt-x")):
        raise RuntimeError("scan failed")

    assert os.environ["SKILLSPECTOR_PROVIDER"] == "anthropic"
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-placeholder"
    assert os.environ["SKILLSPECTOR_MODEL"] == "server-default-model"
    assert os.environ["OPENAI_BASE_URL"] == "https://server-default.example"
    assert "OPENAI_API_KEY" not in os.environ


def test_claude_cli_leaves_api_keys_alone():
    with _llm_env(LLMConfig(provider="claude_cli")):
        assert os.environ["SKILLSPECTOR_PROVIDER"] == "claude_cli"
        assert os.environ["ANTHROPIC_API_KEY"] == "sk-placeholder"
