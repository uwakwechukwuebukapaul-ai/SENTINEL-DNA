from flask import Blueprint,current_app,jsonify,request,render_template
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization,tenant_required
demo_api=Blueprint("customer_zero_demo_api",__name__)
def org(): return current_organization().organization_id
@demo_api.post("/api/customer-zero/demo/run")
@permission_required("customer_zero:execute")
@tenant_required
def run(): return jsonify(current_app.container.get("customer_zero_demo_pipeline").run(org(),(request.get_json(silent=True) or {}).get("scenario","credential_attack"))),201
@demo_api.get("/api/customer-zero/demo/status")
@permission_required("customer_zero:read")
@tenant_required
def status(): return jsonify({"runs":current_app.container.get("customer_zero_demo_pipeline").scoped(org()),"synthetic_only":True})
@demo_api.get("/workspace/customer-zero/demo")
@permission_required("customer_zero:read")
@tenant_required
def workspace(): return render_template("customer_zero_demo.html")
