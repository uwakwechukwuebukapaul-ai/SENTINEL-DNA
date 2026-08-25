import os
import pytest
from services.identity.oidc_routes import OidcRouteConfiguration, create_oidc_blueprint


@pytest.fixture(autouse=True)
def testing_environment(monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.delenv("FLASK_ENV", raising=False)

def test_oidc_routes_are_disabled_without_complete_configuration(monkeypatch):
    for key in ("OIDC_PROVIDER", "OIDC_ISSUER", "OIDC_AUTHORIZATION_ENDPOINT", "OIDC_TOKEN_ENDPOINT", "OIDC_JWKS_URI", "OIDC_CLIENT_ID", "OIDC_AUDIENCE", "OIDC_REDIRECT_URI", "OIDC_CLIENT_SECRET_REFERENCE", "OIDC_PROVIDER_TENANT_CLAIM", "OIDC_SIGNING_ALGORITHMS"): monkeypatch.delenv(key, raising=False)
    assert OidcRouteConfiguration.from_environment() is None
    assert create_oidc_blueprint(None) is None

def test_oidc_configuration_requires_all_values(monkeypatch):
    for key in ("OIDC_PROVIDER", "OIDC_ISSUER", "OIDC_AUTHORIZATION_ENDPOINT", "OIDC_TOKEN_ENDPOINT", "OIDC_JWKS_URI", "OIDC_CLIENT_ID", "OIDC_AUDIENCE", "OIDC_REDIRECT_URI", "OIDC_CLIENT_SECRET_REFERENCE", "OIDC_PROVIDER_TENANT_CLAIM"): monkeypatch.setenv(key, "configured")
    monkeypatch.setenv("OIDC_SIGNING_ALGORITHMS", "RS256"); monkeypatch.setenv("configured", "secret")
    assert OidcRouteConfiguration.from_environment().client_id == "configured"

def test_readiness_reports_missing_secret_without_exposing_secret(monkeypatch):
    for key in ("OIDC_PROVIDER", "OIDC_ISSUER", "OIDC_AUTHORIZATION_ENDPOINT", "OIDC_TOKEN_ENDPOINT", "OIDC_JWKS_URI", "OIDC_CLIENT_ID", "OIDC_AUDIENCE", "OIDC_REDIRECT_URI", "OIDC_CLIENT_SECRET_REFERENCE", "OIDC_PROVIDER_TENANT_CLAIM"): monkeypatch.setenv(key, "configured")
    monkeypatch.setenv("OIDC_SIGNING_ALGORITHMS", "RS256")
    result = OidcRouteConfiguration.readiness(dict(os.environ))
    assert result["ready"] is False and "secret" in result["reason"]

def test_deployment_readiness_requires_governed_trust(monkeypatch):
    env = {"OIDC_PROVIDER":"p", "OIDC_ISSUER":"https://issuer", "OIDC_AUTHORIZATION_ENDPOINT":"https://issuer/auth", "OIDC_TOKEN_ENDPOINT":"https://issuer/token", "OIDC_JWKS_URI":"https://issuer/jwks", "OIDC_CLIENT_ID":"client", "OIDC_AUDIENCE":"aud", "OIDC_REDIRECT_URI":"https://app/callback", "OIDC_CLIENT_SECRET_REFERENCE":"SECRET", "OIDC_PROVIDER_TENANT_CLAIM":"tid", "OIDC_SIGNING_ALGORITHMS":"RS256", "OIDC_EXTERNAL_TENANT_ID":"ext", "SECRET":"not-logged"}
    config = __import__("services.identity.oidc_config", fromlist=["OidcRuntimeConfiguration"]).OidcRuntimeConfiguration.from_environment(env)
    assert config.deployment_readiness(__import__("services.identity.oidc_config", fromlist=["OidcSecretProvider"]).OidcSecretProvider(env)).status == "TRUST_NOT_ESTABLISHED"
