"""The Vercel Queues subscriber that runs hosted scans.

Vercel compiles this module into a queue-triggered function (see [[tool.vercel.subscribers]] in
pyproject.toml). Delivery is at least once: a message can arrive again after its scan finished, or
after the instance running it died, so the handler works from the scan's stored state.
"""

from __future__ import annotations

import time

from vercel.queue import Message, subscribe

from app import db, scan_logs, scanner
from app.jobs.vercel_queues import SCAN_TOPIC
from app.scanner import Job, JobStatus

# A delivery beyond this means earlier attempts never finished, usually because the function was
# stopped mid-scan. Give up and say so rather than retry forever.
MAX_DELIVERIES = 3


@subscribe(topic=SCAN_TOPIC, retry_after=30)
async def run_scan(message: Message[dict[str, str]]) -> None:
    db.ensure_db()
    scan_logs.init_logging()

    scan = db.get_scan(message.payload["scan_id"])
    if scan is None or scan["status"] in (JobStatus.DONE, JobStatus.ERROR):
        return  # Deleted, or already handled by an earlier delivery.

    if message.metadata.delivery_count > MAX_DELIVERIES:
        db.update_scan(
            id=scan["id"],
            status=JobStatus.ERROR,
            finished_at=time.time(),
            result=None,
            error=f"The scan didn't finish after {MAX_DELIVERIES} attempts",
        )
        return

    await scanner.run_job(Job(id=scan["id"], target=scan["target"], llm=None))
