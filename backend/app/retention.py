from __future__ import annotations

import asyncio
import logging
import time

from app import db

logger = logging.getLogger(__name__)

_SWEEP_INTERVAL_SECONDS = 3600.0

_task: asyncio.Task | None = None


def get_retention_days() -> float | None:
    return db.get_retention_days()


def set_retention_days(value: float | None) -> None:
    db.set_retention_days(value)
    sweep_once()


def sweep_once() -> int:
    retention_days = db.get_retention_days()
    if retention_days is None:
        return 0
    cutoff = time.time() - retention_days * 86400
    deleted = db.delete_scans_older_than(cutoff)
    if deleted:
        logger.info("Retention sweep deleted %d scan(s) older than %s day(s)", deleted, retention_days)
    return deleted


async def _sweep_loop() -> None:
    while True:
        sweep_once()
        await asyncio.sleep(_SWEEP_INTERVAL_SECONDS)


def start() -> None:
    global _task
    _task = asyncio.create_task(_sweep_loop())


def stop() -> None:
    global _task
    if _task is not None:
        _task.cancel()
        _task = None
