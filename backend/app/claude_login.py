from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass

_START_READ_SECONDS = 15.0
_COMPLETE_TIMEOUT_SECONDS = 30.0
_STALE_PENDING_SECONDS = 300.0
_URL_RE = re.compile(r"https://\S+")
_AUTH_STATUS_TIMEOUT_SECONDS = 15.0


@dataclass
class PendingLogin:
    process: asyncio.subprocess.Process
    started_at: float


_pending: PendingLogin | None = None
_lock = asyncio.Lock()


def _env_without_api_key() -> dict[str, str]:
    # main.py sets a placeholder ANTHROPIC_API_KEY, and scans may set a user's real one; either
    # would make the CLI report API-key auth instead of its own login.
    return {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}


def is_claude_cli_available() -> bool:
    """Whether the server's `claude` CLI is logged in, without touching os.environ."""
    binary = shutil.which("claude")
    if binary is None:
        return False
    try:
        result = subprocess.run(
            [binary, "auth", "status"],
            capture_output=True,
            check=False,
            env=_env_without_api_key(),
            timeout=_AUTH_STATUS_TIMEOUT_SECONDS,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    out = result.stdout.decode(errors="replace").strip()
    try:
        logged_in = bool(json.loads(out).get("loggedIn"))
    except (json.JSONDecodeError, AttributeError):
        logged_in = result.returncode == 0 and "not logged in" not in out.lower()
    return result.returncode == 0 and logged_in


async def start_claude_login() -> str:
    global _pending
    async with _lock:
        if _pending is not None:
            if time.time() - _pending.started_at < _STALE_PENDING_SECONDS:
                raise RuntimeError("A login is already in progress")
            _pending.process.kill()
            _pending = None

        env = _env_without_api_key()
        process = await asyncio.create_subprocess_exec(
            "claude",
            "auth",
            "login",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )

        buffer = b""
        deadline = time.monotonic() + _START_READ_SECONDS
        while time.monotonic() < deadline:
            try:
                chunk = await asyncio.wait_for(process.stdout.read(256), timeout=1)
            except TimeoutError:
                continue
            if not chunk:
                break
            buffer += chunk
            if b"Paste code here" in buffer:
                break

        match = _URL_RE.search(buffer.decode(errors="replace"))
        if not match:
            process.kill()
            raise RuntimeError("Could not find a login URL in the CLI's output")

        _pending = PendingLogin(process=process, started_at=time.time())
        return match.group(0)


async def complete_claude_login(code: str) -> tuple[bool, str]:
    global _pending
    async with _lock:
        if _pending is None:
            raise RuntimeError("No login is in progress")
        process = _pending.process
        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(input=(code.strip() + "\n").encode()),
                timeout=_COMPLETE_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            process.kill()
            _pending = None
            raise RuntimeError("Login did not complete in time") from None

        success = process.returncode == 0
        _pending = None
        return success, stdout.decode(errors="replace")


def kill_pending() -> None:
    global _pending
    if _pending is not None:
        _pending.process.kill()
        _pending = None
