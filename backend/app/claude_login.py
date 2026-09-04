from __future__ import annotations

import asyncio
import os
import re
import time
from dataclasses import dataclass

_START_READ_SECONDS = 15.0
_COMPLETE_TIMEOUT_SECONDS = 30.0
_STALE_PENDING_SECONDS = 300.0
_URL_RE = re.compile(r"https://\S+")


@dataclass
class PendingLogin:
    process: asyncio.subprocess.Process
    started_at: float


_pending: PendingLogin | None = None
_lock = asyncio.Lock()


async def start_claude_login() -> str:
    global _pending
    async with _lock:
        if _pending is not None:
            if time.time() - _pending.started_at < _STALE_PENDING_SECONDS:
                raise RuntimeError("A login is already in progress")
            _pending.process.kill()
            _pending = None

        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
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
