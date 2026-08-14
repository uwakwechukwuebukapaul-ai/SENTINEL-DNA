from flask import Blueprint,current_app,jsonify,request,render_template,session
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization,tenant_required
pilot_api=Blueprint("pilot_simulation_api",__name__)
def org(): return current_organization().organization_id
def audit(e,d): current_app.container.get("audit_service").record(e,user_id=session.get("user_id"),details=d)
@pilot_api.post("/api/pilot/onboard")
@permission_required("pilot:manage")
@tenant_required
def onboard():
 x=current_app.container.get("pilot_simulation").onboard(org(),(request.get_json(silent=True) or {}).get("name","Enterprise Pilot")); audit("PILOT_TENANT_ONBOARDED",{}); return jsonify(x),201
@pilot_api.post("/api/pilot/scenario/run")
@permission_required("pilot:manage")
@tenant_required
def run():
 x=current_app.container.get("pilot_simulation").run(org(),(request.get_json(silent=True) or {}).get("scenario","credential_compromise")); audit("PILOT_SCENARIO_COMPLETED",{"scenario":x["scenario"]}); return jsonify(x),201
@pilot_api.get("/api/pilot/dashboard")
@permission_required("pilot:read")
@tenant_required
def dashboard(): return jsonify(current_app.container.get("pilot_simulation").view(org(),"customer"))
@pilot_api.get("/workspace/pilot-demo")
@permission_required("pilot:read")
@tenant_required
def workspace(): return render_template("pilot_demo.html")
