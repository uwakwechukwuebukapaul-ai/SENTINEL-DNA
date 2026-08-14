from flask import Blueprint, current_app, jsonify, session
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required
from .readiness_service import ReadinessService
readiness_api = Blueprint("readiness_api", __name__, url_prefix="/api/readiness")
@readiness_api.get("")
@permission_required("readiness:view")
@tenant_required
def readiness():
    service = current_app.container.get("readiness_service") if hasattr(current_app, "container") else ReadinessService()
    report = service.execute(); current_app.container.get("audit_service").record("READINESS_VIEW", user_id=session.get("user_id"), details={"overall_score": report.overall_score}); return jsonify(report.public())
