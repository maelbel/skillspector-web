from __future__ import annotations

import asyncio
import functools
import os
import tempfile
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
from app.sandbox_executor import SandboxExecutor, executor_kind
from app.sandbox_runner import run_scan
from app.transitive import transitive_options

TOTAL_GRAPH_STEPS = len([n for n in graph.get_graph().nodes if n not in ("__start__", "__end__")])


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


LLMProvider = Literal["anthropic", "openai", "azure_openai", "openai_compatible", "nv_build", "ollama", "claude_cli"]

_NO_API_KEY_PROVIDERS = {"ollama", "claude_cli"}
# Providers that only work with an endpoint of the user's: an Azure resource, or any
# OpenAI-compatible API (Groq, Together, Mistral, a gateway…).
NEEDS_BASE_URL = {"azure_openai", "openai_compatible"}

# The variables skillspector reads each provider's key and endpoint from (skillspector/providers/).
_PROVIDER_ENV_VARS: dict[LLMProvider, tuple[str | None, str | None]] = {
    "anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"),
    "openai": ("OPENAI_API_KEY", "OPENAI_BASE_URL"),
    # The model is the Azure deployment's name.
    "azure_openai": ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"),
    "openai_compatible": ("SKILLSPECTOR_COMPAT_API_KEY", "SKILLSPECTOR_COMPAT_BASE_URL"),
    # build.nvidia.com; its endpoint is fixed.
    "nv_build": ("NVIDIA_INFERENCE_KEY", None),
    "ollama": (None, "OLLAMA_BASE_URL"),
    "claude_cli": (None, None),
}


class LLMConfig(BaseModel):
    provider: LLMProvider
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    # Use the Claude key saved to the user's account instead of api_key (app/claude_key.py).
    use_saved_key: bool = False

    @model_validator(mode="after")
    def _require_key_for_hosted_providers(self) -> LLMConfig:
        if self.use_saved_key:
            if self.provider != "anthropic":
                raise ValueError("a saved key is only for the anthropic provider")
            return self
        if self.provider not in _NO_API_KEY_PROVIDERS and not (self.api_key and self.api_key.strip()):
            raise ValueError(f"{self.provider} requires an api_key")
        if self.provider in NEEDS_BASE_URL and not (self.base_url and self.base_url.strip()):
            raise ValueError(f"{self.provider} requires a base_url (its endpoint)")
        return self


@dataclass
class Job:
    id: str
    target: str
    llm: LLMConfig | None
    # A baseline file's text (YAML or JSON): findings it accepts are suppressed.
    baseline: str | None = None
    # Levels of external references to follow and scan too; None follows none.
    transitive_depth: int | None = None
    status: JobStatus = JobStatus.PENDING
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


@functools.cache
def _sandbox_executor() -> SandboxExecutor:
    return SandboxExecutor(get_settings())


# skillspector reads provider credentials from os.environ, so AI scans in one process must not overlap.
_llm_lock = asyncio.Lock()


def create_job(
    target: str,
    llm: LLMConfig | None,
    *,
    owner_id: str | None = None,
    baseline: str | None = None,
    transitive_depth: int | None = None,
) -> Job:
    job = Job(id=uuid.uuid4().hex, target=target, llm=llm, baseline=baseline, transitive_depth=transitive_depth)
    db.insert_scan(
        id=job.id,
        target=job.target,
        status=job.status,
        created_at=job.created_at,
        provider=llm.provider if llm else None,
        owner_id=owner_id,
        llm_model=llm.model if llm else None,
        baseline=baseline,
        transitive_depth=transitive_depth,
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
        result=row["result"],
        error=row["error"],
    )


def list_jobs(limit: int, offset: int, *, owner_id: str | None = None) -> tuple[list[db.ScanRow], int]:
    return db.list_scans(limit, offset, owner_id=owner_id)


def delete_job(job_id: str) -> bool:
    scan_logs.forget(job_id)
    return db.delete_scan(job_id)


async def run_job(job: Job) -> None:
    """Run one scan to completion and record the outcome. Every job runner ends up here.

    Never raises for a failed scan: the error is stored on the scan instead.
    """
    # A scan can be run again (a queue redelivery after its instance died); start its log afresh.
    scan_logs.forget(job.id)
    job.status = JobStatus.RUNNING
    db.update_scan(id=job.id, status=job.status, finished_at=None, result=None, error=None)
    loop = asyncio.get_running_loop()
    try:
        if executor_kind(get_settings()) == "sandbox":
            job.result = await _sandbox_executor().run(
                job.id, job.target, llm=job.llm, baseline=job.baseline, transitive_depth=job.transitive_depth
            )
        elif job.llm is not None:
            async with _llm_lock:
                with _llm_env(job.llm):
                    job.result = await loop.run_in_executor(
                        None, _invoke_graph, job.id, job.target, True, job.baseline, job.transitive_depth
                    )
        else:
            job.result = await loop.run_in_executor(
                None, _invoke_graph, job.id, job.target, False, job.baseline, job.transitive_depth
            )
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


def _invoke_graph(
    job_id: str, target: str, use_llm: bool, baseline: str | None = None, transitive_depth: int | None = None
) -> dict[str, Any]:
    scan_logs.start_capture(job_id)
    scan_logs.append(job_id, f"Starting scan of {target}")
    settings = get_settings()
    baseline_file = None
    try:
        if baseline is not None:
            # skillspector loads baselines from a file.
            baseline_file = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)  # noqa: SIM115
            with baseline_file:
                baseline_file.write(baseline)
        config = {
            "run_name": "skillspector-web-scan",
            "tags": ["skillspector-web"],
            "metadata": {"input_path": target, "use_llm": use_llm},
        }

        def step(node_name: str) -> None:
            scan_logs.append(job_id, f"{node_name} completed")
            scan_logs.increment_progress(job_id)

        try:
            report = run_scan(
                target,
                use_llm=use_llm,
                baseline_path=baseline_file.name if baseline_file else None,
                on_step=step,
                on_log=lambda line: scan_logs.append(job_id, line),
                config=config,
                # skillspector's own deadline is per scan; a repository of several skills shares it.
                deadline_seconds=settings.max_workflow_seconds,
                transitive=transitive_options(settings, transitive_depth),
                yara_rules_dir=str(settings.yara_rules_dir) if settings.yara_rules_dir else None,
            )
        except Exception as exc:
            scan_logs.append(job_id, f"Scan failed: {exc}")
            raise
        scan_logs.append(job_id, "Scan complete")
        return report
    finally:
        scan_logs.stop_capture()
        if baseline_file is not None:
            os.unlink(baseline_file.name)
