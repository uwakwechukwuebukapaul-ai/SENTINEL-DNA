from datetime import datetime, timedelta, timezone

import jwt
import pytest
from flask import Flask

from services.identity.entra_oidc import EntraJwtValidator, EntraOidcConfig, ExternalSecretReferenceResolver
from services.identity.entra_routes import create_entra_blueprint
from services.identity.enterprise_registry import load_enterprise_oidc_registry
from services.identity.enterprise_routes import operational_providers


TENANT = "11111111-1111-4111-8111-111111111111"
CLIENT = "22222222-2222-4222-8222-222222222222"
ISSUER = "https://login.microsoftonline.com/11111111-1111-4111-8111-111111111111/v2.0"
AZURE_BASE = "https://login.microsoftonline.com/11111111-1111-4111-8111-111111111111"


def config(**changes):
    values = dict(
        client_secret_reference="ENTRA_CLIENT_SECRET",
        redirect_uri="https://soc.example.test/auth/enterprise/entra/callback",
        certified_origin="https://soc.example.test",
        issuer=ISSUER,
        tenant_id=TENANT,
        client_id=CLIENT,
        authorization_endpoint=ISSUER + "/authorize",
        token_endpoint=ISSUER + "/token",
        jwks_uri=ISSUER + "/discovery/keys",
        discovery_uri=ISSUER + "/.well-known/openid-configuration",
    )
    values.update(changes)
    return EntraOidcConfig(**values)


def test_entra_registry_is_unavailable_without_explicit_configuration(monkeypatch):
    monkeypatch.delenv("SENTINEL_DNA_ENTRA_OIDC_ENABLED", raising=False)
    assert load_enterprise_oidc_registry({}) == {}


def test_entra_blueprint_registers_literal_enterprise_routes(monkeypatch):
    values = {
        "SENTINEL_DNA_ENTRA_OIDC_ENABLED": "1",
        "SENTINEL_DNA_ENTRA_CLIENT_SECRET_REFERENCE": "SENTINEL_DNA_ENTRA_CLIENT_SECRET",
        "SENTINEL_DNA_ENTRA_TENANT_ID": TENANT,
        "SENTINEL_DNA_ENTRA_CLIENT_ID": CLIENT,
        "SENTINEL_DNA_ENTRA_REDIRECT_URI": "https://soc.example.test/auth/enterprise/entra/callback",
        "SENTINEL_DNA_CERTIFIED_ORIGIN": "https://soc.example.test",
        "SENTINEL_DNA_ENTRA_ISSUER": ISSUER,
        "SENTINEL_DNA_ENTRA_AUTHORIZATION_ENDPOINT": AZURE_BASE + "/oauth2/v2.0/authorize",
        "SENTINEL_DNA_ENTRA_TOKEN_ENDPOINT": AZURE_BASE + "/oauth2/v2.0/token",
        "SENTINEL_DNA_ENTRA_JWKS_URI": AZURE_BASE + "/discovery/v2.0/keys",
        "SENTINEL_DNA_ENTRA_DISCOVERY_URI": ISSUER + "/.well-known/openid-configuration",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)

    blueprint = create_entra_blueprint()
    assert blueprint is not None
    application = Flask(__name__)
    application.register_blueprint(blueprint)
    rules = {rule.rule for rule in application.url_map.iter_rules()}
    assert "/auth/enterprise/entra/login" in rules
    assert "/auth/enterprise/entra/callback" in rules


def test_disabled_entra_blueprint_has_no_routes(monkeypatch):
    monkeypatch.delenv("SENTINEL_DNA_ENTRA_OIDC_ENABLED", raising=False)
    assert create_entra_blueprint() is None


def test_enabled_local_entra_configuration_loads_without_secret_in_configuration():
    values = {
        "SENTINEL_DNA_ENTRA_OIDC_ENABLED": "1",
        "SENTINEL_DNA_ENTRA_CLIENT_SECRET_REFERENCE": "SENTINEL_DNA_ENTRA_CLIENT_SECRET",
        "SENTINEL_DNA_ENTRA_TENANT_ID": TENANT,
        "SENTINEL_DNA_ENTRA_CLIENT_ID": CLIENT,
        "SENTINEL_DNA_ENTRA_REDIRECT_URI": "https://localhost/auth/enterprise/entra/callback",
        "SENTINEL_DNA_CERTIFIED_ORIGIN": "https://localhost",
        "SENTINEL_DNA_ENTRA_ISSUER": ISSUER,
        "SENTINEL_DNA_ENTRA_AUTHORIZATION_ENDPOINT": AZURE_BASE + "/oauth2/v2.0/authorize",
        "SENTINEL_DNA_ENTRA_TOKEN_ENDPOINT": AZURE_BASE + "/oauth2/v2.0/token",
        "SENTINEL_DNA_ENTRA_JWKS_URI": AZURE_BASE + "/discovery/v2.0/keys",
        "SENTINEL_DNA_ENTRA_DISCOVERY_URI": ISSUER + "/.well-known/openid-configuration",
    }
    registry = load_enterprise_oidc_registry(values)
    assert set(registry) == {"entra"}
    assert registry["entra"].configuration.redirect_uri == "https://localhost/auth/enterprise/entra/callback"
    assert registry["entra"].configuration.client_secret_reference == "SENTINEL_DNA_ENTRA_CLIENT_SECRET"
    assert "secret-value" not in repr(registry["entra"])


def test_entra_registry_resolves_external_secret_file(tmp_path):
    secret_file = tmp_path / "entra-client-secret"
    secret_file.write_text("secret-value\n", encoding="utf-8")
    values = {
        "SENTINEL_DNA_ENTRA_OIDC_ENABLED": "1",
        "SENTINEL_DNA_ENTRA_CLIENT_SECRET_REFERENCE": "SENTINEL_DNA_ENTRA_CLIENT_SECRET",
        "SENTINEL_DNA_ENTRA_CLIENT_SECRET_FILE": str(secret_file),
        "SENTINEL_DNA_ENTRA_TENANT_ID": TENANT,
        "SENTINEL_DNA_ENTRA_CLIENT_ID": CLIENT,
        "SENTINEL_DNA_ENTRA_REDIRECT_URI": "https://localhost/auth/enterprise/entra/callback",
        "SENTINEL_DNA_CERTIFIED_ORIGIN": "https://localhost",
        "SENTINEL_DNA_ENTRA_ISSUER": ISSUER,
        "SENTINEL_DNA_ENTRA_AUTHORIZATION_ENDPOINT": AZURE_BASE + "/oauth2/v2.0/authorize",
        "SENTINEL_DNA_ENTRA_TOKEN_ENDPOINT": AZURE_BASE + "/oauth2/v2.0/token",
        "SENTINEL_DNA_ENTRA_JWKS_URI": AZURE_BASE + "/discovery/v2.0/keys",
        "SENTINEL_DNA_ENTRA_DISCOVERY_URI": ISSUER + "/.well-known/openid-configuration",
    }
    registry = load_enterprise_oidc_registry(values)
    assert registry["entra"].secret_resolver("SENTINEL_DNA_ENTRA_CLIENT_SECRET") == "secret-value"


def test_entra_registry_resolves_short_sentinel_reference_to_external_secret_file(tmp_path):
    secret_file = tmp_path / "entra-client-secret"
    secret_file.write_text("secret-value\n", encoding="utf-8")
    values = {
        "SENTINEL_DNA_ENTRA_OIDC_ENABLED": "1",
        "SENTINEL_DNA_ENTRA_CLIENT_SECRET_REFERENCE": "entra_client_secret",
        "SENTINEL_DNA_ENTRA_CLIENT_SECRET_FILE": str(secret_file),
        "SENTINEL_DNA_ENTRA_TENANT_ID": TENANT,
        "SENTINEL_DNA_ENTRA_CLIENT_ID": CLIENT,
        "SENTINEL_DNA_ENTRA_REDIRECT_URI": "https://localhost/auth/enterprise/entra/callback",
        "SENTINEL_DNA_CERTIFIED_ORIGIN": "https://localhost",
        "SENTINEL_DNA_ENTRA_ISSUER": ISSUER,
        "SENTINEL_DNA_ENTRA_AUTHORIZATION_ENDPOINT": AZURE_BASE + "/oauth2/v2.0/authorize",
        "SENTINEL_DNA_ENTRA_TOKEN_ENDPOINT": AZURE_BASE + "/oauth2/v2.0/token",
        "SENTINEL_DNA_ENTRA_JWKS_URI": AZURE_BASE + "/discovery/v2.0/keys",
        "SENTINEL_DNA_ENTRA_DISCOVERY_URI": ISSUER + "/.well-known/openid-configuration",
    }
    registry = load_enterprise_oidc_registry(values)
    assert registry["entra"].secret_resolver("entra_client_secret") == "secret-value"


def test_external_secret_resolver_never_reads_raw_environment_values(tmp_path):
    secret_file = tmp_path / "entra-client-secret"
    secret_file.write_text("file-secret\n", encoding="utf-8")
    resolver = ExternalSecretReferenceResolver({
        "entra_client_secret": "raw-secret",
        "SENTINEL_DNA_ENTRA_CLIENT_SECRET": "raw-secret",
        "SENTINEL_DNA_ENTRA_CLIENT_SECRET_FILE": str(secret_file),
    })
    assert resolver("entra_client_secret") == "file-secret"
    assert resolver("missing_secret") == ""


def test_provider_appears_only_when_configuration_and_health_are_valid():
    class Flow:
        configuration = config()
        begin = lambda self: None
        complete = lambda self, *_: None
        health_check = lambda self: True

    assert operational_providers({"entra": Flow()}) == [{
        "id": "entra",
        "name": "Microsoft Entra ID",
        "start_url": "/auth/enterprise/entra/start",
    }]

    class Unhealthy(Flow):
        health_check = lambda self: False

    assert operational_providers({"entra": Unhealthy()}) == []


def signed_token(private_key, **changes):
    now = datetime.now(timezone.utc)
    claims = {
        "iss": ISSUER, "tid": TENANT, "oid": "33333333-3333-4333-8333-333333333333",
        "sub": "entra-subject", "aud": CLIENT, "exp": int((now + timedelta(minutes=5)).timestamp()),
        "nbf": int((now - timedelta(seconds=1)).timestamp()), "iat": int(now.timestamp()),
        "nonce": "nonce", "roles": ["sdna.requester"], "ver": "2.0",
    }
    claims.update(changes)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "entra-key"})


def validator(private_key):
    class Key:
        key = private_key.public_key()

    class Client:
        def get_signing_key_from_jwt(self, token):
            return Key()

    class Response:
        status_code = 200
        content = b'{"keys":[{"kid":"entra-key","kty":"RSA","use":"sig","alg":"RS256","n":"AQ","e":"AQAB"}]}'

        def json(self):
            return {"keys": [{"kid": "entra-key", "kty": "RSA", "use": "sig", "alg": "RS256", "n": "AQ", "e": "AQAB"}]}

    return EntraJwtValidator(config(), lambda *_: Client(), lambda *_, **__: Response())


@pytest.fixture
def rsa_key():
    from cryptography.hazmat.primitives.asymmetric import rsa
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def test_invalid_issuer_rejected(rsa_key):
    with pytest.raises(ValueError, match="entra_token_invalid"):
        validator(rsa_key).validate(signed_token(rsa_key, iss="https://attacker.example/v2.0"), "nonce")


def test_invalid_audience_rejected(rsa_key):
    with pytest.raises(ValueError, match="entra_token_invalid"):
        validator(rsa_key).validate(signed_token(rsa_key, aud="wrong-client"), "nonce")


def test_expired_token_rejected(rsa_key):
    with pytest.raises(ValueError, match="entra_token_invalid"):
        validator(rsa_key).validate(signed_token(rsa_key, exp=1), "nonce")


def test_tenant_mismatch_rejected(rsa_key):
    with pytest.raises(ValueError, match="entra_identity_claim_mismatch"):
        validator(rsa_key).validate(signed_token(rsa_key, tid="44444444-4444-4444-8444-444444444444"), "nonce")
