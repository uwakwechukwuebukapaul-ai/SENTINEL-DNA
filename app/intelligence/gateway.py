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
import time


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IOCType(str, Enum):
    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    HASH = "hash"
    EMAIL = "email"
    UNKNOWN = "unknown"


class ProviderCapability(str, Enum):
    """Declarative intelligence features; these never grant tenant authority."""
    IPV4_LOOKUP = "ipv4_lookup"
    IPV6_LOOKUP = "ipv6_lookup"
    DOMAIN_LOOKUP = "domain_lookup"
    URL_LOOKUP = "url_lookup"
    MD5_LOOKUP = "md5_lookup"
    SHA1_LOOKUP = "sha1_lookup"
    SHA256_LOOKUP = "sha256_lookup"
    REPUTATION = "reputation"
    MALWARE_METADATA = "malware_metadata"
    THREAT_ACTOR_METADATA = "threat_actor_metadata"
    CAMPAIGN_METADATA = "campaign_metadata"
    ATTACK_METADATA = "attack_metadata"
    HISTORICAL_OBSERVATIONS = "historical_observations"
    TAGS = "tags"
    PASSIVE_DNS = "passive_dns"
    RELATED_INFRASTRUCTURE = "related_infrastructure"


@dataclass(frozen=True)
class ProviderCapabilities:
    """Provider-declared lookup coverage and enrichment features."""
    ioc_types: frozenset[IOCType]
    features: frozenset[ProviderCapability] = frozenset()

    def supports(self, ioc_type: IOCType) -> bool:
        return ioc_type in self.ioc_types


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


class ProviderAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class ProviderHealth:
    """Provider-neutral operational health; no vendor policy is embedded."""

    provider: str
    status: ProviderAvailability
    checked_at: datetime
    success_count: int = 0
    failure_count: int = 0
    timeout_count: int = 0
    last_error_code: str | None = None
    unavailable_reason: str | None = None
    latency_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "status": self.status.value,
            "timestamp": self.checked_at.isoformat(),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "timeout_count": self.timeout_count,
            "last_error_code": self.last_error_code,
            "unavailable_reason": self.unavailable_reason,
            "latency_ms": self.latency_ms,
        }


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
    correlation_id: str | None = None
    case_id: str | None = None

    def __post_init__(self) -> None:
        if not self.tenant_id or not self.actor_id:
            raise ValueError("tenant and actor identity are required")
        if not 0 < self.timeout_seconds <= 30:
            raise ValueError("timeout must be between 0 and 30 seconds")


class ThreatIntelligenceProvider(Protocol):
    @property
    def identity(self) -> ProviderIdentity: ...
    def capabilities(self) -> frozenset[IOCType]: ...
    def provider_capabilities(self) -> ProviderCapabilities: ...
    def lookup(self, request: LookupRequest) -> ProviderResult: ...


@dataclass(frozen=True)
class LookupAudit:
    tenant_id: str
    actor_id: str
    ioc: IOC
    contacted_providers: tuple[str, ...]
    started_at: datetime
    completed_at: datetime
    correlation_id: str | None = None


@dataclass(frozen=True)
class GatewayResult:
    observations: tuple[IntelligenceObservation, ...]
    provider_results: tuple[ProviderResult, ...]
    audit: LookupAudit
    provider_health: tuple[ProviderHealth, ...] = ()

    @property
    def successful(self) -> bool:
        return any(result.observation is not None for result in self.provider_results)


class ThreatIntelligenceGateway:
    def __init__(self, providers: Iterable[ThreatIntelligenceProvider], authorize: Callable[[str, str], bool], provider_policy: Callable[[str, str, str], bool] | None = None):
        self._providers = tuple(sorted(providers, key=lambda p: p.identity.name))
        self._authorize = authorize
        self._provider_policy = provider_policy
        self._health: dict[str, ProviderHealth] = {
            p.identity.name: ProviderHealth(p.identity.name, ProviderAvailability.UNAVAILABLE, _utc_now(), unavailable_reason="not_checked")
            for p in self._providers
        }

    def health(self) -> tuple[ProviderHealth, ...]:
        return tuple(self._health[name] for name in sorted(self._health))

    def _record_health(self, provider: ProviderIdentity, error: ProviderError | None, latency_ms: float | None = None) -> None:
        previous = self._health.get(provider.name)
        success_count = (previous.success_count if previous else 0) + (0 if error else 1)
        failure_count = (previous.failure_count if previous else 0) + (1 if error else 0)
        timeout_count = (previous.timeout_count if previous else 0) + (1 if error and error.code == ProviderErrorCode.TIMEOUT else 0)
        status = ProviderAvailability.AVAILABLE if error is None else ProviderAvailability.UNAVAILABLE
        if error is not None and previous and previous.status == ProviderAvailability.AVAILABLE:
            status = ProviderAvailability.DEGRADED
        self._health[provider.name] = ProviderHealth(provider.name, status, _utc_now(), success_count, failure_count, timeout_count, error.code.value if error else None, error.message if error else None, latency_ms)

    def lookup(self, request: LookupRequest) -> GatewayResult:
        if not self._authorize(request.tenant_id, request.actor_id):
            raise PermissionError("actor is not authorized for threat intelligence lookup")
        started = _utc_now()
        results: list[ProviderResult] = []
        for provider in self._providers:
            if request.ioc.type not in provider.capabilities():
                continue
            provider_started = time.perf_counter()
            if self._provider_policy is not None and not self._provider_policy(request.tenant_id, request.actor_id, provider.identity.name):
                results.append(ProviderResult(provider.identity, error=ProviderError(ProviderErrorCode.CONFIGURATION, "Provider is not enabled by tenant policy", False)))
                self._record_health(provider.identity, results[-1].error, (time.perf_counter() - provider_started) * 1000)
                continue
            try:
                result = provider.lookup(request)
                if result.provider != provider.identity:
                    raise ValueError("provider identity mismatch")
                results.append(result)
                self._record_health(provider.identity, result.error, (time.perf_counter() - provider_started) * 1000)
            except TimeoutError:
                results.append(ProviderResult(provider.identity, error=ProviderError(ProviderErrorCode.TIMEOUT, "provider timed out", True)))
                self._record_health(provider.identity, results[-1].error, (time.perf_counter() - provider_started) * 1000)
            except Exception as exc:  # provider isolation boundary
                results.append(ProviderResult(provider.identity, error=ProviderError(ProviderErrorCode.UNAVAILABLE, "provider failed", True)))
                self._record_health(provider.identity, results[-1].error, (time.perf_counter() - provider_started) * 1000)
        completed = _utc_now()
        return GatewayResult(
            tuple(r.observation for r in results if r.observation),
            tuple(results),
            LookupAudit(
                request.tenant_id,
                request.actor_id,
                request.ioc,
                tuple(r.provider.name for r in results),
                started,
                completed,
                request.correlation_id,
            ),
            self.health(),
        )

    def add_to_case_evidence(self, case: dict[str, Any], request: LookupRequest, context: Any | None = None) -> GatewayResult:
        from cases.evidence import add_evidence
        result = self.lookup(request)
        payload = {"ioc": asdict(request.ioc), "observations": [asdict(o) for o in result.observations], "providers": [asdict(r) for r in result.provider_results], "audit": asdict(result.audit)}
        add_evidence(case, "THREAT_INTELLIGENCE", payload)
        if context is not None:
            context.add_evidence(payload, request.tenant_id)
        return result
