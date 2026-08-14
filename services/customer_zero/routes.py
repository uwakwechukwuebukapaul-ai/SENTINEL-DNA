from flask import Blueprint, current_app, jsonify, request, session
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
from lab.customer_zero.runner import CustomerZeroRunner
from .reporting import CustomerZeroReportService
from .replay import ReplayEngine
customer_zero_api = Blueprint("customer_zero_api", __name__, url_prefix="/api/customer-zero")
_runner = CustomerZeroRunner()
_reports = CustomerZeroReportService(); _replay = ReplayEngine()
def _csrf(): return session.get("csrf_token") and request.headers.get("X-CSRF-Token") == session.get("csrf_token")
@customer_zero_api.post("/run")
@permission_required("customer_zero:execute")
@tenant_required
def run():
    if not _csrf(): return jsonify({"error": "csrf_validation_failed"}), 403
    scenario = (request.get_json(silent=True) or {}).get("scenario", "credential_attack"); current_app.container.get("audit_service").record("CUSTOMER_ZERO_STARTED", user_id=session.get("user_id"), details={"scenario": scenario, "organization_id": current_organization().organization_id})
    try: result = _runner.run(scenario)
    except ValueError as exc: current_app.container.get("audit_service").record("CUSTOMER_ZERO_FAILED", user_id=session.get("user_id"), details={"error": str(exc)}); return jsonify({"error": str(exc)}), 400
    current_app.container.get("audit_service").record("CUSTOMER_ZERO_COMPLETED", user_id=session.get("user_id"), details={"scenario": scenario}); return jsonify(result), 202
@customer_zero_api.get("/status")
@permission_required("customer_zero:execute")
@tenant_required
def status(): return jsonify(_runner.status)
@customer_zero_api.get("/report")
@permission_required("customer_zero:read")
@tenant_required
def report():
    result = _runner.status; generated = _reports.generate(current_organization().organization_id, result); current_app.container.get("audit_service").record("CUSTOMER_ZERO_REPORT_VIEW", user_id=session.get("user_id"), details={"report_id": generated.report_id}); return jsonify({"report": generated.public(), "executive": _reports.executive(generated), "analyst": _reports.analyst(generated, [x.public() for x in _replay.generate(result)])})
@customer_zero_api.get("/replay")
@permission_required("customer_zero:read")
@tenant_required
def replay():
    current_app.container.get("audit_service").record("CUSTOMER_ZERO_REPLAY_VIEW", user_id=session.get("user_id"), details={}); return jsonify({"timeline": [x.public() for x in _replay.generate(_runner.status)]})
