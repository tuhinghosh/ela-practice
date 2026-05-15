"""Per-day AI call quota, keyed by user.

The ``DailyAICallQuota`` class is pure rate-limit logic over a
``QuotaStore`` strategy. Two stores ship:

- ``InMemoryQuotaStore`` — fast and dependency-free, kept for unit tests.
- ``SQLiteQuotaStore`` — backed by the ``ai_call_log`` table so the cap
  survives container rebuilds. Used in production via
  ``backend.app.main``.

The day boundary is UTC, aligning with OpenRouter's billing cycle. The
``learning_day_timezone`` setting governs the *streak* day boundary; the
two are intentionally decoupled so changing the family's local TZ does
not retro-actively shift past AI-call billing.
"""
from __future__ import annotations

import sqlite3
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Callable, Dict


@dataclass(frozen=True)
class QuotaCheck:
    allowed: bool
    used: int
    limit: int
    reset_at: datetime


class QuotaStore(ABC):
    """Counts AI calls per (user_id, UTC date)."""

    @abstractmethod
    def count_today(self, user_id: int, today: date) -> int: ...

    @abstractmethod
    def increment(self, user_id: int, now: datetime) -> int:
        """Record one call. Returns the post-increment count for today."""

    @abstractmethod
    def reset(self) -> None:
        """Drop all recorded calls. For test isolation."""


class InMemoryQuotaStore(QuotaStore):
    def __init__(self) -> None:
        self._counts: Dict[tuple[int, date], int] = defaultdict(int)
        self._lock = threading.Lock()

    def count_today(self, user_id: int, today: date) -> int:
        with self._lock:
            return self._counts.get((user_id, today), 0)

    def increment(self, user_id: int, now: datetime) -> int:
        today = now.astimezone(timezone.utc).date()
        with self._lock:
            self._counts[(user_id, today)] += 1
            return self._counts[(user_id, today)]

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()


class SQLiteQuotaStore(QuotaStore):
    """Counts via the ``ai_call_log`` table. Reuses an existing connection
    factory so the store does not own DB lifecycle.

    ``connection_factory`` is called once per operation and must return a
    ``sqlite3.Connection`` configured with the project's row factory.
    """

    def __init__(
        self,
        connection_factory: Callable[[], sqlite3.Connection],
    ) -> None:
        self._connect = connection_factory

    def count_today(self, user_id: int, today: date) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS n FROM ai_call_log "
                "WHERE user_id = ? AND date(called_at) = ?",
                (user_id, today.isoformat()),
            ).fetchone()
        return int(row["n"]) if row else 0

    def increment(self, user_id: int, now: datetime) -> int:
        now_utc = now.astimezone(timezone.utc)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO ai_call_log (user_id, called_at) VALUES (?, ?)",
                (user_id, now_utc.strftime("%Y-%m-%d %H:%M:%S")),
            )
            connection.commit()
            row = connection.execute(
                "SELECT COUNT(*) AS n FROM ai_call_log "
                "WHERE user_id = ? AND date(called_at) = ?",
                (user_id, now_utc.date().isoformat()),
            ).fetchone()
        return int(row["n"]) if row else 0

    def reset(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM ai_call_log")
            connection.commit()


class DailyAICallQuota:
    def __init__(
        self,
        *,
        daily_limit: int,
        store: QuotaStore | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if daily_limit < 0:
            raise ValueError("daily_limit must be >= 0.")
        self._daily_limit = daily_limit
        self._clock = clock
        self._store: QuotaStore = store if store is not None else InMemoryQuotaStore()

    @property
    def is_enabled(self) -> bool:
        return self._daily_limit > 0

    def _today(self) -> date:
        return self._clock().astimezone(timezone.utc).date()

    def _reset_at(self, today: date) -> datetime:
        return datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)

    def check(self, user_id: int) -> QuotaCheck:
        today = self._today()
        used = self._store.count_today(user_id, today)
        if not self.is_enabled:
            return QuotaCheck(allowed=True, used=used, limit=self._daily_limit, reset_at=self._reset_at(today))
        return QuotaCheck(
            allowed=used < self._daily_limit,
            used=used,
            limit=self._daily_limit,
            reset_at=self._reset_at(today),
        )

    def register(self, user_id: int) -> QuotaCheck:
        now = self._clock()
        today = now.astimezone(timezone.utc).date()
        used = self._store.increment(user_id, now)
        if not self.is_enabled:
            return QuotaCheck(allowed=True, used=used, limit=self._daily_limit, reset_at=self._reset_at(today))
        return QuotaCheck(
            allowed=used <= self._daily_limit,
            used=used,
            limit=self._daily_limit,
            reset_at=self._reset_at(today),
        )

    def reset(self) -> None:
        self._store.reset()
