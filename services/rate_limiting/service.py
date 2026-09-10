"""Provider-neutral rate limiting over the existing SQLite/Redis backend contract."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitPolicy:
    name: str
    limit: int
    window_seconds: int
    cost_class: str = "standard"

    def __post_init__(self) -> None:
        if not self.name or self.limit < 1 or self.window_seconds < 1:
            raise ValueError("invalid_rate_limit_policy")


@dataclass(frozen=True)
class RateLimitRequest:
    tenant_id: str | None = None
    actor_id: str | None = None
    api_key_id: str | None = None
    ip_address: str | None = None
    endpoint: str = "unknown"
    operation: str = "unknown"
    cost_class: str = "standard"


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    policy_name: str
    key_hash: str
    cost_class: str


class RateLimitService:
    """Derive privacy-preserving fairness keys and delegate counting to a backend."""

    def __init__(self, backend) -> None:
        self.backend = backend

    @staticmethod
    def derive_key(request: RateLimitRequest, policy: RateLimitPolicy) -> str:
        dimensions = "|".join(
            (
                "rate-v1",
                request.tenant_id or "anonymous",
                request.actor_id or "anonymous",
                request.api_key_id or "none",
                request.ip_address or "unknown",
                request.endpoint or "unknown",
                request.operation or "unknown",
                request.cost_class or policy.cost_class,
                policy.name,
            )
        )
        return hashlib.sha256(dimensions.encode("utf-8")).hexdigest()

    def allow(self, request: RateLimitRequest, policy: RateLimitPolicy) -> RateLimitDecision:
        key = self.derive_key(request, policy)
        allowed = self.backend.allow(key, limit=policy.limit, window_seconds=policy.window_seconds)
        return RateLimitDecision(
            allowed=bool(allowed),
            policy_name=policy.name,
            key_hash=key,
            cost_class=request.cost_class or policy.cost_class,
        )


__all__ = ["RateLimitDecision", "RateLimitPolicy", "RateLimitRequest", "RateLimitService"]
