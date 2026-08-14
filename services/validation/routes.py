from flask import Blueprint, current_app, jsonify, request, session
from services.auth.permissions import permission_required
from .engine import ValidationEngine
validation_api = Blueprint("validation_api", __name__, url_prefix="/api/validation")
_engine = ValidationEngine()
def _csrf(): return session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token")
@validation_api.post("/run")
@permission_required("validation:execute")
def run():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    try: result = _engine.run(request.get_json(silent=True) or {})
    except (TypeError, ValueError): return jsonify({"error": "invalid_validation_input"}), 400
    current_app.container.get("audit_service").record("SECURITY_VALIDATION_RUN", user_id=session.get("user_id"), details={"result_id": result.id, "campaign_id": result.campaign_id})
    return jsonify(result.public()), 201
@validation_api.get("/results")
@permission_required("validation:read")
def results(): return jsonify({"results": [item.public() for item in _engine.results.values()]})
@validation_api.get("/report/<result_id>")
@permission_required("validation:read")
def report(result_id):
    result = _engine.results.get(result_id)
    return jsonify(result.public() if result else {"error": "validation_result_not_found"}), 200 if result else 404
