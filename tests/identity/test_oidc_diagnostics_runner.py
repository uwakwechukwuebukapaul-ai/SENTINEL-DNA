import pytest

from services.identity.oidc_config import OidcRuntimeConfiguration, OidcSecretProvider
from services.identity.oidc_diagnostics import OidcDeploymentDiagnostics, OidcDiagnosticResult
from services.identity.oidc_diagnostics_runner import OidcDeploymentDiagnosticsRunner
from services.identity.oidc_readiness import OidcDeploymentReadinessValidator


def config(**changes):
    values = dict(provider="p", issuer="https://issuer.example", authorization_endpoint="https://auth.example", token_endpoint="https://token.example", jwks_uri="https://jwks.example", client_id="client", audience="aud", redirect_uri="https://app.example/callback", client_secret_reference="SECRET", provider_tenant_claim="tid", signing_algorithms=("RS256",), external_tenant_id="ext")
    values.update(changes)
    return OidcRuntimeConfiguration(**values)


class Trust:
    def resolve(self, *_args):
        return object()


class Metadata:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def validate(self, _configuration):
        self.calls += 1
        return self.result


def result(state, reason="safe_reason"):
    return type("Result", (), {"valid": state == "READY", "reason": reason})()


def runner(configuration=None):
    validator = OidcDeploymentReadinessValidator(OidcSecretProvider({"SECRET": "secret-value"}), Trust())
    return OidcDeploymentDiagnostics(configuration or config(), validator)


def test_runner_delegates_passive_execution_without_network_or_state():
    diagnostics = runner()
    execution = OidcDeploymentDiagnosticsRunner(diagnostics)
    first = execution.run()
    second = execution.run()
    assert isinstance(first, OidcDiagnosticResult)
    assert first is not second
    assert first.as_dict() == second.as_dict()
    assert not hasattr(execution, "transport")


def test_runner_delegates_explicit_injected_metadata_validation(monkeypatch):
    monkeypatch.setattr("services.identity.oidc_readiness.importlib.util.find_spec", lambda _name: object())
    metadata = Metadata(result("READY", "metadata_validated"))
    output = OidcDeploymentDiagnosticsRunner(runner()).run(metadata)
    assert metadata.calls == 1
    assert output.state == "READY"


@pytest.mark.parametrize("state", [
    "CONFIGURATION_INCOMPLETE", "CONFIGURATION_INVALID", "CRYPTOGRAPHY_UNAVAILABLE",
    "METADATA_UNAVAILABLE", "METADATA_INVALID", "TRUST_NOT_ESTABLISHED",
])
def test_runner_propagates_existing_readiness_state(monkeypatch, state):
    if state == "CRYPTOGRAPHY_UNAVAILABLE":
        monkeypatch.setattr("services.identity.oidc_readiness.importlib.util.find_spec", lambda _name: None)
    elif state == "TRUST_NOT_ESTABLISHED":
        diagnostics = OidcDeploymentDiagnostics(config(), OidcDeploymentReadinessValidator(OidcSecretProvider({"SECRET": "x"}), None))
        assert OidcDeploymentDiagnosticsRunner(diagnostics).run().state == state
        return
    elif state == "CONFIGURATION_INCOMPLETE":
        diagnostics = runner(config(client_secret_reference=""))
        assert OidcDeploymentDiagnosticsRunner(diagnostics).run().state == state
        return
    elif state == "CONFIGURATION_INVALID":
        diagnostics = runner(config(jwks_uri="https://127.0.0.1/jwks"))
        assert OidcDeploymentDiagnosticsRunner(diagnostics).run().state == state
        return
    metadata = Metadata(result(state, state.lower()))
    output = OidcDeploymentDiagnosticsRunner(runner()).run(metadata)
    assert output.state == state


def test_runner_rejects_missing_diagnostics_and_does_not_accept_configuration_inputs():
    with pytest.raises(TypeError):
        OidcDeploymentDiagnosticsRunner(object())
    assert "configuration" not in OidcDeploymentDiagnosticsRunner.run.__annotations__
