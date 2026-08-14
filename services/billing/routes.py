from flask import Blueprint, current_app, jsonify
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
billing_api = Blueprint("billing_api", __name__, url_prefix="/api/billing")
@billing_api.get("/status")
@permission_required("billing:read")
@tenant_required
def status(): return jsonify(current_app.container.get("billing_service").status(current_organization().organization_id))
