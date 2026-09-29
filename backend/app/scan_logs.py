"""Live log lines and step progress for running scans.

Two stores, picked from SKILLSPECTOR_WEB_LOG_STORE (or the mode): `memory` (self-hosted default,
lost on restart) and `database` (hosted default: the scan database, so whichever instance serves
the result page sees what the instance running the scan wrote).
"""

from __future__ import annotations

import logging
import threading
from collections import OrderedDict, deque
from contextvars import ContextVar
from typing import Literal, Protocol

from app import db
from app.core.config import Settings, get_settings
from app.core.mode import Mode

_MAX_LINES_PER_SCAN = 500
_MAX_TRACKED_SCANS = 50

# A ContextVar rather than threading.local: LangGraph runs parallel nodes (the analyzers fanned
# out from build_context) on worker threads, and copies the caller's context into them.
_current_job: ContextVar[str | None] = ContextVar("scan_logs_current_job", default=None)

LogStoreKind = Literal["memory", "database"]


class LogStore(Protocol):
    def append(self, job_id: str, message: str) -> None: ...

    def increment_progress(self, job_id: str) -> None: ...

    def get_progress(self, job_id: str) -> int: ...

    def get_logs(self, job_id: str) -> list[str]: ...

    def forget(self, job_id: str) -> None: ...


class MemoryLogStore:
    """The last 500 lines of the 50 most recently active scans, in this process."""

    def __init__(self) -> None:
        self._buffers: OrderedDict[str, deque[str]] = OrderedDict()
        self._progress: dict[str, int] = {}
        self._lock = threading.Lock()

    def _touch(self, job_id: str) -> None:
        """Track job_id as most-recently active; evict the oldest scan past the cap."""
        if job_id in self._buffers:
            self._buffers.move_to_end(job_id)
            return
        self._buffers[job_id] = deque(maxlen=_MAX_LINES_PER_SCAN)
        while len(self._buffers) > _MAX_TRACKED_SCANS:
            evicted, _ = self._buffers.popitem(last=False)
            self._progress.pop(evicted, None)

    def append(self, job_id: str, message: str) -> None:
        with self._lock:
            self._touch(job_id)
            self._buffers[job_id].append(message)

    def increment_progress(self, job_id: str) -> None:
        with self._lock:
            self._touch(job_id)
            self._progress[job_id] = self._progress.get(job_id, 0) + 1

    def get_progress(self, job_id: str) -> int:
        with self._lock:
            return self._progress.get(job_id, 0)

    def get_logs(self, job_id: str) -> list[str]:
        with self._lock:
            buffer = self._buffers.get(job_id)
            return list(buffer) if buffer is not None else []

    def forget(self, job_id: str) -> None:
        with self._lock:
            self._buffers.pop(job_id, None)
            self._progress.pop(job_id, None)


class DatabaseLogStore:
    """Log lines and step counts stored alongside the scan, capped at 500 lines per scan.

    Lines go away with their scan: deleting it or the retention sweep removes them too.
    """

    def append(self, job_id: str, message: str) -> None:
        db.append_log_line(job_id, message, keep=_MAX_LINES_PER_SCAN)

    def increment_progress(self, job_id: str) -> None:
        db.increment_progress(job_id)

    def get_progress(self, job_id: str) -> int:
        return db.get_progress(job_id)

    def get_logs(self, job_id: str) -> list[str]:
        return db.get_log_lines(job_id)

    def forget(self, job_id: str) -> None:
        db.clear_logs(job_id)


def log_store_kind(settings: Settings) -> LogStoreKind:
    """SKILLSPECTOR_WEB_LOG_STORE when set, otherwise the mode's default."""
    if settings.log_store:
        return settings.log_store
    return "database" if settings.mode is Mode.HOSTED else "memory"


def create_log_store(settings: Settings) -> LogStore:
    return DatabaseLogStore() if log_store_kind(settings) == "database" else MemoryLogStore()


_store: LogStore | None = None
_store_lock = threading.Lock()


def _get_store() -> LogStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = create_log_store(get_settings())
    return _store


def append(job_id: str, message: str) -> None:
    _get_store().append(job_id, message)


def increment_progress(job_id: str) -> None:
    _get_store().increment_progress(job_id)


def get_progress(job_id: str) -> int:
    return _get_store().get_progress(job_id)


def get_logs(job_id: str) -> list[str]:
    return _get_store().get_logs(job_id)


def forget(job_id: str) -> None:
    """Drop a scan's lines and progress: when it's deleted, or before it's run again."""
    _get_store().forget(job_id)


class _JobLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        job_id = _current_job.get()
        if job_id is None:
            return
        try:
            append(job_id, self.format(record))
        except Exception:  # noqa: BLE001
            # A log line that can't be stored must never fail the scan that produced it.
            self.handleError(record)


def init_logging() -> None:
    """Attach the capture handler to skillspector's logger. Safe to call more than once."""
    logger = logging.getLogger("skillspector")
    logger.setLevel(logging.INFO)
    if any(isinstance(existing, _JobLogHandler) for existing in logger.handlers):
        return
    handler = _JobLogHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(handler)


def start_capture(job_id: str) -> None:
    _current_job.set(job_id)


def stop_capture() -> None:
    _current_job.set(None)
