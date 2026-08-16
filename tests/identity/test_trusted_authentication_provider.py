from pathlib import Path

import pytest

from database.connection import DatabaseConnection
from services.identity.authentication import (
    AuthenticatedProviderPrincipal,
    CanonicalAuthenticationBoundary,
    CanonicalAuthenticationError,
    TrustedProviderAdapter,
)
from services.identity.canonical_authority import CanonicalAuthorityService
from services.identity.request_context import CanonicalRequestContextService


class Provider:
    def __init__(self, principal=None, error=None): self.principal, self.error = principal, error
    def authenticate(self, request):
        if self.error: raise self.error
        return self.principal


def setup(tmp_path, principal):
    authority = CanonicalAuthorityService(DatabaseConnection(Path(tmp_path) / "provider.db"))
    authority.tenants.create("Acme", "tenant-a")
    authority.identities.create("a@example.com", actor_id="actor-a")
    authority.memberships.add("tenant-a", "actor-a", "admin")
    boundary = CanonicalAuthenticationBoundary(CanonicalRequestContextService(authority))
    return TrustedProviderAdapter(Provider(principal), boundary), authority


def principal(**overrides):
    values = dict(provider="enterprise-idp", subject="subject-a", tenant_id="tenant-a", actor_id="actor-a", authentication_method="oidc", credential_id="credential-a")
    values.update(overrides)
    return AuthenticatedProviderPrincipal(**values)


def test_valid_provider_principal_creates_canonical_context(tmp_path):
    adapter, _ = setup(tmp_path, principal())
    assert adapter.authenticate(object()).role == "admin"


@pytest.mark.parametrize("field", ["tenant_id", "actor_id"])
def test_missing_canonical_binding_fails_closed(tmp_path, field):
    values = {field: ""}
    adapter, _ = setup(tmp_path, principal(**values))
    with pytest.raises(CanonicalAuthenticationError): adapter.authenticate(object())


def test_provider_failure_does_not_fall_back_to_legacy_authentication(tmp_path):
    authority = CanonicalAuthorityService(DatabaseConnection(Path(tmp_path) / "provider.db"))
    boundary = CanonicalAuthenticationBoundary(CanonicalRequestContextService(authority))
    adapter = TrustedProviderAdapter(Provider(error=RuntimeError("invalid credentials")), boundary)
    with pytest.raises(CanonicalAuthenticationError, match="provider_authentication_failed"):
        adapter.authenticate(object())


@pytest.mark.parametrize("method", ["password", "legacy_session", "unknown"])
def test_unsupported_authentication_method_is_rejected(tmp_path, method):
    adapter, _ = setup(tmp_path, principal(authentication_method=method))
    with pytest.raises(CanonicalAuthenticationError, match="unsupported_authentication_method"):
        adapter.authenticate(object())


def test_provider_principal_has_no_authorization_fields(tmp_path):
    provider_principal = principal()
    assert not hasattr(provider_principal, "role")
    assert not hasattr(provider_principal, "permissions")
    assert not hasattr(provider_principal, "authority")
    adapter, _ = setup(tmp_path, provider_principal)
    assert adapter.authenticate(object()).role == "admin"


def test_inactive_canonical_identity_is_rejected(tmp_path):
    adapter, authority = setup(tmp_path, principal())
    with authority.db.session() as connection:
        connection.execute("UPDATE canonical_identities SET status='inactive' WHERE actor_id='actor-a'")
    with pytest.raises(CanonicalAuthenticationError, match="canonical_authentication_denied"):
        adapter.authenticate(object())

