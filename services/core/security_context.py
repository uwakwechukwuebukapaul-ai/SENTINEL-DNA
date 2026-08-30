"""Request security context for API boundary authorization."""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from uuid import uuid4

from flask import current_app, g, request, session


@dataclass(frozen=True)
class SecurityContext:
    tenant_id: str | None
    user_id: str | None
    roles: tuple[str, ...]
    correlation_id: str
    actor_id: str | None = None
    pilot_authorization_id: str | None = None
    error: str | None = None


def request_context() -> SecurityContext:
    context = getattr(g, "security_context", None)
    if context is not None:
        return context
    user_id = session.get("user_id")
    principal = session.get("canonical_principal") or {}
    session_actor = session.get("actor_id")
    session_tenant = session.get("organization_id")
    header_tenant = request.headers.get("X-Organization-ID")
    tenant_id = None
    error = None
    roles: tuple[str, ...] = ()
    pilot_authorization_id = None
    if not isinstance(principal, Mapping):
        error = "canonical_identity_required"
        principal = {}
    principal_actor = principal.get("actor_id")
    principal_tenant = principal.get("tenant_id")
    if session_actor and principal_actor and str(session_actor) != str(principal_actor):
        error = "canonical_identity_conflict"
    if session_tenant and principal_tenant and str(session_tenant) != str(principal_tenant):
        error = "tenant_context_conflict"
    actor_id = session_actor or principal_actor
    session_tenant = session_tenant or principal_tenant
    if session_tenant and header_tenant and str(session_tenant) != str(header_tenant):
        error = "tenant_context_conflict"
    if user_id and actor_id:
        auth = current_app.container.get("auth_service")
        authenticated_user = (
            auth.session_user(user_id, session.get("session_version"))
            if auth is not None
            else None
        )
        if auth is not None and authenticated_user is None:
            error = "authentication_required"
            user_id = None
            actor_id = None
        elif authenticated_user is not None:
            if authenticated_user.actor_id and str(authenticated_user.actor_id) != str(actor_id):
                error = "canonical_identity_conflict"
            if authenticated_user.tenant_id and session_tenant and str(authenticated_user.tenant_id) != str(session_tenant):
                error = "tenant_context_conflict"
        if error:
            context = SecurityContext(
                tenant_id=None,
                user_id=user_id,
                roles=(),
                correlation_id=request.headers.get("X-Correlation-ID") or str(uuid4()),
                actor_id=str(actor_id) if actor_id else None,
                pilot_authorization_id=None,
                error=error,
            )
            g.security_context = context
            return context
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
            except Exception:
                if not error:
                    error = "tenant_access_denied"
        if not error and tenant_id and "analyst" in roles:
            pilot_service = current_app.container.get("pilot_authorization_service")
            authorization = None
            if pilot_service is not None:
                try:
                    authorization = pilot_service.active_for(str(actor_id), str(tenant_id))
                except Exception:
                    authorization = None
                pilot_authorization_id = authorization.authorization_id if authorization else None
            if current_app.config.get("PILOT_ACCESS_REQUIRED", False) and authorization is None:
                error = "pilot_authorization_required"
                tenant_id = None
                roles = ()
    elif user_id:
        error = "canonical_identity_required"
    context = SecurityContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=roles,
        correlation_id=request.headers.get("X-Correlation-ID") or str(uuid4()),
        actor_id=str(actor_id) if actor_id else None,
        pilot_authorization_id=pilot_authorization_id,
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
    if payload is not None and not isinstance(payload, dict):
        return False, "invalid_investigation_request"
    metadata = (payload or {}).get("metadata") or {}
    if not isinstance(metadata, dict):
        return False, "invalid_investigation_request"
    owner = metadata.get("tenant_id") or metadata.get("organization_id")
    if owner and owner != context.tenant_id:
        return False, "investigation_not_found"
    if write and current_app.config.get("PILOT_ACCESS_REQUIRED", False) and "analyst" in context.roles:
        pilot_service = current_app.container.get("pilot_authorization_service")
        scenario = metadata.get("scenario_id") or metadata.get("scenario")
        synthetic = metadata.get("synthetic")
        customer_data = metadata.get("customer_data")
        production = metadata.get("production") or metadata.get("production_impact")
        if not scenario:
            alert = (payload or {}).get("alert") or {}
            alert_metadata = alert.get("metadata") if isinstance(alert, dict) else {}
            if not isinstance(alert_metadata, dict):
                alert_metadata = {}
            scenario = (alert_metadata or {}).get("scenario_id") or (alert_metadata or {}).get("scenario")
            synthetic = (alert_metadata or {}).get("synthetic", synthetic)
            customer_data = (alert_metadata or {}).get("customer_data", customer_data)
            production = (alert_metadata or {}).get("production", production)
        if pilot_service is None or not context.pilot_authorization_id:
            return False, "pilot_authorization_required"
        if not scenario:
            return False, "pilot_scenario_required"
        if synthetic is not True or customer_data is True or production is True:
            return False, "pilot_synthetic_data_required"
        if not pilot_service.is_scenario_allowed(
            context.pilot_authorization_id,
            str(scenario),
            tenant_id=context.tenant_id,
        ):
            return False, "pilot_scenario_not_approved"
    return True, ""


__all__ = ["SecurityContext", "request_context", "authorize_investigation"]
