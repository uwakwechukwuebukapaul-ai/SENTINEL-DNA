from flask import Blueprint, current_app, jsonify
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
pilot_management_api = Blueprint("pilot_management_api", __name__, url_prefix="/api/pilots")
@pilot_management_api.get("")
@permission_required("pilot:manage")
@tenant_required
def listing(): return jsonify({"pilots": current_app.container.get("pilot_management_service").list(current_organization().organization_id)})
