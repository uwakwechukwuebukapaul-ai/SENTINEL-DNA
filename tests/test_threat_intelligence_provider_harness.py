"""Phase 107.1 tests: all provider behavior is deterministic and offline."""
import pytest

from app.intelligence.gateway import IOC, IOCType, LookupRequest, ProviderErrorCode
from app.intelligence.provider_harness import (
    DeterministicTestProvider, HarnessScenario, ProviderAdapterHarness,
    ProviderRegistration, TransportContract,
)
from services.billing.config import EnvironmentSecretProvider
from tests.credential_helpers import random_secret


ALLOWED = frozenset({"approved-later"})


def request(kind=IOCType.DOMAIN):
    return LookupRequest("tenant-a", "actor-a", IOC("example.test", kind))


def registration(**changes):
    values = dict(provider_id="approved-later", enabled=True, environment="sandbox",
                  base_url="https://provider.invalid", secret_reference="TEST_REFERENCE")
    values.update(changes)
    return ProviderRegistration(**values)


def harness(registration_value, secrets=None, authorize=lambda *_: True):
    if secrets is None:
        secrets = {"TEST_REFERENCE": random_secret()}
    return ProviderAdapterHarness(registration_value, EnvironmentSecretProvider(secrets), ALLOWED, authorize)


def test_capabilities_are_declarative_and_test_provider_is_never_production():
    provider = DeterministicTestProvider()
    assert provider.provider_capabilities().supports(IOCType.DOMAIN)
    result = harness(registration(environment="production", production_enabled=True)).execute(provider, request())
    assert result.error.code == ProviderErrorCode.CONFIGURATION
    assert provider.calls == 0


@pytest.mark.parametrize("scenario, error, partial", [
    (HarnessScenario.SUCCESS, None, False),
    (HarnessScenario.UNKNOWN_IOC, None, False),
    (HarnessScenario.PARTIAL_RESPONSE, None, True),
    (HarnessScenario.HTTP_ERROR, ProviderErrorCode.UNAVAILABLE, False),
    (HarnessScenario.MALFORMED_RESPONSE, ProviderErrorCode.NORMALIZATION, False),
    (HarnessScenario.RATE_LIMIT, ProviderErrorCode.RATE_LIMITED, False),
    (HarnessScenario.PROVIDER_UNAVAILABLE, ProviderErrorCode.UNAVAILABLE, False),
])
def test_deterministic_provider_lifecycle_scenarios(scenario, error, partial):
    provider = DeterministicTestProvider(scenario)
    result = harness(registration()).execute(provider, request())
    assert provider.calls == 1
    assert result.error.code == error if error else result.observation is not None
    if result.observation:
        assert result.observation.partial is partial
        assert result.observation.provider.name == "deterministic-test-only"


def test_timeout_is_bounded_and_uses_gateway_error_isolation():
    provider = DeterministicTestProvider(HarnessScenario.TIMEOUT)
    with pytest.raises(TimeoutError):
        harness(registration()).execute(provider, request())
    assert provider.calls == 1


@pytest.mark.parametrize("changes, reason", [
    ({"enabled": False}, "provider_disabled"),
    ({"provider_id": "not-approved"}, "provider_not_allowlisted"),
    ({"base_url": "http://provider.invalid"}, "invalid_https_endpoint"),
    ({"base_url": ""}, "invalid_https_endpoint"),
    ({"environment": "unknown"}, "invalid_environment"),
    ({"secret_reference": ""}, "secret_reference_missing"),
    ({"timeout_seconds": 31}, "invalid_request_bounds"),
])
def test_invalid_registration_blocks_before_provider_call(changes, reason):
    provider = DeterministicTestProvider()
    result = harness(registration(**changes)).execute(provider, request())
    assert result.error.message == reason
    assert provider.calls == 0


def test_production_registration_requires_a_separate_explicit_activation_switch():
    assert registration(environment="production").validate(ALLOWED) == (False, "production_activation_required")


def test_secret_unavailable_and_unsupported_ioc_never_contact_provider_or_expose_secret():
    provider = DeterministicTestProvider()
    unavailable = harness(registration(), secrets={}).execute(provider, request())
    assert unavailable.error.message == "secret_unavailable" and provider.calls == 0
    unsupported = harness(registration()).execute(provider, request(IOCType.URL))
    assert unsupported.error.message == "unsupported_ioc_type" and provider.calls == 0
    assert "TEST_REFERENCE" not in repr(unavailable)


def test_unauthorized_actor_and_cross_tenant_are_authoritative_before_provider_call():
    provider = DeterministicTestProvider()
    with pytest.raises(PermissionError):
        harness(registration(), authorize=lambda tenant, actor: (tenant, actor) == ("tenant-a", "other")).execute(provider, request())
    assert provider.calls == 0


def test_transport_contract_requires_bounded_https_safe_defaults():
    assert TransportContract().validate()
    assert not TransportContract(allow_redirects=True).validate()
    assert not TransportContract(total_timeout_seconds=31).validate()
    assert not TransportContract(max_response_bytes=1_000_001).validate()
