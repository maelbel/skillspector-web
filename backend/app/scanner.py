"""In-memory job store around skillspector's compiled LangGraph pipeline.

Single-process, no persistence — fine for one homelab replica. If this ever
needs to scale past one instance, swap this module for a real queue (e.g.
Redis) rather than growing the in-memory dict.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from skillspector.graph import graph

from app.core.config import get_settings


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class Job:
    id: str
    target: str
    use_llm: bool
    status: JobStatus = JobStatus.PENDING
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


_jobs: dict[str, Job] = {}
_tasks: set[asyncio.Task] = set()
_semaphore = asyncio.Semaphore(get_settings().max_concurrent_scans)


def create_job(target: str, use_llm: bool) -> Job:
    _evict_expired()
    job = Job(id=uuid.uuid4().hex, target=target, use_llm=use_llm)
    _jobs[job.id] = job
    return job


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def schedule(job: Job) -> None:
    """Fire-and-forget the scan; keep a strong ref so the task isn't GC'd mid-flight."""
    task = asyncio.create_task(_run(job))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def _run(job: Job) -> None:
    async with _semaphore:
        job.status = JobStatus.RUNNING
        loop = asyncio.get_running_loop()
        try:
            job.result = await loop.run_in_executor(None, _invoke_graph, job.target, job.use_llm)
            job.status = JobStatus.DONE
        except Exception as exc:  # noqa: BLE001
            job.error = str(exc)
            job.status = JobStatus.ERROR
        finally:
            job.finished_at = time.time()


def _invoke_graph(target: str, use_llm: bool) -> dict[str, Any]:
    state: dict[str, Any] = {
        "input_path": target,
        "output_format": "json",
        "use_llm": use_llm,
    }
    config = {
        "run_name": "skillspector-web-scan",
        "tags": ["skillspector-web"],
        "metadata": {"input_path": target, "use_llm": use_llm},
    }
    result = graph.invoke(state, config=config)
    report_body = result.get("report_body") or "{}"
    return json.loads(report_body)


def _evict_expired() -> None:
    ttl = get_settings().job_ttl_seconds
    now = time.time()
    expired = [
        job_id
        for job_id, job in _jobs.items()
        if job.finished_at is not None and now - job.finished_at > ttl
    ]
    for job_id in expired:
        del _jobs[job_id]
