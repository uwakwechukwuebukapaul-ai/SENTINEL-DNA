from flask import Blueprint, current_app, jsonify, request, session
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
api_management_api = Blueprint("api_management_api", __name__, url_prefix="/api/management")
def _csrf(): return session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token")
@api_management_api.get("/keys")
@permission_required("api:read")
@tenant_required
def keys(): return jsonify({"keys": current_app.container.get("api_management_service").list(current_organization().organization_id)})
@api_management_api.post("/keys")
@permission_required("api:manage")
@tenant_required
def create_key():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}; return jsonify(current_app.container.get("api_management_service").create_key(current_organization().organization_id, data.get("name", "integration"))), 201
