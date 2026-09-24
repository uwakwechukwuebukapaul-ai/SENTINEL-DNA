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


def test_oidc_blueprint_requires_application_authentication_boundary():
    class Flow:
        def begin(self, _session): return "https://idp.example/authorize"

    assert create_oidc_blueprint(Flow()) is None


def test_oidc_callback_delegates_verified_principal_to_application_session():
    from flask import Flask

    class Flow:
        def complete(self, _session, _params): return "verified-principal"
        def begin(self, _session): return "https://idp.example/authorize"
        def logout(self, _session): pass

    received = []
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.register_blueprint(create_oidc_blueprint(Flow(), received.append))
    response = app.test_client().get("/auth/oidc/callback?code=opaque&state=valid")
    assert response.status_code == 302
    assert received == ["verified-principal"]


def test_oidc_callback_clears_partial_session_on_authentication_failure():
    from flask import Flask, session

    class Flow:
        def complete(self, _session, _params): raise ValueError("identity_binding_denied")
        def begin(self, _session): return "https://idp.example/authorize"
        def logout(self, _session): pass

    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.register_blueprint(create_oidc_blueprint(Flow(), lambda _principal: None))
    client = app.test_client()
    with client.session_transaction() as state:
        state.update(user_id=1, actor_id="actor", organization_id="tenant", mfa_session_token="partial")
    response = client.get("/auth/oidc/callback?code=opaque&state=bad")
    assert response.status_code == 401
    with client.session_transaction() as state:
        assert not any(key in state for key in ("user_id", "actor_id", "organization_id", "mfa_session_token", "auth_stage"))

def test_readiness_reports_missing_secret_without_exposing_secret(monkeypatch):
    for key in ("OIDC_PROVIDER", "OIDC_ISSUER", "OIDC_AUTHORIZATION_ENDPOINT", "OIDC_TOKEN_ENDPOINT", "OIDC_JWKS_URI", "OIDC_CLIENT_ID", "OIDC_AUDIENCE", "OIDC_REDIRECT_URI", "OIDC_CLIENT_SECRET_REFERENCE", "OIDC_PROVIDER_TENANT_CLAIM"): monkeypatch.setenv(key, "configured")
    monkeypatch.setenv("OIDC_SIGNING_ALGORITHMS", "RS256")
    result = OidcRouteConfiguration.readiness(dict(os.environ))
    assert result["ready"] is False and "secret" in result["reason"]

def test_deployment_readiness_requires_governed_trust(monkeypatch):
    env = {"OIDC_PROVIDER":"p", "OIDC_ISSUER":"https://issuer", "OIDC_AUTHORIZATION_ENDPOINT":"https://issuer/auth", "OIDC_TOKEN_ENDPOINT":"https://issuer/token", "OIDC_JWKS_URI":"https://issuer/jwks", "OIDC_CLIENT_ID":"client", "OIDC_AUDIENCE":"aud", "OIDC_REDIRECT_URI":"https://app/callback", "OIDC_CLIENT_SECRET_REFERENCE":"SECRET", "OIDC_PROVIDER_TENANT_CLAIM":"tid", "OIDC_SIGNING_ALGORITHMS":"RS256", "OIDC_EXTERNAL_TENANT_ID":"ext", "SECRET":"not-logged"}
    config = __import__("services.identity.oidc_config", fromlist=["OidcRuntimeConfiguration"]).OidcRuntimeConfiguration.from_environment(env)
    assert config.deployment_readiness(__import__("services.identity.oidc_config", fromlist=["OidcSecretProvider"]).OidcSecretProvider(env)).status == "TRUST_NOT_ESTABLISHED"
