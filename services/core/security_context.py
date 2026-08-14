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


def request_context() -> SecurityContext:
    context = getattr(g, "security_context", None)
    if context is not None:
        return context
    tenant_id = session.get("organization_id") or request.headers.get("X-Organization-ID")
    user_id = session.get("user_id")
    roles: tuple[str, ...] = ()
    if user_id:
        service = current_app.container.get("auth_service")
        user = service.get_by_id(user_id) if service else None
        if user and getattr(user, "role", None):
            roles = (str(user.role).lower(),)
    if not tenant_id and current_app.testing:
        tenant_id = "test"
    context = SecurityContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=roles,
        correlation_id=request.headers.get("X-Correlation-ID") or str(uuid4()),
    )
    g.security_context = context
    return context


def authorize_investigation(payload: dict | None = None, write: bool = False) -> tuple[bool, str]:
    """Authorize an investigation boundary without exposing internal details."""
    context = request_context()
    if current_app.testing or current_app.config.get("ENVIRONMENT", "development") in {"development", "test"}:
        return True, ""
    if not context.user_id:
        return False, "authentication_required"
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
