from __future__ import annotations

import logging
import threading
from collections import OrderedDict, deque

_MAX_LINES_PER_SCAN = 500
_MAX_TRACKED_SCANS = 50

_buffers: OrderedDict[str, deque[str]] = OrderedDict()
_progress: dict[str, int] = {}
_lock = threading.Lock()
_current_job = threading.local()


def _touch(job_id: str) -> None:
    """Track job_id as most-recently active; evict the oldest scan past the cap."""
    if job_id in _buffers:
        _buffers.move_to_end(job_id)
        return
    _buffers[job_id] = deque(maxlen=_MAX_LINES_PER_SCAN)
    while len(_buffers) > _MAX_TRACKED_SCANS:
        evicted, _ = _buffers.popitem(last=False)
        _progress.pop(evicted, None)


def append(job_id: str, message: str) -> None:
    with _lock:
        _touch(job_id)
        _buffers[job_id].append(message)


def increment_progress(job_id: str) -> None:
    with _lock:
        _touch(job_id)
        _progress[job_id] = _progress.get(job_id, 0) + 1


def get_progress(job_id: str) -> int:
    with _lock:
        return _progress.get(job_id, 0)


class _JobLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        job_id = getattr(_current_job, "job_id", None)
        if job_id is None:
            return
        append(job_id, self.format(record))


def init_logging() -> None:
    logger = logging.getLogger("skillspector")
    logger.setLevel(logging.INFO)
    handler = _JobLogHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(handler)


def start_capture(job_id: str) -> None:
    _current_job.job_id = job_id


def stop_capture() -> None:
    _current_job.job_id = None


def get_logs(job_id: str) -> list[str]:
    with _lock:
        buffer = _buffers.get(job_id)
        return list(buffer) if buffer is not None else []


def forget(job_id: str) -> None:
    with _lock:
        _buffers.pop(job_id, None)
        _progress.pop(job_id, None)
