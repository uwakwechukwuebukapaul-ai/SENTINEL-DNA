from flask import Blueprint,current_app,jsonify,request,render_template,session
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization,tenant_required
lab_api=Blueprint("lab_api",__name__)
def org(): return current_organization().organization_id
def audit(e,d): current_app.container.get("audit_service").record(e,user_id=session.get("user_id"),details=d)
@lab_api.post("/api/lab/environment/create")
@permission_required("lab:manage")
@tenant_required
def create():
 x=current_app.container.get("lab_manager").create(org()); audit("LAB_ENVIRONMENT_CREATED",{"id":x["id"]}); return jsonify(x),201
@lab_api.post("/api/lab/scenario/run")
@permission_required("lab:execute")
@tenant_required
def run():
 x=current_app.container.get("simulation_runner").run(org(),(request.get_json(silent=True) or {}).get("scenario","credential_attack")); current_app.container.get("lab_manager").runs.append(x); audit("LAB_SIMULATION_COMPLETED",{"scenario":x["scenario"]}); return jsonify(x),201
@lab_api.get("/api/lab/status")
@permission_required("lab:view")
@tenant_required
def status(): return jsonify(current_app.container.get("lab_manager").status(org()))
@lab_api.get("/api/lab/report")
@permission_required("lab:view")
@tenant_required
def report(): return jsonify({"report":"Customer Zero laboratory validation report","status":current_app.container.get("lab_manager").status(org())})
@lab_api.get("/workspace/lab")
@permission_required("lab:view")
@tenant_required
def workspace(): return render_template("lab.html")
