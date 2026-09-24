import json
from types import SimpleNamespace

import pytest

import app as app_module
from app import _oidc_startup_readiness, create_app
from services.identity.oidc_config import OidcRuntimeConfiguration, OidcSecretProvider


def config(**changes):
    values = dict(
        provider="entra",
        issuer="https://issuer.example",
        authorization_endpoint="https://issuer.example/authorize",
        token_endpoint="https://issuer.example/token",
        jwks_uri="https://issuer.example/keys",
        client_id="client",
        audience="client",
        redirect_uri="https://app.example/auth/oidc/callback",
        client_secret_reference="OIDC_SECRET",
        provider_tenant_claim="tid",
        signing_algorithms=("RS256",),
        external_tenant_id="tenant-external",
    )
    values.update(changes)
    return OidcRuntimeConfiguration(**values)


class Trust:
    def resolve(self, *_args):
        return object()


def transport(discovery, jwks):
    def fetch(url, **_kwargs):
        payload = discovery if url.endswith("openid-configuration") else jwks
        return 200, json.dumps(payload)
    return fetch


def valid_documents(configuration):
    return (
        {
            "issuer": configuration.issuer,
            "authorization_endpoint": configuration.authorization_endpoint,
            "token_endpoint": configuration.token_endpoint,
            "jwks_uri": configuration.jwks_uri,
            "id_token_signing_alg_values_supported": ["RS256"],
        },
        {"keys": [{"kty": "RSA", "kid": "key-1", "alg": "RS256", "n": "n", "e": "e"}]},
    )


@pytest.fixture
def application(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "oidc-startup.sqlite"))
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    return create_app()


def test_invalid_discovery_metadata_prevents_readiness():
    configuration = config()
    discovery, jwks = valid_documents(configuration)
    discovery["issuer"] = "https://wrong.example"
    result = _oidc_startup_readiness(
        configuration,
        OidcSecretProvider({"OIDC_SECRET": "configured"}),
        Trust(),
        transport(discovery, jwks),
    )
    assert result.status == "METADATA_INVALID"


def test_invalid_jwks_prevents_readiness():
    configuration = config()
    discovery, jwks = valid_documents(configuration)
    jwks["keys"][0]["alg"] = "HS256"
    result = _oidc_startup_readiness(
        configuration,
        OidcSecretProvider({"OIDC_SECRET": "configured"}),
        Trust(),
        transport(discovery, jwks),
    )
    assert result.status == "METADATA_INVALID"


def test_complete_readiness_succeeds_only_with_discovery_and_jwks():
    configuration = config()
    discovery, jwks = valid_documents(configuration)
    result = _oidc_startup_readiness(
        configuration,
        OidcSecretProvider({"OIDC_SECRET": "configured"}),
        Trust(),
        transport(discovery, jwks),
    )
    assert result.status == "READY"


def test_incomplete_readiness_keeps_routes_and_button_disabled(application, monkeypatch):
    monkeypatch.setattr(app_module, "_oidc_startup_readiness", lambda *_args: SimpleNamespace(status="METADATA_INVALID"))
    assert app_module._build_oidc_blueprint(application, lambda _principal: None) is None
    assert application.config["OIDC_ROUTES_ENABLED"] is False
    assert b"Continue with Microsoft" not in application.test_client().get("/login").data


def test_ready_readiness_registers_routes_and_renders_button(application, monkeypatch):
    values = {
        "OIDC_PROVIDER": "entra",
        "OIDC_ISSUER": "https://issuer.example",
        "OIDC_AUTHORIZATION_ENDPOINT": "https://issuer.example/authorize",
        "OIDC_TOKEN_ENDPOINT": "https://issuer.example/token",
        "OIDC_JWKS_URI": "https://issuer.example/keys",
        "OIDC_CLIENT_ID": "client",
        "OIDC_AUDIENCE": "client",
        "OIDC_REDIRECT_URI": "https://app.example/auth/oidc/callback",
        "OIDC_CLIENT_SECRET_REFERENCE": "OIDC_SECRET",
        "OIDC_PROVIDER_TENANT_CLAIM": "tid",
        "OIDC_SIGNING_ALGORITHMS": "RS256",
        "OIDC_EXTERNAL_TENANT_ID": "tenant-external",
        "OIDC_SECRET": "configured",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(app_module, "_oidc_startup_readiness", lambda *_args: SimpleNamespace(status="READY"))
    blueprint = app_module._build_oidc_blueprint(application, lambda _principal: None)
    assert blueprint is not None
    application.register_blueprint(blueprint)
    application.config["OIDC_ROUTES_ENABLED"] = True
    application.config["OIDC_LOGIN_URL"] = "/auth/oidc/login"
    assert any(rule.rule == "/auth/oidc/login" for rule in application.url_map.iter_rules())
    assert b"Continue with Microsoft" in application.test_client().get("/login").data
