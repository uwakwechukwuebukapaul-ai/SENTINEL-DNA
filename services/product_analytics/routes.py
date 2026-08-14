from flask import Blueprint, current_app, jsonify
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
product_analytics_api = Blueprint("product_analytics_api", __name__, url_prefix="/api/product-analytics")
@product_analytics_api.get("/summary")
@permission_required("product_analytics:read")
@tenant_required
def summary(): return jsonify(current_app.container.get("product_analytics_service").summary(current_organization().organization_id))
