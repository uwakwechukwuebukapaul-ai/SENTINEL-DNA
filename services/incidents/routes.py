from flask import Blueprint, current_app, jsonify, request, session
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
from services.incidents.sla.calculator import SLACalculator
incidents_api = Blueprint("incidents_api", __name__, url_prefix="/api/incidents")
def _csrf(): return session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token")
def _org(): return current_organization().organization_id
@incidents_api.get("")
@permission_required("incidents:read")
@tenant_required
def listing(): return jsonify({"incidents": current_app.container.get("incident_service").list(_org())})
@incidents_api.post("")
@permission_required("incidents:manage")
@tenant_required
def create():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}; item = current_app.container.get("incident_service").create(_org(), data.get("title", "Untitled incident"), data.get("severity", "medium"), session.get("user_id"), data.get("sla_minutes", 60)); current_app.container.get("workflow_service").create(item["id"], _org()); return jsonify(item), 201
@incidents_api.post("/<incident_id>/transition")
@permission_required("incidents:manage")
@tenant_required
def transition(incident_id):
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}
    try: workflow_item = current_app.container.get("workflow_service").transition(incident_id, _org(), str(data.get("state", "")).upper(), session.get("user_id"), data.get("reason", ""))
    except LookupError: return jsonify({"error": "incident_not_found"}), 404
    except ValueError: return jsonify({"error": "invalid_state_transition"}), 400
    try: item = current_app.container.get("incident_service").transition(incident_id, _org(), data.get("state", ""), data.get("resolution"))
    except LookupError: return jsonify({"error": "incident_not_found"}), 404
    except ValueError: return jsonify({"error": "invalid_incident_state"}), 400
    current_app.container.get("audit_service").record("INCIDENT_STATUS_CHANGED", user_id=session.get("user_id"), details={"incident_id": incident_id, "state": data.get("state")}); return jsonify({**item, "workflow": workflow_item.public()})
@incidents_api.get("/<incident_id>/workflow")
@permission_required("incident:view")
@tenant_required
def workflow(incident_id):
    try: item = current_app.container.get("workflow_service").get(incident_id, _org())
    except LookupError: return jsonify({"error": "incident_not_found"}), 404
    return jsonify(item.public())
@incidents_api.post("/<incident_id>/comments")
@permission_required("incident:comment")
@tenant_required
def comment(incident_id):
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}; item = current_app.container.get("collaboration_service").comment(incident_id, _org(), session.get("user_id"), data.get("message", ""), data.get("kind", "comment")); current_app.container.get("audit_service").record("INCIDENT_COMMENT_CREATED", user_id=session.get("user_id"), details={"incident_id": incident_id}); return jsonify(item), 201
@incidents_api.get("/<incident_id>/comments")
@permission_required("incident:view")
@tenant_required
def comments(incident_id): return jsonify({"comments": current_app.container.get("collaboration_service").list_comments(incident_id, _org())})
@incidents_api.get("/<incident_id>/sla")
@permission_required("incident:view")
@tenant_required
def sla(incident_id):
    try: item = current_app.container.get("workflow_service").get(incident_id, _org())
    except LookupError: return jsonify({"error": "incident_not_found"}), 404
    return jsonify(current_app.container.get("sla_calculator").calculate(item.timestamps))
@incidents_api.post("/<incident_id>/actions")
@permission_required("incident:update")
@tenant_required
def action(incident_id):
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}; item = current_app.container.get("collaboration_service").action(incident_id, _org(), session.get("user_id"), data.get("action", ""), data.get("metadata")); current_app.container.get("audit_service").record("INCIDENT_ACTION_EXECUTED", user_id=session.get("user_id"), details={"incident_id": incident_id, "action": data.get("action")}); return jsonify(item), 201
