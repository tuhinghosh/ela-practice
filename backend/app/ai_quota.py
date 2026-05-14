"""Per-day AI call quota, keyed by user.

State lives in-process and resets when the app restarts. That is fine for
a single-container family MVP — the quota's purpose is to cap accidental
runaway cost, not to be an audit-grade ledger. For a multi-process
deployment this would need to move to the database or a shared store.

The day boundary is UTC. A future iteration could honor the configured
``learning_day_timezone`` for symmetry with the streak logic; today UTC is
simpler and aligns with the OpenRouter billing cycle.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Callable, Dict, Optional


@dataclass(frozen=True)
class QuotaCheck:
    allowed: bool
    used: int
    limit: int
    reset_at: datetime


class DailyAICallQuota:
    def __init__(
        self,
        *,
        daily_limit: int,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if daily_limit < 0:
            raise ValueError("daily_limit must be >= 0.")
        self._daily_limit = daily_limit
        self._clock = clock
        self._counts: Dict[tuple[int, date], int] = defaultdict(int)
        self._lock = threading.Lock()

    @property
    def is_enabled(self) -> bool:
        return self._daily_limit > 0

    def _today(self) -> date:
        return self._clock().astimezone(timezone.utc).date()

    def _reset_at(self, today: date) -> datetime:
        return datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)

    def check(self, user_id: int) -> QuotaCheck:
        today = self._today()
        with self._lock:
            used = self._counts.get((user_id, today), 0)
        if not self.is_enabled:
            return QuotaCheck(allowed=True, used=used, limit=self._daily_limit, reset_at=self._reset_at(today))
        return QuotaCheck(
            allowed=used < self._daily_limit,
            used=used,
            limit=self._daily_limit,
            reset_at=self._reset_at(today),
        )

    def register(self, user_id: int) -> QuotaCheck:
        today = self._today()
        with self._lock:
            self._counts[(user_id, today)] += 1
            used = self._counts[(user_id, today)]
        if not self.is_enabled:
            return QuotaCheck(allowed=True, used=used, limit=self._daily_limit, reset_at=self._reset_at(today))
        return QuotaCheck(
            allowed=used <= self._daily_limit,
            used=used,
            limit=self._daily_limit,
            reset_at=self._reset_at(today),
        )

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()
