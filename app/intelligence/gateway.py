"""Provider-neutral threat intelligence gateway.

Providers return observations; the gateway never turns an observation into a
case verdict.  The module is deliberately transport agnostic so tests and
future adapters can enforce their own bounded HTTP client policy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Iterable, Mapping, Protocol


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IOCType(str, Enum):
    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    HASH = "hash"
    EMAIL = "email"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class IOC:
    value: str
    type: IOCType

    def __post_init__(self) -> None:
        value = self.value.strip().lower()
        if not value or len(value) > 2048:
            raise ValueError("IOC value must be non-empty and bounded")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True)
class ProviderIdentity:
    name: str
    version: str | None = None


class ProviderErrorCode(str, Enum):
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    NORMALIZATION = "normalization_error"
    CONFIGURATION = "configuration_error"


@dataclass(frozen=True)
class ProviderError:
    code: ProviderErrorCode
    message: str
    retryable: bool = False


@dataclass(frozen=True)
class IntelligenceObservation:
    ioc: IOC
    provider: ProviderIdentity
    retrieved_at: datetime
    provider_record: str | None = None
    reputation: str | None = None
    malicious_score: float | None = None
    suspicious_score: float | None = None
    confidence: float | None = None
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    observation_count: int | None = None
    tags: tuple[str, ...] = ()
    malware_families: tuple[str, ...] = ()
    threat_actors: tuple[str, ...] = ()
    campaigns: tuple[str, ...] = ()
    related_infrastructure: tuple[str, ...] = ()
    attack_techniques: tuple[str, ...] = ()
    source_timestamp: datetime | None = None
    expires_at: datetime | None = None
    provider_status: str = "success"
    provider_error: ProviderError | None = None
    partial: bool = False

    @property
    def stale(self) -> bool:
        return self.expires_at is not None and _utc_now() >= self.expires_at


@dataclass(frozen=True)
class ProviderResult:
    provider: ProviderIdentity
    observation: IntelligenceObservation | None = None
    error: ProviderError | None = None


@dataclass(frozen=True)
class LookupRequest:
    tenant_id: str
    actor_id: str
    ioc: IOC
    timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        if not self.tenant_id or not self.actor_id:
            raise ValueError("tenant and actor identity are required")
        if not 0 < self.timeout_seconds <= 30:
            raise ValueError("timeout must be between 0 and 30 seconds")


class ThreatIntelligenceProvider(Protocol):
    @property
    def identity(self) -> ProviderIdentity: ...
    def capabilities(self) -> frozenset[IOCType]: ...
    def lookup(self, request: LookupRequest) -> ProviderResult: ...


@dataclass(frozen=True)
class LookupAudit:
    tenant_id: str
    actor_id: str
    ioc: IOC
    contacted_providers: tuple[str, ...]
    started_at: datetime
    completed_at: datetime


@dataclass(frozen=True)
class GatewayResult:
    observations: tuple[IntelligenceObservation, ...]
    provider_results: tuple[ProviderResult, ...]
    audit: LookupAudit

    @property
    def successful(self) -> bool:
        return any(result.observation is not None for result in self.provider_results)


class ThreatIntelligenceGateway:
    def __init__(self, providers: Iterable[ThreatIntelligenceProvider], authorize: Callable[[str, str], bool]):
        self._providers = tuple(sorted(providers, key=lambda p: p.identity.name))
        self._authorize = authorize

    def lookup(self, request: LookupRequest) -> GatewayResult:
        if not self._authorize(request.tenant_id, request.actor_id):
            raise PermissionError("actor is not authorized for threat intelligence lookup")
        started = _utc_now()
        results: list[ProviderResult] = []
        for provider in self._providers:
            if request.ioc.type not in provider.capabilities():
                continue
            try:
                result = provider.lookup(request)
                if result.provider != provider.identity:
                    raise ValueError("provider identity mismatch")
                results.append(result)
            except TimeoutError:
                results.append(ProviderResult(provider.identity, error=ProviderError(ProviderErrorCode.TIMEOUT, "provider timed out", True)))
            except Exception as exc:  # provider isolation boundary
                results.append(ProviderResult(provider.identity, error=ProviderError(ProviderErrorCode.UNAVAILABLE, str(exc)[:200], True)))
        completed = _utc_now()
        return GatewayResult(tuple(r.observation for r in results if r.observation), tuple(results), LookupAudit(request.tenant_id, request.actor_id, request.ioc, tuple(r.provider.name for r in results), started, completed))

    def add_to_case_evidence(self, case: dict[str, Any], request: LookupRequest, context: Any | None = None) -> GatewayResult:
        from cases.evidence import add_evidence
        result = self.lookup(request)
        payload = {"ioc": asdict(request.ioc), "observations": [asdict(o) for o in result.observations], "providers": [asdict(r) for r in result.provider_results], "audit": asdict(result.audit)}
        add_evidence(case, "THREAT_INTELLIGENCE", payload)
        if context is not None:
            context.add_evidence(payload, request.tenant_id)
        return result
