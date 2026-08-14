from flask import Blueprint, current_app, jsonify
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
support_api = Blueprint("support_api", __name__, url_prefix="/api/support")
@support_api.get("/tickets")
@permission_required("support:read")
@tenant_required
def tickets(): return jsonify({"tickets": current_app.container.get("support_service").list(current_organization().organization_id)})
