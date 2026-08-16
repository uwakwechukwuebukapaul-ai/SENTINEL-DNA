from pathlib import Path
from flask import Flask, g, session
import pytest

from database.connection import DatabaseConnection
from services.identity.authentication import AuthenticatedProviderPrincipal, CanonicalAuthenticationBoundary, TrustedProviderAdapter
from services.identity.canonical_authority import CanonicalAuthorityService
from services.identity.flask_integration import canonical_request_context, require_canonical_authentication
from services.identity.request_context import CanonicalRequestContextService


class Provider:
    def __init__(self, principal): self.principal = principal
    def authenticate(self, request): return self.principal


def app(tmp_path, principal):
    db = DatabaseConnection(Path(tmp_path) / "flask.db"); authority = CanonicalAuthorityService(db)
    authority.tenants.create("Acme", "tenant-a"); authority.identities.create("a@example.com", actor_id="actor-a"); authority.memberships.add("tenant-a", "actor-a", "admin")
    boundary = CanonicalAuthenticationBoundary(CanonicalRequestContextService(authority))
    adapter = TrustedProviderAdapter(Provider(principal), boundary)
    flask_app = Flask(__name__); flask_app.secret_key = "test-only"

    @flask_app.get("/canonical")
    @require_canonical_authentication(adapter)
    def canonical(): return {"tenant_id": canonical_request_context().tenant_id, "actor_id": canonical_request_context().actor_id, "role": canonical_request_context().role}

    flask_app.canonical_adapter = adapter
    return flask_app


def principal(**changes):
    values = dict(provider="entra", subject="subject-a", tenant_id="tenant-a", actor_id="actor-a", authentication_method="oidc", credential_id="credential-a", external_subject="")
    values.update(changes); return AuthenticatedProviderPrincipal(**values)


def test_valid_provider_creates_request_local_context(tmp_path):
    client = app(tmp_path, principal()).test_client()
    response = client.get("/canonical")
    assert response.status_code == 200 and response.json["role"] == "admin"


def test_invalid_provider_fails_closed_and_legacy_session_is_ignored(tmp_path):
    client = app(tmp_path, principal(actor_id="missing" )).test_client()
    with client.session_transaction() as state: state["user_id"] = 1; state["organization_id"] = "tenant-a"
    response = client.get("/canonical")
    assert response.status_code == 401


def test_context_is_request_scoped(tmp_path):
    flask_app = app(tmp_path, principal()); seen = []
    @flask_app.get("/capture")
    @require_canonical_authentication(flask_app.canonical_adapter)
    def capture(): seen.append(g.canonical_request_context.request_id); return "ok"
    client = flask_app.test_client(); assert client.get("/capture").status_code == 200; assert client.get("/capture").status_code == 200
    assert len(seen) == 2 and seen[0] != seen[1]
