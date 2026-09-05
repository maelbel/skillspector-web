from __future__ import annotations

import threading
import time
from collections import OrderedDict, deque

from fastapi import Request

_MAX_TRACKED_CLIENTS = 1000

_hits: OrderedDict[str, deque[float]] = OrderedDict()
_lock = threading.Lock()


def client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check(key: str, limit: int, window_seconds: float) -> bool:
    """Record a hit for key; return True if it's within the allowed rate."""
    now = time.monotonic()
    with _lock:
        window = _hits.get(key)
        if window is None:
            window = deque()
            _hits[key] = window
            while len(_hits) > _MAX_TRACKED_CLIENTS:
                _hits.popitem(last=False)
        else:
            _hits.move_to_end(key)

        cutoff = now - window_seconds
        while window and window[0] < cutoff:
            window.popleft()

        if len(window) >= limit:
            return False
        window.append(now)
        return True
