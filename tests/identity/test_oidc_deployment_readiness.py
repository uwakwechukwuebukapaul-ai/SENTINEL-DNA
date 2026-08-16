import pytest

from services.identity.oidc_config import OidcRuntimeConfiguration, OidcSecretProvider
from services.identity.oidc_diagnostics import OidcDeploymentDiagnostics, OidcDiagnosticResult
from services.identity.oidc_diagnostics_runner import OidcDeploymentDiagnosticsRunner
from services.identity.oidc_deployment_readiness import OidcDeploymentReadinessService
from services.identity.oidc_readiness import OidcDeploymentReadinessValidator


def config(**changes):
    values = dict(provider="p", issuer="https://issuer.example", authorization_endpoint="https://auth.example", token_endpoint="https://token.example", jwks_uri="https://jwks.example", client_id="client", audience="aud", redirect_uri="https://app.example/callback", client_secret_reference="SECRET", provider_tenant_claim="tid", signing_algorithms=("RS256",), external_tenant_id="ext")
    values.update(changes)
    return OidcRuntimeConfiguration(**values)


class Trust:
    def resolve(self, *_args):
        return object()


def service(configuration=None, trust=None):
    validator = OidcDeploymentReadinessValidator(OidcSecretProvider({"SECRET": "secret-value"}), trust or Trust())
    diagnostics = OidcDeploymentDiagnostics(configuration or config(), validator)
    return OidcDeploymentReadinessService(OidcDeploymentDiagnosticsRunner(diagnostics))


def safe_result(state):
    return OidcDiagnosticResult(state, state == "READY", "safe_reason", (("configuration", "PASS"),))


def test_check_delegates_to_existing_runner_and_preserves_result(monkeypatch):
    readiness = service()
    expected = safe_result("READY")
    monkeypatch.setattr(readiness._runner, "run", lambda _metadata=None: expected)
    assert readiness.check() is expected


@pytest.mark.parametrize("state", [
    "READY", "DISABLED", "CONFIGURATION_INCOMPLETE", "CONFIGURATION_INVALID",
    "TRUST_NOT_ESTABLISHED", "CRYPTOGRAPHY_UNAVAILABLE", "METADATA_UNAVAILABLE",
    "METADATA_INVALID",
])
def test_check_propagates_all_existing_states(monkeypatch, state):
    readiness = service()
    expected = safe_result(state)
    monkeypatch.setattr(readiness._runner, "run", lambda _metadata=None: expected)
    assert readiness.check().state == state


def test_passive_check_does_not_create_transport_or_use_flask_state():
    readiness = service()
    result = readiness.check()
    assert isinstance(result, OidcDiagnosticResult)
    assert not hasattr(readiness, "transport")
    assert not hasattr(readiness, "session")
    assert not hasattr(readiness, "request")


def test_configuration_is_not_overridable_by_check_call():
    readiness = service()
    with pytest.raises(TypeError):
        readiness.check(issuer="https://attacker.example")
    assert "configuration" not in OidcDeploymentReadinessService.check.__annotations__


def test_invalid_configuration_fails_closed_without_secret_exposure():
    result = service(config(jwks_uri="https://127.0.0.1/jwks")).check()
    assert result.state == "CONFIGURATION_INVALID"
    assert "secret-value" not in repr(result.as_dict())
