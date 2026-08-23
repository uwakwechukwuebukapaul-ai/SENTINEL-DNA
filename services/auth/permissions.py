from __future__ import annotations
from functools import wraps
from flask import current_app, jsonify, session

ROLE_ALIASES = {"ADMIN": "admin", "SOC_MANAGER": "soc_manager", "ANALYST": "analyst", "VIEWER": "viewer"}
PERMISSIONS = {
    "investigations:read": {"admin", "soc_manager", "analyst", "viewer"},
    "investigations:run": {"admin", "soc_manager", "analyst"},
    "reports:read": {"admin", "soc_manager", "analyst", "viewer"},
    "cases:assign": {"admin", "soc_manager"},
    "cases:notes": {"admin", "soc_manager", "analyst"},
    "exports:read": {"admin", "soc_manager", "analyst"},
    "hunting:read": {"admin", "soc_manager", "analyst", "viewer"},
    "hunting:execute": {"admin", "soc_manager", "analyst"},
    "automation:read": {"admin", "soc_manager", "analyst", "viewer"},
    "automation:execute": {"admin", "soc_manager", "analyst"},
    "automation:manage": {"admin", "soc_manager"},
    "integrations:read": {"admin", "soc_manager", "analyst", "viewer"},
    "integrations:test": {"admin", "soc_manager", "analyst"},
    "integrations:manage": {"admin", "soc_manager"},
    "detection:read": {"admin", "soc_manager", "analyst", "viewer"},
    "detection:ingest": {"admin", "soc_manager", "analyst"},
    "adversary:read": {"admin", "soc_manager", "analyst", "viewer"},
    "adversary:execute": {"admin", "soc_manager", "analyst"},
    "adversary:manage": {"admin", "soc_manager"},
    "validation:read": {"admin", "soc_manager", "analyst", "viewer"},
    "validation:execute": {"admin", "soc_manager", "analyst"},
    "organizations:create": {"admin", "soc_manager", "analyst"},
    "connectors:read": {"admin", "soc_manager", "analyst", "viewer"},
    "connectors:test": {"admin", "soc_manager", "analyst"},
    "connectors:collect": {"admin", "soc_manager", "analyst"},
    "connectors:manage": {"admin", "soc_manager"},
    "streaming:read": {"admin", "soc_manager", "analyst", "viewer"},
    "streaming:publish": {"admin", "soc_manager", "analyst"},
    "reasoning:read": {"admin", "soc_manager", "analyst", "viewer"},
    "reasoning:execute": {"admin", "soc_manager", "analyst"},
    "copilot:read": {"admin", "soc_manager", "analyst", "viewer"},
    "copilot:use": {"admin", "soc_manager", "analyst"},
    "governance:read": {"admin", "soc_manager", "analyst", "viewer"},
    "governance:approve": {"admin", "soc_manager"},
    "marketplace:read": {"admin", "soc_manager", "analyst", "viewer"},
    "incidents:read": {"admin", "soc_manager", "analyst", "viewer"},
    "incidents:manage": {"admin", "soc_manager", "analyst"},
    "api:read": {"admin", "soc_manager"},
    "api:manage": {"admin", "soc_manager"},
    "audit:read": {"admin", "soc_manager"},
    "billing:read": {"admin", "soc_manager"},
    "mssp:read": {"admin", "soc_manager"},
    "compliance:read": {"admin", "soc_manager", "analyst", "viewer"},
    "mlops:read": {"admin", "soc_manager"},
    "monitoring:read": {"admin", "soc_manager", "analyst", "viewer"},
    "customer_success:read": {"admin", "soc_manager"},
    "product_analytics:read": {"admin", "soc_manager"},
    "pilot:read": {"admin", "soc_manager", "analyst", "viewer"},
    "pilot:manage": {"admin", "soc_manager"},
    "support:read": {"admin", "soc_manager", "analyst", "viewer"},
    "exercises:read": {"admin", "soc_manager", "analyst", "viewer"},
    "readiness:view": {"admin", "soc_manager", "analyst", "viewer"},
    "customer_zero:execute": {"admin", "soc_manager", "analyst"},
    "customer_zero:read": {"admin", "soc_manager", "analyst", "viewer"},
    "incident:view": {"admin", "soc_manager", "analyst", "viewer"},
    "incident:update": {"admin", "soc_manager", "analyst"},
    "incident:approve": {"admin", "soc_manager"},
    "incident:close": {"admin", "soc_manager"},
    "incident:comment": {"admin", "soc_manager", "analyst"},
    "detection:view": {"admin", "soc_manager", "analyst", "viewer"},
    "detection:create": {"admin", "soc_manager", "analyst"},
    "detection:test": {"admin", "soc_manager", "analyst"},
    "detection:approve": {"admin", "soc_manager"},
    "detection:deploy": {"admin", "soc_manager"},
    "threat:view": {"admin", "soc_manager", "analyst", "viewer"},
    "threat:create": {"admin", "soc_manager", "analyst"},
    "threat:enrich": {"admin", "soc_manager", "analyst"},
    "threat:manage_feeds": {"admin", "soc_manager"},
    "exposure:view": {"admin", "soc_manager", "analyst", "viewer"},
    "exposure:create": {"admin", "soc_manager", "analyst"},
    "exposure:manage": {"admin", "soc_manager"},
    "exposure:scan": {"admin", "soc_manager", "analyst"},
    "analytics:view": {"admin", "soc_manager", "analyst", "viewer"},
    "analytics:search": {"admin", "soc_manager", "analyst"},
    "analytics:manage_retention": {"admin", "soc_manager"},
    "ueba:view": {"admin", "soc_manager", "analyst", "viewer"},
    "ueba:manage": {"admin", "soc_manager", "analyst"},
    "detection:discover": {"admin", "soc_manager", "analyst"},
    "detection:approve_discovery": {"admin", "soc_manager"},
    "agents:view": {"admin", "soc_manager", "analyst", "viewer"}, "agents:execute": {"admin", "soc_manager", "analyst"},
    "graph:view": {"admin", "soc_manager", "analyst", "viewer"}, "query:view": {"admin", "soc_manager", "analyst", "viewer"}, "query:create": {"admin", "soc_manager", "analyst"}, "memory:view": {"admin", "soc_manager", "analyst", "viewer"},
    "xdr:view": {"admin", "soc_manager", "analyst", "viewer"}, "xdr:investigate": {"admin", "soc_manager", "analyst"}, "xdr:respond": {"admin", "soc_manager", "analyst"}, "xdr:manage": {"admin", "soc_manager", "analyst"},
    "hunting:approve": {"admin", "soc_manager"},
    "security_twin:view": {"admin", "soc_manager", "analyst", "viewer"}, "security_twin:analyze": {"admin", "soc_manager", "analyst"}, "security_twin:simulate": {"admin", "soc_manager", "analyst"},
    "prevention:view": {"admin", "soc_manager", "analyst", "viewer"}, "prevention:analyze": {"admin", "soc_manager", "analyst"}, "prevention:approve": {"admin", "soc_manager"}, "prevention:execute": {"admin", "soc_manager", "analyst"}, "prevention:manage": {"admin", "soc_manager"},
    "validation:read": {"admin", "soc_manager", "analyst", "viewer"}, "validation:execute": {"admin", "soc_manager", "analyst"},
    "memory:view": {"admin", "soc_manager", "analyst", "viewer"}, "memory:search": {"admin", "soc_manager", "analyst"}, "memory:learn": {"admin", "soc_manager", "analyst"}, "memory:manage": {"admin", "soc_manager"},
    "soc:view": {"admin", "soc_manager", "analyst", "viewer"}, "soc:manage": {"admin", "soc_manager"}, "soc:assign": {"admin", "soc_manager", "analyst"}, "soc:approve": {"admin", "soc_manager"},
    "advisor:view": {"admin", "soc_manager", "analyst", "viewer"}, "advisor:report": {"admin", "soc_manager"}, "advisor:manage": {"admin", "soc_manager"},
    "marketplace:view": {"admin", "soc_manager", "analyst", "viewer"}, "marketplace:publish": {"admin", "soc_manager"}, "marketplace:install": {"admin", "soc_manager", "analyst"}, "marketplace:manage": {"admin", "soc_manager"},
    "lab:view": {"admin", "soc_manager", "analyst", "viewer"}, "lab:manage": {"admin", "soc_manager"}, "lab:execute": {"admin", "soc_manager", "analyst"},
    "operations:view": {"admin", "soc_manager"},
    "pilot:read": {"admin", "soc_manager", "analyst", "viewer"}, "pilot:manage": {"admin", "soc_manager"}, "compliance:manage": {"admin", "soc_manager"},
    "identity:view": {"admin", "soc_manager", "analyst", "viewer"}, "identity:manage": {"admin", "soc_manager"}, "identity:review": {"admin", "soc_manager", "analyst"},
    "data_security:view": {"admin", "soc_manager", "analyst", "viewer"}, "data_security:manage": {"admin", "soc_manager"},
    "decision:view": {"admin", "soc_manager", "analyst", "viewer"}, "decision:analyze": {"admin", "soc_manager", "analyst"},
    "copilot:view": {"admin", "soc_manager", "analyst", "viewer"}, "copilot:use": {"admin", "soc_manager", "analyst"},
    "platform:view": {"admin", "soc_manager", "analyst", "viewer"}, "platform:manage": {"admin", "soc_manager"},
}

def current_role() -> str | None:
    user = current_app.container.get("auth_service").get_by_id(session.get("user_id"))
    return ROLE_ALIASES.get(str(user.role).upper()) if user else None

def permission_required(permission: str):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            role = current_role()
            if not role:
                return jsonify({"error": "authentication_required"}), 401
            if role not in PERMISSIONS.get(permission, set()):
                return jsonify({"error": "forbidden"}), 403
            return view(*args, **kwargs)
        return wrapped
    return decorator
