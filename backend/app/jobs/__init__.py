from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.core.mode import Mode
from app.jobs.base import JobRejectedError, JobRunner

__all__ = ["JobRejectedError", "JobRunner", "create_runner", "get_runner", "runner_kind"]


def runner_kind(settings: Settings) -> str:
    """SKILLSPECTOR_WEB_JOB_RUNNER when set, otherwise the mode's default."""
    if settings.job_runner:
        return settings.job_runner
    return "vercel_queues" if settings.mode is Mode.HOSTED else "in_process"


def create_runner(settings: Settings) -> JobRunner:
    if runner_kind(settings) == "vercel_queues":
        # Imported lazily so self-hosted installs never load the Queues SDK.
        from app.jobs.vercel_queues import VercelQueuesRunner

        return VercelQueuesRunner()

    from app.jobs.in_process import InProcessRunner

    return InProcessRunner()


@lru_cache
def get_runner() -> JobRunner:
    return create_runner(get_settings())
