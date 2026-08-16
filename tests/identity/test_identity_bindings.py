from pathlib import Path
import pytest
from database.connection import DatabaseConnection
from services.identity.bindings import IdentityBindingError, IdentityBindingService
from services.identity.canonical_authority import CanonicalAuthorityService


def setup(tmp_path):
    db = DatabaseConnection(Path(tmp_path) / "bindings.db")
    authority = CanonicalAuthorityService(db)
    authority.identities.create("a@example.com", actor_id="actor-a")
    return IdentityBindingService(db), authority


def test_binding_resolves_deterministically_and_email_is_irrelevant(tmp_path):
    service, authority = setup(tmp_path)
    binding = service.bind("entra", "subject-a", "actor-a", "operator-1")
    authority.identities.create("changed@example.com", actor_id="actor-b")
    assert service.resolve("entra", "subject-a").actor_id == binding.actor_id


def test_duplicate_provider_subject_is_rejected(tmp_path):
    service, authority = setup(tmp_path)
    authority.identities.create("b@example.com", actor_id="actor-b")
    service.bind("entra", "subject-a", "actor-a", "operator-1")
    with pytest.raises(IdentityBindingError): service.bind("entra", "subject-a", "actor-b", "operator-1")


@pytest.mark.parametrize("status", ["disabled", "revoked"])
def test_inactive_binding_fails_closed(tmp_path, status):
    service, _ = setup(tmp_path)
    binding = service.bind("entra", "subject-a", "actor-a", "operator-1")
    service.set_status(binding.binding_id, status)
    with pytest.raises(IdentityBindingError): service.resolve("entra", "subject-a")


def test_binding_does_not_create_unknown_actor(tmp_path):
    service, _ = setup(tmp_path)
    with pytest.raises(IdentityBindingError):
        service.bind("entra", "subject-a", "missing-actor", "operator-1")
