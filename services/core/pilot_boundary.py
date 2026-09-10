"""Central deny-by-default policy for staging pilot analysts."""

from __future__ import annotations

import re

from flask import current_app, jsonify, request, session

from services.core.security_context import request_context


PILOT_ALLOWED_PERMISSIONS = frozenset(
    {
        "investigations:read",
        "investigations:run",
        "reports:read",
        "pilot:read",
    }
)


def _pilot_user():
    if not current_app.config.get("PILOT_ACCESS_REQUIRED", False):
        return None
    user_id = session.get("user_id")
    if not user_id:
        return None
    try:
        auth = current_app.container.get("auth_service")
    except Exception:
        return None
    if auth is None:
        return None
    try:
        user = auth.session_user(user_id, session.get("session_version"))
    except Exception:
        return None
    if user is None:
        return None
    # The database role is only a compatibility field.  When the canonical
    # authority says this actor is an analyst, retain the restrictive pilot
    # boundary even if the legacy role column was tampered with.
    if str(user.role).lower() == "analyst":
        return user
    principal = session.get("canonical_principal") or {}
    actor_id = session.get("actor_id") or (
        principal.get("actor_id") if isinstance(principal, dict) else None
    )
    tenant_id = session.get("organization_id") or (
        principal.get("tenant_id") if isinstance(principal, dict) else None
    )
    try:
        authority = current_app.container.get("canonical_authority")
        _tenant, _identity, membership = authority.resolve(str(tenant_id), str(actor_id))
    except Exception:
        return None
    if str(membership.role).lower() != "analyst":
        return None
    return user


def pilot_path_allowed(path: str, method: str) -> bool:
    """Return whether a path belongs to the explicitly approved pilot surface."""
    method = method.upper()
    readonly = {"GET", "HEAD", "OPTIONS"}
    if path in {"/", "/profile", "/health", "/ready", "/api/auth/me", "/api/dashboard/investigation"}:
        return method in readonly
    if path == "/api/auth/csrf":
        return method in readonly
    if path == "/api/auth/logout":
        return method in {"POST", "OPTIONS"}
    if path in {"/investigate", "/api/investigations", "/api/investigations/jobs", "/api/investigations/run"}:
        return method == "POST" or (path == "/api/investigations" and method == "GET")
    if path in {"/api/investigations/executions", "/api/investigations/feedback/analytics"}:
        return method in readonly
    if re.fullmatch(r"/api/investigations/executions/[^/]+", path):
        return method in readonly
    if re.fullmatch(
        r"/api/investigations/[^/]+(?:/(?:report|timeline|view|metrics|feedback|quality/evidence|quality))?",
        path,
    ):
        return method in readonly or (path.endswith("/feedback") and method == "POST")
    if path == "/api/pilot-authorizations/current":
        return method in readonly
    if re.fullmatch(r"/api/pilot-authorizations/[^/]+/scenarios", path):
        return method in readonly
    if path == "/api/pilot-provisioning/activate":
        return method in {"POST", "OPTIONS"}
    if path == "/workspace/":
        return method in readonly
    if re.fullmatch(r"/workspace/(?:investigation|analyst)/[^/]+", path):
        return method in readonly
    if re.fullmatch(r"/workspace/investigation/[^/]+/report", path):
        return method in readonly
    if re.fullmatch(r"/workspace/investigation/[^/]+/start", path):
        return method in {"POST", "OPTIONS"}
    if path.startswith("/workspace/dashboard/static/") or path.startswith("/static/"):
        return method in readonly
    return False


def _denied(error: str = "pilot_route_forbidden"):
    return jsonify({"error": error}), 403


def enforce_pilot_analyst_boundary():
    """Enforce active authorization and path allowlisting for pilot analysts."""
    user = _pilot_user()
    if user is None:
        return None
    if not pilot_path_allowed(request.path, request.method):
        return _denied()
    # An analyst without a current authorization may still obtain a CSRF token
    # and explicitly log out, but receives no identity, workspace, or API data.
    if request.path in {"/api/auth/csrf", "/api/auth/logout"}:
        return None
    context = request_context()
    if context.error:
        return _denied(context.error)
    if not context.tenant_id or not context.pilot_authorization_id:
        return _denied("pilot_authorization_required")
    return None


def pilot_permission_allowed(permission: str):
    """Apply the same policy when a route is tested outside the app factory."""
    if _pilot_user() is None:
        return True, None
    response = enforce_pilot_analyst_boundary()
    if response is not None:
        return False, response
    if permission not in PILOT_ALLOWED_PERMISSIONS:
        return False, _denied()
    return True, None


__all__ = [
    "PILOT_ALLOWED_PERMISSIONS",
    "enforce_pilot_analyst_boundary",
    "pilot_path_allowed",
    "pilot_permission_allowed",
]
