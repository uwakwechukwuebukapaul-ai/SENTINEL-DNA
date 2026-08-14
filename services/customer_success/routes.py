from flask import Blueprint, current_app, jsonify
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
customer_success_api = Blueprint("customer_success_api", __name__, url_prefix="/api/customer-success")
@customer_success_api.get("/report")
@permission_required("customer_success:read")
@tenant_required
def report(): return jsonify(current_app.container.get("customer_success_service").report(current_organization().organization_id))
