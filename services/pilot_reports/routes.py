from flask import Blueprint, current_app, jsonify, request, session
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
pilot_reports_api = Blueprint("pilot_reports_api", __name__, url_prefix="/api/pilot")
@pilot_reports_api.get("/report")
@permission_required("pilot:read")
@tenant_required
def report():
    org = current_organization().organization_id; analytics = current_app.container.get("pilot_analytics_service").report(org); return jsonify(current_app.container.get("pilot_report_service").generate(org, analytics))

@pilot_reports_api.get("/scenarios")
@permission_required("pilot:read")
@tenant_required
def scenarios():
    return jsonify({"scenarios": current_app.container.get("pilot_simulation").scenarios()})

@pilot_reports_api.post("/runs")
@permission_required("investigations:run")
@tenant_required
def create_pilot_run():
    payload = request.get_json(silent=True) or {}
    if set(payload) - {"scenario_id", "case_id"} or not payload.get("scenario_id") or not payload.get("case_id"):
        return jsonify({"error": "scenario_id_and_case_id_required"}), 400
    try: result = current_app.container.get("pilot_simulation").create_run(current_organization().organization_id, payload["scenario_id"], payload["case_id"])
    except ValueError as exc: return jsonify({"error": str(exc)}), 400
    return jsonify(result), 201

@pilot_reports_api.get("/runs/<run_id>")
@permission_required("pilot:read")
@tenant_required
def get_pilot_run(run_id):
    result = current_app.container.get("pilot_simulation").get_run(current_organization().organization_id, run_id)
    return jsonify(result) if result else (jsonify({"error": "pilot_run_not_found"}), 404)

@pilot_reports_api.post("/runs/<run_id>/observations")
@permission_required("investigations:run")
@tenant_required
def record_pilot_observation(run_id):
    try: result = current_app.container.get("pilot_simulation").record_observation(current_organization().organization_id, run_id, request.get_json(silent=True) or {})
    except LookupError: return jsonify({"error": "pilot_run_not_found"}), 404
    except ValueError as exc: return jsonify({"error": str(exc)}), 400
    return jsonify(result), 201

@pilot_reports_api.post("/investigations")
@permission_required("investigations:run")
@tenant_required
def run_pilot_investigation():
    payload = request.get_json(silent=True) or {}
    required = {"case_id", "scenario_id"}
    if not required.issubset(payload): return jsonify({"error": "case_id_and_scenario_id_required"}), 400
    if set(payload) - {"run_id", "case_id", "scenario_id", "alert", "artifacts"}: return jsonify({"error": "invalid_pilot_fields"}), 400
    org = current_organization().organization_id
    actor_id = session.get("actor_id") or session.get("user_id")
    try:
        result = current_app.container.get("pilot_simulation").run_investigation(tenant_id=org, actor_id=str(actor_id or ""), case_id=str(payload["case_id"]), scenario_id=str(payload["scenario_id"]), coordinator=current_app.container.get("investigation_coordinator"), alert=payload.get("alert"), artifacts=payload.get("artifacts"), run_id=payload.get("run_id"))
    except LookupError as exc: return jsonify({"error": str(exc)}), 404
    except ValueError as exc: return jsonify({"error": str(exc)}), 400
    except PermissionError as exc: return jsonify({"error": str(exc)}), 403
    return jsonify(result), 202

@pilot_reports_api.get("/investigations/<case_id>/summary")
@permission_required("pilot:read")
@tenant_required
def investigation_summary(case_id):
    org = current_organization().organization_id; context = type("PilotContext", (), {"tenant_id": org})()
    coordinator = current_app.container.get("investigation_coordinator")
    try:
        view = coordinator.get_investigation_view(case_id, context); metrics = coordinator.get_investigation_metrics(case_id, context)
    except PermissionError: return jsonify({"error": "investigation_not_found"}), 404
    if view is None: return jsonify({"error": "investigation_not_found"}), 404
    return jsonify(current_app.container.get("pilot_report_service").investigation_summary(org, view, metrics))

@pilot_reports_api.get("/runs/<run_id>/validation")
@permission_required("pilot:read")
@tenant_required
def pilot_validation(run_id):
    org = current_organization().organization_id
    try: return jsonify(current_app.container.get("pilot_simulation").validation_report(org, run_id, request.args.getlist("observation")))
    except LookupError: return jsonify({"error": "pilot_run_not_found"}), 404

@pilot_reports_api.get("/outcome")
@permission_required("pilot:read")
@tenant_required
def pilot_outcome():
    org = current_organization().organization_id; simulation = current_app.container.get("pilot_simulation")
    runs = [item for item in simulation.runs if item.get("organization_id") == org]
    validations = [simulation.validation_report(org, item["run_id"]) for item in runs if item.get("status") == "completed"]
    return jsonify(current_app.container.get("pilot_report_service").pilot_outcome(org, runs, validations, simulation.customer_pilot(org)))

@pilot_reports_api.get("/customer-success")
@permission_required("pilot:read")
@tenant_required
def customer_success_overview():
    org = current_organization().organization_id; simulation = current_app.container.get("pilot_simulation")
    runs = [item for item in simulation.runs if item.get("organization_id") == org]
    validations = [simulation.validation_report(org, item["run_id"]) for item in runs if item.get("status") == "completed" and item.get("run_id")]
    return jsonify(current_app.container.get("pilot_report_service").customer_success_overview(org, simulation.customer_pilot(org), runs, validations))

@pilot_reports_api.post("/customer-success")
@permission_required("pilot:manage")
@tenant_required
def configure_customer_success():
    payload = request.get_json(silent=True) or {}
    if set(payload) - {"objectives", "status", "checklist"}: return jsonify({"error": "invalid_customer_success_fields"}), 400
    simulation = current_app.container.get("pilot_simulation"); org = current_organization().organization_id
    try:
        result = simulation.configure_customer_pilot(org, payload["objectives"]) if "objectives" in payload else simulation.customer_pilot(org)
        if "status" in payload: result = simulation.advance_customer_pilot(org, payload["status"], payload.get("checklist"))
    except ValueError as exc: return jsonify({"error": str(exc)}), 400
    return jsonify(result), 200

@pilot_reports_api.post("/customer-success/feedback")
@permission_required("investigations:run")
@tenant_required
def customer_success_feedback():
    try: result = current_app.container.get("pilot_simulation").record_customer_feedback(current_organization().organization_id, request.get_json(silent=True) or {})
    except ValueError as exc: return jsonify({"error": str(exc)}), 400
    return jsonify(result), 201
