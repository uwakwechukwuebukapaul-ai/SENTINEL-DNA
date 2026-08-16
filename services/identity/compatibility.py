"""Read-only compatibility seam between legacy web identity and tenant identity."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Protocol

class IdentityResolutionError(ValueError):
    """Raised when trusted identity or tenant resolution cannot complete."""

class DecisionSource(Protocol):
    def get(self, tenant_id: str, decision_id: str) -> Any: ...

@dataclass(frozen=True)
class CanonicalIdentityContext:
    tenant_id: str
    actor_id: str
    actor_type: str = "human"
    role: str = "viewer"
    authorization_scope: tuple[str, ...] = ()
    authentication_source: str = "legacy_web_session"
    organization_id: str = ""
    request_id: str = ""

@dataclass(frozen=True)
class DecisionVisibility:
    decision_id: str
    tenant_id: str
    exists: bool
    visible: bool
    eligible_for_feedback: bool

class IdentityCompatibility:
    """Resolve identity through explicit authorities; stores no mappings."""
    def __init__(self, *, organization_to_tenant: Callable[[str], Any], legacy_actor_to_canonical: Callable[[Any, str], Any], authorization: Any, identity_repository: Any) -> None:
        if not callable(organization_to_tenant): raise ValueError("organization_mapping_resolver_required")
        if not callable(legacy_actor_to_canonical): raise ValueError("actor_mapping_resolver_required")
        if authorization is None or not hasattr(authorization, "require_permission"): raise ValueError("tenant_authorization_required")
        if identity_repository is None or not hasattr(identity_repository, "get_user"): raise ValueError("identity_repository_required")
        self.organization_to_tenant, self.legacy_actor_to_canonical, self.authorization, self.identity_repository = organization_to_tenant, legacy_actor_to_canonical, authorization, identity_repository

    def resolve(self, legacy_actor_id: Any, organization_id: str, *, request_id: str = "", scope: tuple[str, ...] = (), role: str = "viewer") -> CanonicalIdentityContext:
        organization_id = str(organization_id or "").strip()
        if not organization_id: raise IdentityResolutionError("organization_id_required")
        mapping = self.organization_to_tenant(organization_id)
        if mapping is None: raise IdentityResolutionError("organization_tenant_mapping_absent")
        if isinstance(mapping, (list, tuple, set, frozenset)):
            values = {str(value).strip() for value in mapping if str(value).strip()}
            if not values: raise IdentityResolutionError("organization_tenant_mapping_absent")
            if len(values) > 1: raise IdentityResolutionError("organization_tenant_mapping_ambiguous")
            tenant_id = values.pop()
        else: tenant_id = str(mapping).strip()
        if not tenant_id or tenant_id == organization_id: raise IdentityResolutionError("organization_tenant_mapping_invalid")
        actor_id = str(self.legacy_actor_to_canonical(legacy_actor_id, tenant_id) or "").strip()
        if not actor_id: raise IdentityResolutionError("canonical_actor_unresolved")
        actor = self.identity_repository.get_user(actor_id, tenant_id)
        if actor is None: raise IdentityResolutionError("canonical_actor_not_found")
        if getattr(actor, "status", "active") != "active": raise IdentityResolutionError("canonical_actor_inactive")
        requested_scope = tuple(str(permission).strip() for permission in scope if str(permission).strip())
        if not requested_scope: raise IdentityResolutionError("authorization_scope_required")
        context = CanonicalIdentityContext(tenant_id, actor_id, role=role, authorization_scope=requested_scope, organization_id=organization_id, request_id=request_id)
        for permission in requested_scope: self.authorization.require_permission(context, tenant_id, permission)
        return context

class DecisionVisibilityResolver:
    """Perform tenant-scoped, read-only decision ownership checks."""
    def __init__(self, source: DecisionSource, authorization: Any) -> None:
        if source is None or not hasattr(source, "get"): raise ValueError("decision_source_required")
        if authorization is None or not hasattr(authorization, "can_access_resource"): raise ValueError("tenant_authorization_required")
        self.source, self.authorization = source, authorization

    def resolve(self, context: CanonicalIdentityContext, decision_id: str) -> DecisionVisibility:
        decision_id = str(decision_id or "").strip()
        if not decision_id: raise IdentityResolutionError("decision_id_required")
        decision = self.source.get(context.tenant_id, decision_id)
        if decision is None: return DecisionVisibility(decision_id, context.tenant_id, False, False, False)
        if str(getattr(decision, "tenant_id", "") or "") != context.tenant_id: return DecisionVisibility(decision_id, context.tenant_id, False, False, False)
        visible = bool(self.authorization.can_access_resource(context, context.tenant_id, "investigations.read"))
        eligible = bool(getattr(decision, "eligible_for_feedback", False))
        return DecisionVisibility(decision_id, context.tenant_id, True, visible, visible and eligible)
