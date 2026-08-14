from flask import Blueprint, current_app, jsonify, request, session
from services.auth.permissions import permission_required
from .context import tenant_required, current_organization
tenancy_api = Blueprint("tenancy_api", __name__, url_prefix="/api/organizations")
def _csrf(): return session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token")
@tenancy_api.post("")
@permission_required("organizations:create")
def create():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    data = request.get_json(silent=True) or {}
    try: org = current_app.container.get("tenancy_service").create(data.get("name", ""), data.get("subscription_tier", "trial"), session.get("user_id"))
    except ValueError: return jsonify({"error": "invalid_organization"}), 400
    session["organization_id"] = org.organization_id; current_app.container.get("audit_service").record("ORGANIZATION_CREATED", user_id=session.get("user_id"), details={"organization_id": org.organization_id}); return jsonify(org.public()), 201
@tenancy_api.get("/current")
@tenant_required
def current(): return jsonify(current_organization().public())
@tenancy_api.get("/users")
@tenant_required
def users(): return jsonify({"users": current_app.container.get("tenancy_service").users(current_organization().organization_id)})
