"""Unit tests for the per-host HTTP budget (throttle + backoff + circuit breaker)."""

import pytest

from app.services.infrastructure.http_budget import (
    BACKOFF_CAP_SECONDS,
    CircuitOpenError,
    HttpBudget,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def make_budget(clock: FakeClock, **kwargs) -> HttpBudget:
    return HttpBudget(clock=clock.monotonic, sleep=clock.sleep, **kwargs)


class TestThrottle:
    def test_first_request_does_not_sleep(self, clock):
        budget = make_budget(clock, min_interval_by_host={"reddit.com": 2.0})
        budget.acquire("reddit.com")
        assert clock.sleeps == []

    def test_second_request_waits_min_interval(self, clock):
        budget = make_budget(clock, min_interval_by_host={"reddit.com": 2.0})
        budget.acquire("reddit.com")
        clock.now += 0.5
        budget.acquire("reddit.com")
        assert clock.sleeps == [pytest.approx(1.5)]

    def test_no_wait_after_interval_elapsed(self, clock):
        budget = make_budget(clock, min_interval_by_host={"reddit.com": 2.0})
        budget.acquire("reddit.com")
        clock.now += 3.0
        budget.acquire("reddit.com")
        assert clock.sleeps == []

    def test_hosts_are_independent(self, clock):
        budget = make_budget(clock, min_interval_by_host={"a.com": 2.0, "b.com": 2.0})
        budget.acquire("a.com")
        budget.acquire("b.com")
        assert clock.sleeps == []

    def test_unknown_host_uses_default_interval(self, clock):
        budget = make_budget(clock, default_min_interval=1.0)
        budget.acquire("x.com")
        budget.acquire("x.com")
        assert clock.sleeps == [pytest.approx(1.0)]


class TestCircuitBreaker:
    def test_opens_after_threshold_failures(self, clock):
        budget = make_budget(clock, failure_threshold=3, cooldown_seconds=600.0)
        for _ in range(3):
            budget.record_failure("reddit.com")
        assert budget.is_open("reddit.com")
        with pytest.raises(CircuitOpenError) as exc_info:
            budget.acquire("reddit.com")
        assert exc_info.value.retry_in == pytest.approx(600.0)

    def test_success_resets_failure_count(self, clock):
        budget = make_budget(clock, failure_threshold=3)
        budget.record_failure("reddit.com")
        budget.record_failure("reddit.com")
        budget.record_success("reddit.com")
        budget.record_failure("reddit.com")
        budget.record_failure("reddit.com")
        assert not budget.is_open("reddit.com")

    def test_circuit_closes_after_cooldown(self, clock):
        budget = make_budget(clock, failure_threshold=1, cooldown_seconds=600.0)
        budget.record_failure("reddit.com")
        assert budget.is_open("reddit.com")
        clock.now += 601.0
        assert not budget.is_open("reddit.com")
        budget.acquire("reddit.com")  # must not raise

    def test_failures_on_one_host_do_not_open_another(self, clock):
        budget = make_budget(clock, failure_threshold=1)
        budget.record_failure("a.com")
        assert budget.is_open("a.com")
        assert not budget.is_open("b.com")
        budget.acquire("b.com")


class TestBackoffDelay:
    def test_honors_numeric_retry_after(self, clock):
        budget = make_budget(clock)
        assert budget.backoff_delay(0, retry_after="7") == pytest.approx(7.0)

    def test_retry_after_capped(self, clock):
        budget = make_budget(clock)
        assert budget.backoff_delay(0, retry_after="9999") == pytest.approx(BACKOFF_CAP_SECONDS)

    def test_non_numeric_retry_after_falls_back_to_jitter(self, clock):
        budget = make_budget(clock)
        delay = budget.backoff_delay(1, retry_after="Wed, 21 Oct 2026 07:28:00 GMT")
        assert 1.0 <= delay <= 2.0  # attempt 1 → ceiling 2.0, full jitter from half

    def test_exponential_growth_capped(self, clock):
        budget = make_budget(clock)
        delay = budget.backoff_delay(10)
        assert delay <= BACKOFF_CAP_SECONDS
