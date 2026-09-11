"""Application-boundary separation for Entra requester/reviewer identities."""

from __future__ import annotations

from .entra_oidc import EntraBindingRepository, EntraIdentityTuple, EntraOidcError


def require_distinct_entra_identities(
    requester: EntraIdentityTuple,
    reviewer: EntraIdentityTuple,
    binding_repository: EntraBindingRepository | None = None,
) -> None:
    """Require two independently active, unambiguous bindings and distinct tuples."""
    if not isinstance(requester, EntraIdentityTuple) or not isinstance(reviewer, EntraIdentityTuple):
        raise EntraOidcError("entra_requester_reviewer_identity_missing")
    requester.validate()
    reviewer.validate()
    if requester == reviewer:
        raise EntraOidcError("entra_requester_reviewer_same_identity")
    repository = binding_repository or EntraBindingRepository()
    repository.resolve(requester)
    repository.resolve(reviewer)
