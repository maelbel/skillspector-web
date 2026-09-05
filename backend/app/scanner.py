from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, model_validator
from skillspector.graph import graph

from app import db, scan_logs
from app.core.config import get_settings

TOTAL_GRAPH_STEPS = len([n for n in graph.get_graph().nodes if n not in ("__start__", "__end__")])


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


LLMProvider = Literal["anthropic", "openai", "ollama", "claude_cli"]

_NO_API_KEY_PROVIDERS = {"ollama", "claude_cli"}

_PROVIDER_ENV_VARS: dict[LLMProvider, tuple[str | None, str | None]] = {
    "anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"),
    "openai": ("OPENAI_API_KEY", "OPENAI_BASE_URL"),
    "ollama": (None, "OLLAMA_BASE_URL"),
    "claude_cli": (None, None),
}


class LLMConfig(BaseModel):
    provider: LLMProvider
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None

    @model_validator(mode="after")
    def _require_key_for_hosted_providers(self) -> LLMConfig:
        if self.provider not in _NO_API_KEY_PROVIDERS and not (self.api_key and self.api_key.strip()):
            raise ValueError(f"{self.provider} requires an api_key")
        return self


@dataclass
class Job:
    id: str
    target: str
    llm: LLMConfig | None
    status: JobStatus = JobStatus.PENDING
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


_tasks: set[asyncio.Task] = set()
_semaphore = asyncio.Semaphore(get_settings().max_concurrent_scans)
_llm_lock = asyncio.Lock()


def create_job(target: str, llm: LLMConfig | None) -> Job:
    job = Job(id=uuid.uuid4().hex, target=target, llm=llm)
    db.insert_scan(
        id=job.id,
        target=job.target,
        status=job.status,
        created_at=job.created_at,
        provider=llm.provider if llm else None,
    )
    return job


def get_job(job_id: str) -> Job | None:
    row = db.get_scan(job_id)
    if row is None:
        return None
    return Job(
        id=row["id"],
        target=row["target"],
        llm=None,
        status=JobStatus(row["status"]),
        created_at=row["created_at"],
        finished_at=row["finished_at"],
        result=json.loads(row["result"]) if row["result"] else None,
        error=row["error"],
    )


def list_jobs(limit: int, offset: int) -> tuple[list[sqlite3.Row], int]:
    return db.list_scans(limit, offset)


def schedule(job: Job) -> None:
    task = asyncio.create_task(_run(job))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def _run(job: Job) -> None:
    async with _semaphore:
        job.status = JobStatus.RUNNING
        db.update_scan(id=job.id, status=job.status, finished_at=None, result=None, error=None)
        loop = asyncio.get_running_loop()
        try:
            if job.llm is not None:
                async with _llm_lock:
                    with _llm_env(job.llm):
                        job.result = await loop.run_in_executor(None, _invoke_graph, job.id, job.target, True)
            else:
                job.result = await loop.run_in_executor(None, _invoke_graph, job.id, job.target, False)
            job.status = JobStatus.DONE
        except Exception as exc:  # noqa: BLE001
            job.error = str(exc)
            job.status = JobStatus.ERROR
        finally:
            job.finished_at = time.time()
            job.llm = None
            db.update_scan(
                id=job.id,
                status=job.status,
                finished_at=job.finished_at,
                result=job.result,
                error=job.error,
            )


@contextmanager
def _llm_env(config: LLMConfig) -> Iterator[None]:
    api_key_var, base_url_var = _PROVIDER_ENV_VARS[config.provider]
    keys = {"SKILLSPECTOR_PROVIDER", "SKILLSPECTOR_MODEL", api_key_var, base_url_var} - {None}
    previous = {key: os.environ.get(key) for key in keys}
    try:
        os.environ["SKILLSPECTOR_PROVIDER"] = config.provider
        if config.model:
            os.environ["SKILLSPECTOR_MODEL"] = config.model
        elif "SKILLSPECTOR_MODEL" in os.environ:
            del os.environ["SKILLSPECTOR_MODEL"]
        if api_key_var and config.api_key:
            os.environ[api_key_var] = config.api_key
        if base_url_var:
            if config.base_url:
                os.environ[base_url_var] = config.base_url
            elif base_url_var in os.environ:
                del os.environ[base_url_var]
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _invoke_graph(job_id: str, target: str, use_llm: bool) -> dict[str, Any]:
    scan_logs.start_capture(job_id)
    scan_logs.append(job_id, f"Starting scan of {target}")
    try:
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
        final_state: dict[str, Any] | None = None
        try:
            for mode, chunk in graph.stream(state, config=config, stream_mode=["updates", "values"]):
                if mode == "updates":
                    for node_name in chunk:
                        scan_logs.append(job_id, f"{node_name} completed")
                        scan_logs.increment_progress(job_id)
                elif mode == "values":
                    final_state = chunk
        except Exception as exc:
            scan_logs.append(job_id, f"Scan failed: {exc}")
            raise
        scan_logs.append(job_id, "Scan complete")
        report_body = (final_state or {}).get("report_body") or "{}"
        return json.loads(report_body)
    finally:
        scan_logs.stop_capture()
