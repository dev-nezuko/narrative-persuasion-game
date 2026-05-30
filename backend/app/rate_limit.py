"""In-process sliding-window limits.

Good enough for the single-process demo this backend is; a multi-worker
deployment would need a shared store such as Redis instead.
"""

import time
from collections import deque
from threading import Lock
from typing import Callable, Hashable


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float, clock: Callable[[], float] = time.monotonic):
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[Hashable, deque] = {}
        self._lock = Lock()

    def retry_after(self, key: Hashable) -> float:
        """Record a hit for key; return 0 if allowed, else seconds until a slot frees up."""
        now = self._clock()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= self.window_seconds:
                hits.popleft()
            if len(hits) >= self.limit:
                return self.window_seconds - (now - hits[0])
            hits.append(now)
            if len(self._hits) > 10_000:
                self._drop_idle(now)
            return 0.0

    def _drop_idle(self, now: float) -> None:
        idle = [k for k, h in self._hits.items() if not h or now - h[-1] >= self.window_seconds]
        for key in idle:
            del self._hits[key]

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()
