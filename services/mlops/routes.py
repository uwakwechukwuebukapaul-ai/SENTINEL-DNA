from flask import Blueprint, current_app, jsonify
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
mlops_api = Blueprint("mlops_api", __name__, url_prefix="/api/mlops")
@mlops_api.get("/metrics")
@permission_required("mlops:read")
@tenant_required
def metrics():
    return jsonify(current_app.container.get("mlops_service").metrics(current_organization().organization_id))
