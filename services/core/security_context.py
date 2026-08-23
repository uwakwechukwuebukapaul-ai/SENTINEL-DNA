"""Request security context for API boundary authorization."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from flask import current_app, g, request, session
from services.core.observability import normalize_correlation_id


@dataclass(frozen=True)
class SecurityContext:
    tenant_id: str | None
    user_id: str | None
    roles: tuple[str, ...]
    correlation_id: str
    actor_id: str | None = None
    tenant_context_valid: bool = True


def request_context() -> SecurityContext:
    context = getattr(g, "security_context", None)
    if context is not None:
        return context
    user_id = session.get("user_id")
    actor_id = session.get("actor_id")
    session_tenant = session.get("organization_id")
    header_tenant = request.headers.get("X-Organization-ID")
    tenant_id = None
    roles: tuple[str, ...] = ()
    tenant_context_valid = True
    if user_id:
        service = current_app.container.get("auth_service")
        user = service.get_by_id(user_id) if service else None
        if user:
            actor_id = getattr(user, "actor_id", None) or actor_id
            bound_tenant = getattr(user, "tenant_id", None)
            if bound_tenant and session_tenant and str(bound_tenant) != str(session_tenant):
                tenant_context_valid = False
            tenant_id = bound_tenant or session_tenant
            if header_tenant and str(header_tenant) != str(tenant_id):
                tenant_context_valid = False
            authority = current_app.container.get("canonical_authority")
            if tenant_id and actor_id and authority:
                try:
                    _tenant, _identity, membership = authority.resolve(str(tenant_id), str(actor_id))
                    roles = (str(membership.role).lower(),)
                except Exception:
                    tenant_context_valid = False
            elif tenant_id:
                tenant_context_valid = False
    elif header_tenant:
        tenant_context_valid = False
    context = SecurityContext(
        tenant_id=tenant_id,
        user_id=user_id,
        actor_id=actor_id,
        roles=roles,
        correlation_id=normalize_correlation_id(request.headers.get("X-Correlation-ID")),
        tenant_context_valid=tenant_context_valid,
    )
    g.security_context = context
    return context


def authorize_investigation(payload: dict | None = None, write: bool = False) -> tuple[bool, str]:
    """Authorize an investigation boundary without exposing internal details."""
    context = request_context()
    if not context.user_id:
        return False, "authentication_required"
    if not context.tenant_id or not context.tenant_context_valid:
        return False, "organization_context_required"
    allowed = {"admin", "soc_manager", "analyst"} if write else {"admin", "soc_manager", "analyst", "viewer"}
    if not set(context.roles).intersection(allowed):
        return False, "forbidden"
    metadata = (payload or {}).get("metadata") or {}
    owner = metadata.get("tenant_id") or metadata.get("organization_id")
    if owner and owner != context.tenant_id:
        return False, "investigation_not_found"
    return True, ""


__all__ = ["SecurityContext", "request_context", "authorize_investigation"]
