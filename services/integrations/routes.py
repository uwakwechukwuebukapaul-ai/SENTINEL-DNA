from flask import Blueprint, current_app, jsonify, request, session
from services.auth.permissions import permission_required
from .registry import IntegrationRegistry
integrations_api = Blueprint("integrations_api", __name__, url_prefix="/api/integrations")
_registry = IntegrationRegistry()
def _csrf():
    return session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token")
def _audit(event, details): current_app.container.get("audit_service").record(event, user_id=session.get("user_id"), details=details)
@integrations_api.post("")
@permission_required("integrations:manage")
def create():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}
    try: item = _registry.register(data.get("name", ""), data.get("provider", ""), data.get("kind", ""), data.get("config"), data.get("credentials"))
    except (TypeError, ValueError): return jsonify({"error": "invalid_integration"}), 400
    _audit("INTEGRATION_CREATED", {"integration_id": item.id, "provider": item.provider}); return jsonify(item.public()), 201
@integrations_api.get("")
@permission_required("integrations:read")
def listing(): return jsonify({"integrations": [item.public() for item in _registry.all()]})
@integrations_api.post("/test")
@permission_required("integrations:test")
def test():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    item = _registry.get((request.get_json(silent=True) or {}).get("integration_id", ""))
    if not item: return jsonify({"error": "integration_not_found"}), 404
    result = _registry.test(item); _audit("INTEGRATION_HEALTH_CHECKED", {"integration_id": item.id, "status": item.status}); return jsonify({"integration": item.public(), "health": result})
