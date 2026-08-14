from flask import Blueprint, current_app, jsonify
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required
monitoring_api = Blueprint("monitoring_api", __name__, url_prefix="/api/monitoring")
@monitoring_api.get("/health")
@permission_required("monitoring:read")
@tenant_required
def health(): return jsonify(current_app.container.get("monitoring_service").snapshot())
