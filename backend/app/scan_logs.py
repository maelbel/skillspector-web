from __future__ import annotations

import logging
import threading
from collections import OrderedDict, deque

_MAX_LINES_PER_SCAN = 500
_MAX_TRACKED_SCANS = 50

_buffers: OrderedDict[str, deque[str]] = OrderedDict()
_lock = threading.Lock()
_current_job = threading.local()


def append(job_id: str, message: str) -> None:
    with _lock:
        buffer = _buffers.get(job_id)
        if buffer is None:
            buffer = deque(maxlen=_MAX_LINES_PER_SCAN)
            _buffers[job_id] = buffer
            while len(_buffers) > _MAX_TRACKED_SCANS:
                _buffers.popitem(last=False)
        _buffers.move_to_end(job_id)
        buffer.append(message)


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
