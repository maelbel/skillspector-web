from __future__ import annotations

import asyncio
import time

from app import db, scanner, uploads
from app.core.config import get_settings
from app.scanner import Job, LLMConfig


class InProcessRunner:
    """Scans run as asyncio tasks in this process: the self-hosted default."""

    def __init__(self) -> None:
        self._tasks: set[asyncio.Task] = set()
        self._semaphore = asyncio.Semaphore(get_settings().max_concurrent_scans)

    def on_startup(self) -> None:
        # Jobs run in this process, so anything still pending/running from a previous one is dead.
        db.fail_unfinished_scans(error="Interrupted: the API restarted before this scan finished", finished_at=time.time())
        # So no upload is waiting for a scan any more.
        uploads.clear_local()

    def is_full(self) -> bool:
        return len(self._tasks) >= get_settings().max_queued_scans

    def check(self, llm: LLMConfig | None) -> None:
        return None

    async def submit(self, job: Job) -> None:
        task = asyncio.create_task(self._run(job))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run(self, job: Job) -> None:
        async with self._semaphore:
            await scanner.run_job(job)
