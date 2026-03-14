import random
import time
from dataclasses import dataclass, field
from datetime import date
from threading import Lock


@dataclass
class AccountRateLimiter:
    requests_per_minute: int
    daily_cap: int
    _lock: Lock = field(default_factory=Lock)
    _tokens: float = 0.0
    _last_refill: float = field(default_factory=time.monotonic)
    _day_marker: date = field(default_factory=date.today)
    _day_count: int = 0

    def __post_init__(self) -> None:
        self._tokens = float(self.requests_per_minute)

    def wait_for_slot(self) -> None:
        while True:
            if self.try_acquire():
                # Small randomized delay helps reduce burst signatures.
                time.sleep(random.uniform(0.35, 1.25))
                return
            time.sleep(1.0)

    def try_acquire(self) -> bool:
        with self._lock:
            self._reset_day_if_needed()
            if self._day_count >= self.daily_cap:
                return False
            self._refill_tokens()
            if self._tokens < 1.0:
                return False
            self._tokens -= 1.0
            self._day_count += 1
            return True

    def _refill_tokens(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        per_second = self.requests_per_minute / 60.0
        self._tokens = min(float(self.requests_per_minute), self._tokens + elapsed * per_second)
        self._last_refill = now

    def _reset_day_if_needed(self) -> None:
        today = date.today()
        if today != self._day_marker:
            self._day_marker = today
            self._day_count = 0
