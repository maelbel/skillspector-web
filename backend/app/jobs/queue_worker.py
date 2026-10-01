"""The Vercel Queues subscriber that runs hosted scans.

Vercel compiles this module into a queue-triggered function (see [[tool.vercel.subscribers]] in
pyproject.toml). Delivery is at least once: a message can arrive again after its scan finished, or
after the instance running it died, so the handler works from the scan's stored state.
"""

from __future__ import annotations

import time

from vercel.queue import Message, subscribe

from app.analysis_settings import apply_to_process

# The operator's skillspector settings, before skillspector reads them on import (app.scanner).
apply_to_process()

from app import claude_key, db, scan_logs, scanner, uploads
from app.jobs.vercel_queues import SCAN_TOPIC
from app.scanner import Job, JobStatus, LLMConfig

# A delivery beyond this means earlier attempts never finished, usually because the function was
# stopped mid-scan. Give up and say so rather than retry forever.
MAX_DELIVERIES = 3


@subscribe(topic=SCAN_TOPIC, retry_after=30)
async def run_scan(message: Message[dict[str, str]]) -> None:
    db.ensure_db()
    scan_logs.init_logging()

    scan = db.get_scan(message.payload["scan_id"])
    if scan is None or scan["status"] in (JobStatus.DONE, JobStatus.ERROR):
        db.delete_scan_secret(message.payload["scan_id"])
        # A deleted scan's upload is swept with retention; a finished one's is already gone.
        return  # Deleted, or already handled by an earlier delivery.

    if message.metadata.delivery_count > MAX_DELIVERIES:
        db.update_scan(
            id=scan["id"],
            status=JobStatus.ERROR,
            finished_at=time.time(),
            result=None,
            error=f"The scan didn't finish after {MAX_DELIVERIES} attempts",
        )
        db.delete_scan_secret(scan["id"])
        await uploads.delete(scan.get("upload"))
        return

    try:
        llm = _llm_for(scan)
    except _NoKeyError as exc:
        db.update_scan(id=scan["id"], status=JobStatus.ERROR, finished_at=time.time(), result=None, error=str(exc))
        await uploads.delete(scan.get("upload"))
        return
    try:
        job = Job(
            id=scan["id"],
            target=scan["target"],
            llm=llm,
            baseline=scan.get("baseline"),
            transitive_depth=scan.get("transitive_depth"),
            upload=scan.get("upload"),
        )
        # run_job deletes the upload once it's scanned.
        await scanner.run_job(job)
    finally:
        # A one-off key lives only as long as its scan.
        db.delete_scan_secret(scan["id"])


class _NoKeyError(Exception):
    pass


def _llm_for(scan: dict) -> LLMConfig | None:
    """The scan's AI settings, with its key fetched now: the one-off key held for it, else the
    owner's saved key. Keys never travel in queue messages."""
    if not scan["provider"]:
        return None
    key = claude_key.held_for_scan(scan["id"])
    if key is None and scan.get("owner_id"):
        key = claude_key.saved_key(scan["owner_id"])
    if key is None:
        raise _NoKeyError("No Claude key is available for this scan: connect one on your account page and scan again")
    return LLMConfig(provider=scan["provider"], api_key=key, model=scan.get("llm_model"))
