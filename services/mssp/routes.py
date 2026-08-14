from flask import Blueprint, jsonify
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
mssp_api = Blueprint("mssp_api", __name__, url_prefix="/api/mssp")
@mssp_api.get("/context")
@permission_required("mssp:read")
@tenant_required
def context():
    return jsonify({"organization_id": current_organization().organization_id})
