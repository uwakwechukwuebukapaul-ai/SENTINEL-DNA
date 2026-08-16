import pytest
from services.identity.oidc_config import OidcRuntimeConfiguration, OidcSecretProvider
from services.identity.oidc_diagnostics import OidcDeploymentDiagnostics
from services.identity.oidc_readiness import OidcDeploymentReadinessValidator

def config(**changes):
    v=dict(provider="p",issuer="https://issuer.example",authorization_endpoint="https://auth.example",token_endpoint="https://token.example",jwks_uri="https://jwks.example",client_id="client",audience="aud",redirect_uri="https://app.example/callback",client_secret_reference="SECRET",provider_tenant_claim="tid",signing_algorithms=("RS256",),external_tenant_id="ext"); v.update(changes); return OidcRuntimeConfiguration(**v)
class Trust:
    def resolve(self, *_args): return object()
class Metadata:
    def __init__(self, valid=True): self.valid, self.calls = valid, 0
    def validate(self, _configuration): self.calls += 1; return type("Result", (), {"valid":self.valid,"reason":"metadata_validated" if self.valid else "oidc_jwks_invalid"})()
def diagnostics(configuration=None, trust=None): return OidcDeploymentDiagnostics(configuration or config(), OidcDeploymentReadinessValidator(OidcSecretProvider({"SECRET":"secret-value"}), trust or Trust()))
def test_passive_is_structured_and_does_not_validate_metadata():
    result=diagnostics().passive().as_dict(); assert result["state"] in {"METADATA_UNAVAILABLE","CRYPTOGRAPHY_UNAVAILABLE"}; assert set(result)=={"state","ready","reason","checks"}
def test_explicit_validation_uses_injected_validator_only(monkeypatch):
    monkeypatch.setattr("services.identity.oidc_readiness.importlib.util.find_spec", lambda _name: object()); metadata=Metadata(); result=diagnostics().validate_metadata(metadata).as_dict(); assert metadata.calls==1; assert result["state"] in {"READY","CRYPTOGRAPHY_UNAVAILABLE"}; assert "secret-value" not in repr(result)
def test_incomplete_configuration_is_safe():
    result=OidcDeploymentDiagnostics(config(client_secret_reference=""), OidcDeploymentReadinessValidator(OidcSecretProvider({}), Trust())).passive().as_dict(); assert result["state"]=="CONFIGURATION_INCOMPLETE"; assert "SECRET" not in repr(result)
def test_no_caller_controlled_metadata_inputs_or_missing_validator():
    service=diagnostics();
    with pytest.raises(ValueError): service.validate_metadata(None)
    assert not hasattr(service, "transport")
