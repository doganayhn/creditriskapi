"""Concurrency-safe sliding-window limiter; intentionally process-local."""

from collections import deque
from math import ceil
from threading import Lock
from time import monotonic


class RateLimiter:
    def __init__(self, requests_per_minute, clock=monotonic):
        self.limit, self.clock = requests_per_minute, clock
        self._requests = {}
        self._lock = Lock()

    def acquire(self, api_key_id):
        with self._lock:
            now = self.clock()
            history = self._requests.setdefault(api_key_id, deque())
            while history and history[0] <= now - 60:
                history.popleft()
            if len(history) >= self.limit:
                return max(1, ceil(60 - (now - history[0])))
            history.append(now)
            return None
