import os
from services.identity.oidc_routes import OidcRouteConfiguration, create_oidc_blueprint

def test_oidc_routes_are_disabled_without_complete_configuration(monkeypatch):
    for key in ("OIDC_PROVIDER", "OIDC_ISSUER", "OIDC_AUTHORIZATION_ENDPOINT", "OIDC_TOKEN_ENDPOINT", "OIDC_JWKS_URI", "OIDC_CLIENT_ID", "OIDC_AUDIENCE", "OIDC_REDIRECT_URI", "OIDC_CLIENT_SECRET_REFERENCE", "OIDC_PROVIDER_TENANT_CLAIM", "OIDC_SIGNING_ALGORITHMS"): monkeypatch.delenv(key, raising=False)
    assert OidcRouteConfiguration.from_environment() is None
    assert create_oidc_blueprint(None) is None

def test_oidc_configuration_requires_all_values(monkeypatch):
    for key in ("OIDC_PROVIDER", "OIDC_ISSUER", "OIDC_AUTHORIZATION_ENDPOINT", "OIDC_TOKEN_ENDPOINT", "OIDC_JWKS_URI", "OIDC_CLIENT_ID", "OIDC_AUDIENCE", "OIDC_REDIRECT_URI", "OIDC_CLIENT_SECRET_REFERENCE", "OIDC_PROVIDER_TENANT_CLAIM"): monkeypatch.setenv(key, "configured")
    monkeypatch.setenv("OIDC_SIGNING_ALGORITHMS", "RS256"); monkeypatch.setenv("configured", "secret")
    assert OidcRouteConfiguration.from_environment().client_id == "configured"
