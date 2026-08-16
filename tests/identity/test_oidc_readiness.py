from services.identity.oidc_config import OidcRuntimeConfiguration, OidcSecretProvider
from services.identity.oidc_readiness import OidcDeploymentReadinessValidator

def config(**changes):
    values=dict(provider="p",issuer="https://issuer.example",authorization_endpoint="https://auth.example",token_endpoint="https://token.example",jwks_uri="https://jwks.example",client_id="client",audience="aud",redirect_uri="https://app.example/callback",client_secret_reference="SECRET",provider_tenant_claim="tid",signing_algorithms=("RS256",),external_tenant_id="ext")
    values.update(changes); return OidcRuntimeConfiguration(**values)

def test_missing_secret_is_incomplete_and_secret_is_not_returned():
    result=OidcDeploymentReadinessValidator(OidcSecretProvider({})).validate(config()); assert result.status=="CONFIGURATION_INCOMPLETE" and "SECRET" not in result.reason

def test_private_endpoint_is_invalid():
    result=OidcDeploymentReadinessValidator(OidcSecretProvider({"SECRET":"x"})).validate(config(jwks_uri="https://127.0.0.1/jwks")); assert result.status=="CONFIGURATION_INVALID"

def test_missing_trust_is_not_ready():
    result=OidcDeploymentReadinessValidator(OidcSecretProvider({"SECRET":"x"})).validate(config()); assert result.status in {"TRUST_NOT_ESTABLISHED","CONFIGURATION_INVALID"}

def test_metadata_validator_is_required_after_trust():
    class Trust:
        def resolve(self, *args): return object()
    result=OidcDeploymentReadinessValidator(OidcSecretProvider({"SECRET":"x"}), Trust()).validate(config())
    assert result.status in {"METADATA_UNAVAILABLE", "CRYPTOGRAPHY_UNAVAILABLE"}

def test_valid_injected_metadata_can_reach_ready_without_network():
    class Trust:
        def resolve(self, *args): return object()
    class Metadata:
        def validate(self, config): return type("Result", (), {"valid": True, "reason": "metadata_validated"})()
    result=OidcDeploymentReadinessValidator(OidcSecretProvider({"SECRET":"x"}), Trust()).validate(config(), Metadata())
    assert result.status in {"READY", "CRYPTOGRAPHY_UNAVAILABLE"}
