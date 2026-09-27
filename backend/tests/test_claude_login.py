from __future__ import annotations

import os
import subprocess

from app import claude_login


def _fake_run(stdout: bytes, returncode: int = 0, calls: list | None = None):
    def run(args, **kwargs):
        if calls is not None:
            calls.append(kwargs)
        return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr=b"")

    return run


def test_availability_probe_strips_api_key_without_mutating_environ(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-user-key")
    monkeypatch.setattr(claude_login.shutil, "which", lambda _: "/usr/bin/claude")
    calls: list = []
    monkeypatch.setattr(claude_login.subprocess, "run", _fake_run(b'{"loggedIn": true}', calls=calls))

    assert claude_login.is_claude_cli_available() is True
    assert "ANTHROPIC_API_KEY" not in calls[0]["env"]
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-user-key"


def test_availability_probe_reports_logged_out(monkeypatch):
    monkeypatch.setattr(claude_login.shutil, "which", lambda _: "/usr/bin/claude")
    monkeypatch.setattr(claude_login.subprocess, "run", _fake_run(b'{"loggedIn": false}'))

    assert claude_login.is_claude_cli_available() is False


def test_availability_probe_without_binary(monkeypatch):
    monkeypatch.setattr(claude_login.shutil, "which", lambda _: None)

    assert claude_login.is_claude_cli_available() is False
