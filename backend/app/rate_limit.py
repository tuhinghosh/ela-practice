"""In-memory sliding-window rate limiter.

A ``SlidingWindowLimiter`` instance owns a dict mapping arbitrary keys to a
deque of failed-attempt timestamps. ``check`` prunes expired entries and
returns the current state without recording; ``register_failure`` records
one attempt; ``clear`` drops a key (called on successful authentication so
fat-fingering users are not locked out).

The store is in-process only — restarting the app resets all counters, and
the limiter is not shared across processes. Good enough for the single-
container MVP; document the constraint if/when this scales out.

Time source is injectable so tests can advance the clock without sleeping.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, Dict


@dataclass(frozen=True)
class LimitResult:
    allowed: bool
    remaining: int
    retry_after_seconds: float


class SlidingWindowLimiter:
    def __init__(
        self,
        *,
        max_attempts: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_attempts < 0:
            raise ValueError("max_attempts must be >= 0.")
        if window_seconds < 0:
            raise ValueError("window_seconds must be >= 0.")
        self._max_attempts = max_attempts
        self._window_seconds = float(window_seconds)
        self._clock = clock
        self._store: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    @property
    def is_enabled(self) -> bool:
        return self._max_attempts > 0 and self._window_seconds > 0

    def _prune(self, bucket: Deque[float], now: float) -> None:
        cutoff = now - self._window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

    def check(self, key: str) -> LimitResult:
        if not self.is_enabled:
            return LimitResult(allowed=True, remaining=self._max_attempts, retry_after_seconds=0.0)
        now = self._clock()
        with self._lock:
            bucket = self._store.get(key)
            if bucket is None:
                return LimitResult(
                    allowed=True,
                    remaining=self._max_attempts,
                    retry_after_seconds=0.0,
                )
            self._prune(bucket, now)
            if not bucket:
                self._store.pop(key, None)
                return LimitResult(
                    allowed=True,
                    remaining=self._max_attempts,
                    retry_after_seconds=0.0,
                )
            if len(bucket) >= self._max_attempts:
                retry_after = max(0.0, bucket[0] + self._window_seconds - now)
                return LimitResult(allowed=False, remaining=0, retry_after_seconds=retry_after)
            return LimitResult(
                allowed=True,
                remaining=self._max_attempts - len(bucket),
                retry_after_seconds=0.0,
            )

    def register_failure(self, key: str) -> None:
        """Record one failed attempt. Whether the *next* attempt is allowed is
        determined by ``check`` — this method never reports allow/deny so the
        endpoint logic stays simple: gate with ``check``, then respond with
        the credential error and record."""
        if not self.is_enabled:
            return
        now = self._clock()
        with self._lock:
            bucket = self._store.setdefault(key, deque())
            self._prune(bucket, now)
            bucket.append(now)

    def clear(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._store.clear()
