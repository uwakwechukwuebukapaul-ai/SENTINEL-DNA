from flask import Blueprint,current_app,jsonify,request,render_template,session
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization,tenant_required
data_security_api=Blueprint("data_security_api",__name__)
def org(): return current_organization().organization_id
def svc(): return current_app.container.get("data_security")
@data_security_api.post("/api/data-security/assets")
@permission_required("data_security:manage")
@tenant_required
def asset():
 x=svc().add_asset(org(),request.get_json(silent=True) or {}); current_app.container.get("audit_service").record("DATA_ASSET_CREATED",user_id=session.get("user_id"),details={}); return jsonify(x),201
@data_security_api.get("/api/data-security/assets")
@permission_required("data_security:view")
@tenant_required
def assets(): return jsonify({"assets":svc().scoped(org())})
@data_security_api.get("/api/data-security/risk")
@permission_required("data_security:view")
@tenant_required
def risk(): return jsonify({"risk":[svc().risk(x) for x in svc().scoped(org())]})
@data_security_api.post("/api/data-security/access")
@permission_required("data_security:manage")
@tenant_required
def access(): return jsonify(svc().add_access(org(),request.get_json(silent=True) or {})),201
@data_security_api.get("/workspace/data-security")
@permission_required("data_security:view")
@tenant_required
def workspace(): return render_template("data_security.html")
