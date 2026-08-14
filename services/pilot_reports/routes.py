from flask import Blueprint, current_app, jsonify
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
pilot_reports_api = Blueprint("pilot_reports_api", __name__, url_prefix="/api/pilot")
@pilot_reports_api.get("/report")
@permission_required("pilot:read")
@tenant_required
def report():
    org = current_organization().organization_id; analytics = current_app.container.get("pilot_analytics_service").report(org); return jsonify(current_app.container.get("pilot_report_service").generate(org, analytics))
