"""Hosted scans: published to a Vercel Queues topic and run by the subscriber in queue_worker.py."""

from __future__ import annotations

from vercel.queue import DuplicateIdempotencyKeyError, QueueClient

from app import db
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
        # A queued message is stored for hours, so it must never carry an API key. Per-user keys,
        # fetched by the worker at run time, come with #46.
        if llm is not None:
            from app.jobs.base import JobRejectedError

            raise JobRejectedError("AI review isn't available on this server yet; run a static scan instead")

    async def submit(self, job: Job) -> None:
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
