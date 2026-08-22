"""Request security context for API boundary authorization."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from flask import current_app, g, request, session


@dataclass(frozen=True)
class SecurityContext:
    tenant_id: str | None
    user_id: str | None
    roles: tuple[str, ...]
    correlation_id: str
    actor_id: str | None = None
    error: str | None = None


def request_context() -> SecurityContext:
    context = getattr(g, "security_context", None)
    if context is not None:
        return context
    user_id = session.get("user_id")
    principal = session.get("canonical_principal") or {}
    actor_id = session.get("actor_id") or principal.get("actor_id")
    session_tenant = session.get("organization_id")
    header_tenant = request.headers.get("X-Organization-ID")
    tenant_id = None
    error = None
    roles: tuple[str, ...] = ()
    if user_id and actor_id:
        if session_tenant and header_tenant and str(session_tenant) != str(header_tenant):
            error = "tenant_context_conflict"
        else:
            if header_tenant and not session_tenant:
                error = "tenant_context_required"
                candidate = None
            else:
                candidate = session_tenant
            authority = current_app.container.get("canonical_authority")
            try:
                if error:
                    raise ValueError(error)
                if candidate:
                    tenant, _identity, membership = authority.resolve(str(candidate), str(actor_id))
                    tenant_id = tenant.tenant_id
                    roles = (str(membership.role).lower(),)
                else:
                    memberships = [m for m in authority.memberships.list_for_actor(str(actor_id)) if m.status == "active"]
                    if len(memberships) == 1:
                        tenant_id = memberships[0].tenant_id
                        roles = (str(memberships[0].role).lower(),)
                    elif len(memberships) > 1:
                        error = "organization_context_required"
                    else:
                        error = "tenant_membership_required"
            except (LookupError, PermissionError, ValueError):
                error = "tenant_access_denied"
    elif user_id:
        error = "canonical_identity_required"
    context = SecurityContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=roles,
        correlation_id=request.headers.get("X-Correlation-ID") or str(uuid4()),
        actor_id=str(actor_id) if actor_id else None,
        error=error,
    )
    g.security_context = context
    return context


def authorize_investigation(payload: dict | None = None, write: bool = False) -> tuple[bool, str]:
    """Authorize an investigation boundary without exposing internal details."""
    context = request_context()
    if not context.user_id:
        return False, "authentication_required"
    if context.error:
        return False, context.error
    if not context.actor_id:
        return False, "canonical_identity_required"
    if not context.tenant_id:
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
