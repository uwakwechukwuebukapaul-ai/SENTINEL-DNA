"""Bounded, sanitized retry policy for scheduled operations jobs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


FAILURE_CATEGORIES = {"transient_failure", "provider_unavailable", "policy_error", "authorization_failure", "internal_failure"}


@dataclass(frozen=True)
class RetryDecision:
    retry: bool
    category: str
    retry_count: int
    next_attempt_at: str | None
    reason: str


class OperationsRetryPolicy:
    def __init__(self, max_retries: int = 3, base_delay_seconds: int = 30):
        self.max_retries = max(0, int(max_retries)); self.base_delay_seconds = max(1, int(base_delay_seconds))

    def classify(self, error: Exception) -> str:
        name = error.__class__.__name__.lower(); message = str(error).lower()
        if "provider" in message or "unavailable" in message: return "provider_unavailable"
        if "permission" in name or "authorization" in message or "credential" in message or "secret" in message: return "authorization_failure"
        if "policy" in message or "threshold" in message: return "policy_error"
        if "timeout" in message or "temporary" in message or "429" in message or "5xx" in message or "network" in message: return "transient_failure"
        if "invalid" in message or "unsafe" in message or "unsupported" in message or "malformed" in message: return "policy_error"
        return "internal_failure"

    def decide(self, *, retry_count: int, category: str, now=None) -> RetryDecision:
        category = category if category in FAILURE_CATEGORIES else "internal_failure"
        retryable = category in {"transient_failure", "provider_unavailable", "internal_failure"}
        next_count = int(retry_count) + 1
        if not retryable or next_count > self.max_retries:
            return RetryDecision(False, category, int(retry_count), None, "retry_limit_or_non_retryable_failure")
        now = now or datetime.now(timezone.utc)
        delay = self.base_delay_seconds * (2 ** max(0, int(retry_count)))
        return RetryDecision(True, category, next_count, (now + timedelta(seconds=delay)).isoformat(), "bounded_exponential_backoff")
