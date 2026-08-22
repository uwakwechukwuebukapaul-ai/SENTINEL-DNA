"""Bounded local rate-limiting seam for security-sensitive endpoints.

The current supported SQLite deployment uses one application worker. The
limiter protects authentication endpoints locally and has an explicit
replacement seam for a shared Redis/edge limiter before horizontal scaling.
"""
from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from time import monotonic


class FixedWindowRateLimiter:
    def __init__(self, *, limit: int = 10, window_seconds: int = 60, max_keys: int = 10_000):
        self.limit = max(1, int(limit))
        self.window_seconds = max(1, int(window_seconds))
        self.max_keys = max(100, int(max_keys))
        self._windows: OrderedDict[str, tuple[float, int]] = OrderedDict()
        self._lock = Lock()

    def allow(self, key: str, *, now: float | None = None) -> bool:
        current = monotonic() if now is None else float(now)
        key = str(key or "unknown")[:200]
        with self._lock:
            start, count = self._windows.get(key, (current, 0))
            if current - start >= self.window_seconds:
                start, count = current, 0
            count += 1
            self._windows[key] = (start, count)
            self._windows.move_to_end(key)
            while len(self._windows) > self.max_keys:
                self._windows.popitem(last=False)
            return count <= self.limit


__all__ = ["FixedWindowRateLimiter"]
