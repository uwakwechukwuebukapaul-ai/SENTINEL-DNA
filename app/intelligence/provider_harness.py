"""Safe, deterministic foundation for evaluating future threat-intelligence adapters.

This module deliberately contains no vendor endpoints, SDKs, or HTTP client.  It
is test-only infrastructure: production registration remains an explicit future
deployment decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Mapping
from urllib.parse import urlparse

from services.billing.config import EnvironmentSecretProvider
from .gateway import (
    IOCType, IntelligenceObservation, LookupRequest, ProviderCapabilities,
    ProviderCapability, ProviderError, ProviderErrorCode, ProviderIdentity,
    ProviderResult, ThreatIntelligenceProvider,
)


class HarnessScenario(str, Enum):
    SUCCESS = "success"
    UNKNOWN_IOC = "unknown_ioc"
    PARTIAL_RESPONSE = "partial_response"
    TIMEOUT = "timeout"
    HTTP_ERROR = "http_error"
    MALFORMED_RESPONSE = "malformed_response"
    UNSUPPORTED_IOC = "unsupported_ioc"
    AUTH_FAILURE = "auth_failure"
    RATE_LIMIT = "rate_limit"
    PROVIDER_UNAVAILABLE = "provider_unavailable"


@dataclass(frozen=True)
class ProviderRegistration:
    """Secret-free infrastructure configuration for a future approved provider."""
    provider_id: str
    enabled: bool = False
    environment: str = "sandbox"
    base_url: str = ""
    secret_reference: str = ""
    capabilities: ProviderCapabilities = ProviderCapabilities(frozenset())
    timeout_seconds: float = 5.0
    request_limit: int = 1
    production_enabled: bool = False

    def validate(self, allowed_provider_ids: frozenset[str]) -> tuple[bool, str]:
        if not self.provider_id or self.provider_id not in allowed_provider_ids:
            return False, "provider_not_allowlisted"
        if self.environment not in {"sandbox", "production"}:
            return False, "invalid_environment"
        if self.enabled is False:
            return False, "provider_disabled"
        if self.environment == "production" and not self.production_enabled:
            return False, "production_activation_required"
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            return False, "invalid_https_endpoint"
        if not self.secret_reference:
            return False, "secret_reference_missing"
        if not 0 < self.timeout_seconds <= 30 or not 0 < self.request_limit <= 100:
            return False, "invalid_request_bounds"
        return True, "ready"


@dataclass(frozen=True)
class TransportContract:
    """Requirements a future injected production transport must meet."""
    connect_timeout_seconds: float = 3.0
    read_timeout_seconds: float = 5.0
    total_timeout_seconds: float = 10.0
    max_response_bytes: int = 1_000_000
    allow_redirects: bool = False

    def validate(self) -> bool:
        return (0 < self.connect_timeout_seconds <= self.total_timeout_seconds <= 30
                and 0 < self.read_timeout_seconds <= self.total_timeout_seconds
                and 0 < self.max_response_bytes <= 1_000_000 and not self.allow_redirects)


class DeterministicTestProvider:
    """TEST ONLY provider with zero transport and zero secret dependencies."""
    identity = ProviderIdentity("deterministic-test-only", "107.1")
    is_test_only = True

    def __init__(self, scenario: HarnessScenario = HarnessScenario.SUCCESS) -> None:
        self.scenario = scenario
        self.calls = 0

    def capabilities(self) -> frozenset[IOCType]:
        return frozenset({IOCType.IP, IOCType.DOMAIN, IOCType.HASH})

    def provider_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(self.capabilities(), frozenset({
            ProviderCapability.REPUTATION, ProviderCapability.TAGS,
            ProviderCapability.MALWARE_METADATA, ProviderCapability.ATTACK_METADATA,
        }))

    def lookup(self, request: LookupRequest) -> ProviderResult:
        self.calls += 1
        if request.ioc.type not in self.capabilities():
            return ProviderResult(self.identity, error=ProviderError(ProviderErrorCode.CONFIGURATION, "unsupported_ioc_type"))
        if self.scenario == HarnessScenario.TIMEOUT:
            raise TimeoutError("deterministic_timeout")
        if self.scenario == HarnessScenario.RATE_LIMIT:
            return ProviderResult(self.identity, error=ProviderError(ProviderErrorCode.RATE_LIMITED, "rate_limited", True))
        if self.scenario in {HarnessScenario.HTTP_ERROR, HarnessScenario.PROVIDER_UNAVAILABLE}:
            return ProviderResult(self.identity, error=ProviderError(ProviderErrorCode.UNAVAILABLE, "provider_unavailable", True))
        if self.scenario == HarnessScenario.MALFORMED_RESPONSE:
            return ProviderResult(self.identity, error=ProviderError(ProviderErrorCode.NORMALIZATION, "malformed_provider_response"))
        if self.scenario == HarnessScenario.UNKNOWN_IOC:
            return ProviderResult(self.identity, IntelligenceObservation(request.ioc, self.identity, _now(), provider_status="unknown"))
        partial = self.scenario == HarnessScenario.PARTIAL_RESPONSE
        return ProviderResult(self.identity, IntelligenceObservation(
            request.ioc, self.identity, _now(), provider_record="test-record",
            reputation="suspicious", malicious_score=0.2, suspicious_score=0.7,
            confidence=0.75, tags=("test-only",), malware_families=("test-family",),
            attack_techniques=("T1059",), provider_status="partial" if partial else "success", partial=partial,
        ))


class ProviderAdapterHarness:
    """Lifecycle gate for adapter tests; it never performs network I/O itself."""
    def __init__(self, registration: ProviderRegistration, secret_provider: EnvironmentSecretProvider,
                 allowed_provider_ids: frozenset[str], authorize: Callable[[str, str], bool]) -> None:
        self.registration, self.secret_provider = registration, secret_provider
        self.allowed_provider_ids, self.authorize = allowed_provider_ids, authorize

    def execute(self, provider: ThreatIntelligenceProvider, request: LookupRequest) -> ProviderResult:
        if getattr(provider, "is_test_only", False) and self.registration.environment == "production":
            return ProviderResult(provider.identity, error=ProviderError(ProviderErrorCode.CONFIGURATION, "test_provider_cannot_be_production_registered"))
        if not self.authorize(request.tenant_id, request.actor_id):
            raise PermissionError("actor is not authorized for threat intelligence lookup")
        valid, reason = self.registration.validate(self.allowed_provider_ids)
        if not valid:
            return ProviderResult(provider.identity, error=ProviderError(ProviderErrorCode.CONFIGURATION, reason))
        if not self.secret_provider.get(self.registration.secret_reference):
            return ProviderResult(provider.identity, error=ProviderError(ProviderErrorCode.CONFIGURATION, "secret_unavailable"))
        if request.ioc.type not in provider.capabilities():
            return ProviderResult(provider.identity, error=ProviderError(ProviderErrorCode.CONFIGURATION, "unsupported_ioc_type"))
        return provider.lookup(request)


def _now() -> datetime:
    return datetime.now(timezone.utc)
