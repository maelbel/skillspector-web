"""Hosted scans: published to a Vercel Queues topic and run by the subscriber in queue_worker.py."""

from __future__ import annotations

from vercel.queue import DuplicateIdempotencyKeyError, QueueClient

from app import claude_key, db
from app.core.config import get_settings
from app.scanner import Job, LLMConfig

SCAN_TOPIC = "scans"

# Messages outlive a crashed instance, so a stuck scan is retried; this long is plenty.
_RETENTION_SECONDS = 6 * 3600


class VercelQueuesRunner:
    def __init__(self, client: QueueClient | None = None) -> None:
        self._client = client or QueueClient()

    def on_startup(self) -> None:
        # Other instances may be mid-scan, so unlike the in-process runner nothing is failed here;
        # the worker's delivery limit handles scans whose instance died.
        return None

    def is_full(self) -> bool:
        return db.count_active_scans() >= get_settings().max_queued_scans

    def check(self, llm: LLMConfig | None) -> None:
        # Queue messages carry only the scan id, never a key: the worker gets it at run time, from
        # the user's saved key or from the one-off key held encrypted for this scan.
        if llm is not None and llm.provider != "anthropic":
            from app.jobs.base import JobRejectedError

            raise JobRejectedError("Only Claude (Anthropic) is available for AI review on this server")

    async def submit(self, job: Job) -> None:
        if job.llm is not None and not job.llm.use_saved_key and job.llm.api_key:
            claude_key.hold_for_scan(job.id, job.llm.api_key)
        # The scan id doubles as the idempotency key, so a retried request can't queue it twice.
        try:
            await self._client.send(
                SCAN_TOPIC,
                {"scan_id": job.id},
                idempotency_key=job.id,
                retention=_RETENTION_SECONDS,
            )
        except DuplicateIdempotencyKeyError:
            pass  # Already queued.
