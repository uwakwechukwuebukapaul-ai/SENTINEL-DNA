from pathlib import Path
import pytest
from database.connection import DatabaseConnection
from services.identity.bindings import IdentityBindingService
from services.identity.oidc import OidcProviderConfiguration, OidcProviderAdapter, OidcTrustError, VerifiedOidcClaims


class Verifier:
    def __init__(self, claims=None, error=None): self.claims, self.error = claims, error
    def verify(self, *args):
        if self.error: raise self.error
        return self.claims


def setup(tmp_path, claims=None):
    db = DatabaseConnection(Path(tmp_path) / "oidc.db"); bindings = IdentityBindingService(db)
    from services.identity.canonical_authority import CanonicalAuthorityService
    authority = CanonicalAuthorityService(db); authority.identities.create("a@example.com", actor_id="actor-a")
    bindings.bind("entra", "subject-a", "actor-a", "operator")
    config = OidcProviderConfiguration("entra", "https://issuer.example", "client", "audience", "https://app/callback", "tenant-a")
    return OidcProviderAdapter(config, Verifier(claims), bindings)


def claims(**changes):
    values = dict(issuer="https://issuer.example", audience="audience", external_subject="subject-a", provider_tenant_id="tenant-a", credential_id="opaque")
    values.update(changes); return VerifiedOidcClaims(**values)


def test_verified_oidc_subject_resolves_binding(tmp_path):
    principal = setup(tmp_path, claims()).authenticate("code", "state", "nonce", "verifier")
    assert principal.actor_id == "actor-a" and principal.tenant_id == "tenant-a"


@pytest.mark.parametrize("field", ["issuer", "audience", "provider_tenant_id", "external_subject"])
def test_untrusted_oidc_claims_fail_closed(tmp_path, field):
    values = {field: "wrong" if field != "external_subject" else ""}
    with pytest.raises(OidcTrustError): setup(tmp_path, claims(**values)).authenticate("code", "state", "nonce", "verifier")


def test_missing_binding_fails_closed(tmp_path):
    with pytest.raises(OidcTrustError, match="identity_binding_denied"):
        setup(tmp_path, claims(external_subject="unknown")).authenticate("code", "state", "nonce", "verifier")


def test_missing_oidc_flow_parameters_fail_closed(tmp_path):
    with pytest.raises(OidcTrustError): setup(tmp_path, claims()).authenticate("", "state", "nonce", "verifier")

