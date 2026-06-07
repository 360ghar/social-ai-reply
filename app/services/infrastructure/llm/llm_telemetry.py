"""LLM usage telemetry and cost estimation.

Logs per-call metrics (provider, model, latency, tokens, cost) from
Pydantic AI RunResult.usage() and provides aggregated stats.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Approximate cost per 1M tokens (input/output) as of 2026-05.
# These are rough estimates; adjust as pricing changes.
_COST_PER_1M_TOKENS: dict[str, tuple[float, float]] = {
    # (input_cost_per_1M, output_cost_per_1M)
    "gemini": (0.075, 0.30),
    "openai": (0.60, 2.40),
    "anthropic": (0.80, 4.00),
    "perplexity": (0.20, 0.80),
}


@dataclass
class LLMCallRecord:
    """Record of a single LLM call."""

    agent_name: str
    provider: str
    model: str
    latency_ms: float
    request_tokens: int = 0
    response_tokens: int = 0
    cost_usd: float = 0.0
    success: bool = True
    error: str = ""


@dataclass
class LLMTelemetry:
    """Accumulated LLM call telemetry."""

    calls: list[LLMCallRecord] = field(default_factory=list)
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    def record(self, call: LLMCallRecord) -> None:
        self.calls.append(call)
        self.total_tokens += call.request_tokens + call.response_tokens
        self.total_cost_usd += call.cost_usd

    def summary(self) -> dict:
        return {
            "total_calls": len(self.calls),
            "successful_calls": sum(1 for c in self.calls if c.success),
            "failed_calls": sum(1 for c in self.calls if not c.success),
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "by_agent": _aggregate_by(self.calls, "agent_name"),
            "by_provider": _aggregate_by(self.calls, "provider"),
        }


def _aggregate_by(calls: list[LLMCallRecord], attr: str) -> dict:
    result: dict[str, dict] = {}
    for call in calls:
        key = getattr(call, attr, "unknown")
        entry = result.setdefault(key, {"calls": 0, "tokens": 0, "cost_usd": 0.0})
        entry["calls"] += 1
        entry["tokens"] += call.request_tokens + call.response_tokens
        entry["cost_usd"] = round(entry["cost_usd"] + call.cost_usd, 6)
    return result


def estimate_cost(provider: str, request_tokens: int, response_tokens: int) -> float:
    """Estimate USD cost for a given provider and token counts."""
    rates = _COST_PER_1M_TOKENS.get(provider, (0.30, 1.20))
    input_cost = (request_tokens / 1_000_000) * rates[0]
    output_cost = (response_tokens / 1_000_000) * rates[1]
    return round(input_cost + output_cost, 8)


# Module-level singleton for aggregated stats
_telemetry = LLMTelemetry()


def record_call(call: LLMCallRecord) -> None:
    """Record a call to the global telemetry."""
    _telemetry.record(call)
    logger.info(
        "llm_call agent=%s provider=%s model=%s latency=%.0fms "
        "tokens_in=%d tokens_out=%d cost=$%.6f success=%s",
        call.agent_name,
        call.provider,
        call.model,
        call.latency_ms,
        call.request_tokens,
        call.response_tokens,
        call.cost_usd,
        call.success,
    )


def get_telemetry_summary() -> dict:
    """Return a summary dict of all recorded LLM calls."""
    return _telemetry.summary()


class CallTimer:
    """Context manager to time an LLM agent call."""

    def __init__(self, agent_name: str, provider: str, model: str) -> None:
        self.agent_name = agent_name
        self.provider = provider
        self.model = model
        self.start: float = 0.0

    def __enter__(self) -> CallTimer:
        self.start = time.monotonic()
        return self

    def __exit__(self, *exc) -> None:
        pass  # Recording is done explicitly via record()

    @property
    def elapsed_ms(self) -> float:
        return (time.monotonic() - self.start) * 1000

    def record_success(self, request_tokens: int = 0, response_tokens: int = 0) -> None:
        cost = estimate_cost(self.provider, request_tokens, response_tokens)
        record_call(LLMCallRecord(
            agent_name=self.agent_name,
            provider=self.provider,
            model=self.model,
            latency_ms=self.elapsed_ms,
            request_tokens=request_tokens,
            response_tokens=response_tokens,
            cost_usd=cost,
            success=True,
        ))

    def record_failure(self, error: str = "") -> None:
        record_call(LLMCallRecord(
            agent_name=self.agent_name,
            provider=self.provider,
            model=self.model,
            latency_ms=self.elapsed_ms,
            success=False,
            error=error[:200],
        ))
