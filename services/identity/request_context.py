"""Canonical request security-context composition.

This boundary accepts canonical identifiers only. Legacy organization and
authentication identifiers must be resolved before reaching this service.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from .canonical_authority import (
    CanonicalAuthorityError,
    CanonicalAuthorityService,
    CanonicalIdentity,
    CanonicalMembership,
    CanonicalTenant,
)


@dataclass(frozen=True)
class CanonicalRequestContext:
    """Immutable, request-scoped canonical security context."""

    tenant_id: str
    actor_id: str
    role: str
    tenant: CanonicalTenant
    identity: CanonicalIdentity
    membership: CanonicalMembership
    request_id: str


class CanonicalRequestContextService:
    """Compose canonical request context after authoritative resolution."""

    def __init__(self, canonical_authority: CanonicalAuthorityService):
        if canonical_authority is None or not hasattr(canonical_authority, "resolve"):
            raise ValueError("canonical_authority_required")
        self.canonical_authority = canonical_authority

    def resolve(self, tenant_id: str, actor_id: str) -> CanonicalRequestContext:
        tenant_id = str(tenant_id or "").strip()
        actor_id = str(actor_id or "").strip()
        if not tenant_id:
            raise CanonicalAuthorityError("canonical_tenant_required")
        if not actor_id:
            raise CanonicalAuthorityError("canonical_actor_required")
        try:
            tenant, identity, membership = self.canonical_authority.resolve(tenant_id, actor_id)
        except Exception as exc:
            raise CanonicalAuthorityError("canonical_request_context_denied") from exc
        return CanonicalRequestContext(
            tenant_id=tenant.tenant_id,
            actor_id=identity.actor_id,
            role=membership.role,
            tenant=tenant,
            identity=identity,
            membership=membership,
            request_id=str(uuid4()),
        )

