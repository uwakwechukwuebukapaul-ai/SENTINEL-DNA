from flask import Blueprint, current_app, jsonify, request, session
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
from .autonomous import AutonomousInvestigationEngine
from services.ai import ReasoningFabric
reasoning_api = Blueprint("reasoning_api", __name__, url_prefix="/api/intelligence/reasoning")
_engine = AutonomousInvestigationEngine()
_fabric = ReasoningFabric()
def _csrf(): return session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token")
@reasoning_api.post("/investigate")
@permission_required("reasoning:execute")
@tenant_required
def investigate():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}; org = current_organization().organization_id
    result = _engine.investigate(org, data.get("alert", {}), data.get("evidence", []), data.get("iocs", []), data.get("previous_incidents"))
    current_app.container.get("audit_service").record("AUTONOMOUS_INVESTIGATION_COMPLETED", user_id=session.get("user_id"), details={"organization_id": org, "decision": result["decision"]["decision"]}); return jsonify(result), 200
@reasoning_api.get("/memory")
@permission_required("reasoning:read")
@tenant_required
def memory():
    return jsonify({"records": _engine.memory.search(current_organization().organization_id)})
@reasoning_api.post("/ai")
@permission_required("reasoning:execute")
@tenant_required
def ai_reasoning():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}
    try: result = _fabric.investigate(current_organization().organization_id, data.get("question", ""), data.get("evidence", []))
    except ValueError as exc: return jsonify({"error": str(exc)}), 400
    current_app.container.get("audit_service").record("AI_REASONING_COMPLETED", user_id=session.get("user_id"), details={"organization_id": current_organization().organization_id, "confidence": result["confidence"]}); return jsonify(result)
