from flask import Blueprint, current_app, jsonify, request, session
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
governance_api = Blueprint("governance_api", __name__, url_prefix="/api/governance")
def _csrf(): return session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token")
@governance_api.get("/decisions")
@permission_required("governance:read")
@tenant_required
def decisions():
    org = current_organization().organization_id; return jsonify({"decisions": [x for x in current_app.container.get("governance_service").records if x["organization_id"] == org]})
@governance_api.post("/approvals")
@permission_required("governance:approve")
@tenant_required
def approval():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}; item = current_app.container.get("governance_service").request_approval(current_organization().organization_id, data.get("action", ""), data.get("decision_id", "")); return jsonify(item), 201
