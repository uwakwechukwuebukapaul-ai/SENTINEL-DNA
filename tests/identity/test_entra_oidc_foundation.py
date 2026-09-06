import pytest
import json
import time
import sqlite3
from importlib import import_module

from services.identity.entra_oidc import (
    EntraOidcConfig,
    EntraOidcError,
    EntraIdentityTuple,
    begin_transaction,
    consume_transaction,
    pkce_challenge,
    EntraJwtValidator,
    validate_jwks_document,
)
from services.identity.entra_routes import create_entra_blueprint
from services.identity.entra_separation import require_distinct_entra_identities
from app import create_app
entra_migration = import_module("database.migrations.011_entra_identity_bindings")


TEST_TENANT_ID = "11111111-1111-4111-8111-111111111111"
TEST_CLIENT_ID = "22222222-2222-4222-8222-222222222222"
TEST_ISSUER = "https://login.microsoftonline.test/tenant/v2.0"
TEST_AUTHORIZATION = TEST_ISSUER + "/authorize"
TEST_TOKEN = TEST_ISSUER + "/token"
TEST_JWKS = TEST_ISSUER + "/keys"
TEST_DISCOVERY = TEST_ISSUER + "/.well-known/openid-configuration"
TEST_CERTIFIED_ORIGIN = "https://staging.example.test"
TEST_REDIRECT = "https://staging.example.test/auth/callback"


def config(**changes):
    values = dict(
        client_secret_reference="ENTRA_TEST_SECRET",
        redirect_uri=TEST_REDIRECT,
        certified_origin=TEST_CERTIFIED_ORIGIN,
        issuer=TEST_ISSUER,
        tenant_id=TEST_TENANT_ID,
        client_id=TEST_CLIENT_ID,
        authorization_endpoint=TEST_AUTHORIZATION,
        token_endpoint=TEST_TOKEN,
        jwks_uri=TEST_JWKS,
        discovery_uri=TEST_DISCOVERY,
    )
    values.update(changes)
    return EntraOidcConfig(**values)


@pytest.fixture
def entra_app(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "entra.sqlite"))
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    monkeypatch.setenv("SENTINEL_DNA_ENTRA_OIDC_ENABLED", "1")
    monkeypatch.setenv("SENTINEL_DNA_ENTRA_CLIENT_SECRET_REFERENCE", "ENTRA_TEST_SECRET")
    monkeypatch.setenv("SENTINEL_DNA_ENTRA_TENANT_ID", TEST_TENANT_ID)
    monkeypatch.setenv("SENTINEL_DNA_ENTRA_CLIENT_ID", TEST_CLIENT_ID)
    monkeypatch.setenv("SENTINEL_DNA_ENTRA_REDIRECT_URI", TEST_REDIRECT)
    monkeypatch.setenv("SENTINEL_DNA_CERTIFIED_ORIGIN", TEST_CERTIFIED_ORIGIN)
    monkeypatch.setenv("SENTINEL_DNA_ENTRA_ISSUER", TEST_ISSUER)
    monkeypatch.setenv("SENTINEL_DNA_ENTRA_AUTHORIZATION_ENDPOINT", TEST_AUTHORIZATION)
    monkeypatch.setenv("SENTINEL_DNA_ENTRA_TOKEN_ENDPOINT", TEST_TOKEN)
    monkeypatch.setenv("SENTINEL_DNA_ENTRA_JWKS_URI", TEST_JWKS)
    monkeypatch.setenv("SENTINEL_DNA_ENTRA_DISCOVERY_URI", TEST_DISCOVERY)
    application = create_app()
    application.config.update(TESTING=True)
    return application


def test_locked_configuration_and_pkce():
    cfg = config(); cfg.validate()
    session = {}
    url = begin_transaction(session, cfg)
    transaction = session["entra_oidc_transaction"]
    assert "code_challenge_method=S256" in url
    assert pkce_challenge(transaction["verifier"]) in url


def test_state_is_single_use_and_replay_fails():
    session = {}; begin_transaction(session, config())
    state = session["entra_oidc_transaction"]["state"]
    consume_transaction(session, state)
    with pytest.raises(EntraOidcError): consume_transaction(session, state)


def test_wrong_state_fails_and_consumes_transaction():
    session = {}; begin_transaction(session, config())
    with pytest.raises(EntraOidcError): consume_transaction(session, "wrong")
    assert "entra_oidc_transaction" not in session


def test_identity_tuple_is_not_display_identity():
    identity = EntraIdentityTuple(TEST_ISSUER, TEST_TENANT_ID, "oid", "sub")
    identity.validate()
    assert identity.object_id != identity.subject_id


def test_configuration_rejects_unsafe_redirect():
    with pytest.raises(EntraOidcError):
        config(client_secret_reference="x", redirect_uri="https://evil.example/callback").validate()


def test_external_configuration_is_required_and_validated(monkeypatch):
    values = {
        "SENTINEL_DNA_ENTRA_CLIENT_SECRET_REFERENCE": "ENTRA_TEST_SECRET",
        "SENTINEL_DNA_ENTRA_TENANT_ID": TEST_TENANT_ID,
        "SENTINEL_DNA_ENTRA_CLIENT_ID": TEST_CLIENT_ID,
        "SENTINEL_DNA_ENTRA_REDIRECT_URI": TEST_REDIRECT,
        "SENTINEL_DNA_CERTIFIED_ORIGIN": TEST_CERTIFIED_ORIGIN,
        "SENTINEL_DNA_ENTRA_ISSUER": TEST_ISSUER,
        "SENTINEL_DNA_ENTRA_AUTHORIZATION_ENDPOINT": TEST_AUTHORIZATION,
        "SENTINEL_DNA_ENTRA_TOKEN_ENDPOINT": TEST_TOKEN,
        "SENTINEL_DNA_ENTRA_JWKS_URI": TEST_JWKS,
        "SENTINEL_DNA_ENTRA_DISCOVERY_URI": TEST_DISCOVERY,
    }
    loaded = EntraOidcConfig.from_environment(values)
    loaded.validate()
    for missing in ("SENTINEL_DNA_ENTRA_TENANT_ID", "SENTINEL_DNA_ENTRA_CLIENT_ID", "SENTINEL_DNA_ENTRA_REDIRECT_URI"):
        incomplete = dict(values)
        incomplete.pop(missing)
        with pytest.raises(EntraOidcError, match="configuration_missing"):
            EntraOidcConfig.from_environment(incomplete)
    malformed = dict(values, SENTINEL_DNA_ENTRA_REDIRECT_URI="http://not-https.test/callback")
    with pytest.raises(EntraOidcError, match="endpoint_untrusted"):
        EntraOidcConfig.from_environment(malformed).validate()
    monkeypatch.setenv("SENTINEL_DNA_ENTRA_OIDC_ENABLED", "1")
    for key in values:
        monkeypatch.delenv(key, raising=False)
    assert create_entra_blueprint() is None


def test_entra_configuration_has_no_source_identity_defaults():
    import services.identity.entra_oidc as module
    source = open(module.__file__, encoding="utf-8").read()
    assert not hasattr(module, "ENTRA_TENANT_ID")
    assert not hasattr(module, "ENTRA_CLIENT_ID")
    assert not hasattr(module, "ENTRA_REDIRECT_URI")
    assert "login.microsoftonline.com" not in source
    assert "taile388cc" not in source


def test_configuration_errors_do_not_echo_secret_or_identifiers():
    with pytest.raises(EntraOidcError) as error:
        EntraOidcConfig.from_environment({"SENTINEL_DNA_ENTRA_CLIENT_SECRET_REFERENCE": "SECRET_REFERENCE"})
    assert "SECRET_REFERENCE" not in str(error.value)


def test_flask_boundary_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SENTINEL_DNA_ENTRA_OIDC_ENABLED", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_ENTRA_CLIENT_SECRET_REFERENCE", raising=False)
    assert create_entra_blueprint() is None


def test_transaction_has_id_expiry_and_consumed_status():
    session = {}
    begin_transaction(session, config())
    # The transaction is intentionally removed on consumption; inspect its
    # durable fields before consuming it.
    session = {}
    begin_transaction(session, config())
    record = session["entra_oidc_transaction"]
    assert record["transaction_id"] and record["status"] == "pending"
    assert record["expires_at"] > record["created_at"]
    consumed = consume_transaction(session, record["state"])
    assert consumed["status"] == "consumed" and consumed["consumed_at"]


def test_expired_transaction_fails_closed():
    session = {"entra_oidc_transaction": {"status": "pending", "state": "s", "nonce": "n", "verifier": "v", "created_at": 1, "expires_at": 1}}
    with pytest.raises(EntraOidcError, match="expired"):
        consume_transaction(session, "s")


def test_entra_logout_reuses_csrf_and_clears_remember_cookie(entra_app):
    client = entra_app.test_client()
    with client.session_transaction() as browser_session:
        browser_session.update(test_marker="present", csrf_token="csrf")
    assert client.post("/auth/logout").status_code == 403
    response = client.post("/auth/logout", headers={"X-CSRF-Token": "csrf"})
    assert response.status_code == 200
    assert any("sentinel_remember=" in value and "expires=" in value.lower() for value in response.headers.getlist("Set-Cookie"))
    with client.session_transaction() as browser_session:
        assert not browser_session


def test_jwks_requires_unique_rsa_signing_keys():
    valid = {"keys": [{"kid": "k1", "kty": "RSA", "use": "sig", "alg": "RS256", "n": "AQ", "e": "AQAB"}]}
    assert validate_jwks_document(valid)[0]["kid"] == "k1"
    for document in (
        {},
        {"keys": "not-an-array"},
        {"keys": [{"kid": "k1", "kty": "EC", "n": "AQ", "e": "AQAB"}]},
        {"keys": [{"kid": "k1", "kty": "RSA", "alg": "HS256", "n": "AQ", "e": "AQAB"}]},
        {"keys": [{"kid": "k1", "kty": "RSA", "n": "AQ"}]},
        {"keys": [{"kid": "k1", "kty": "RSA", "n": "AQ", "e": "AQAB"}, {"kid": "k1", "kty": "RSA", "n": "AQ", "e": "AQAB"}]},
    ):
        with pytest.raises(EntraOidcError):
            validate_jwks_document(document)


class _BindingRepo:
    def __init__(self, active=True):
        self.active = active
        self.calls = []

    def resolve(self, identity):
        self.calls.append(identity)
        if not self.active:
            raise EntraOidcError("entra_identity_binding_denied")
        return {"user_id": 1, "status": "active"}


def test_requester_reviewer_separation_uses_tuple_only():
    requester = EntraIdentityTuple(TEST_ISSUER, TEST_TENANT_ID, "oid-a", "sub-a")
    reviewer = EntraIdentityTuple(TEST_ISSUER, TEST_TENANT_ID, "oid-b", "sub-b")
    repo = _BindingRepo()
    require_distinct_entra_identities(requester, reviewer, repo)
    assert repo.calls == [requester, reviewer]
    with pytest.raises(EntraOidcError, match="same_identity"):
        require_distinct_entra_identities(requester, requester, repo)
    with pytest.raises(EntraOidcError):
        require_distinct_entra_identities(requester, reviewer, _BindingRepo(active=False))


def test_entra_binding_migration_is_additive_and_reversible_in_isolated_sqlite():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
    entra_migration.upgrade(connection)
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(entra_identity_bindings)")}
    assert {"binding_id", "user_id", "issuer", "tenant_id", "object_id", "subject_id", "status", "revoked_at"} <= columns
    connection.execute("INSERT INTO users(id) VALUES (1)")
    values = ("b1", 1, TEST_ISSUER, TEST_TENANT_ID, "oid", "sub", "active", "now", "now", "test", None)
    connection.execute("INSERT INTO entra_identity_bindings VALUES (?,?,?,?,?,?,?,?,?,?,?)", values)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO entra_identity_bindings VALUES (?,?,?,?,?,?,?,?,?,?,?)", ("b2", 1, TEST_ISSUER, TEST_TENANT_ID, "oid", "sub", "active", "now", "now", "test", None))
    entra_migration.downgrade(connection)
    assert connection.execute("SELECT name FROM sqlite_master WHERE name='entra_identity_bindings'").fetchone() is None
