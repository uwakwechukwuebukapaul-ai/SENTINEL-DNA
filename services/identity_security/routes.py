from flask import Blueprint,current_app,jsonify,request,render_template,session
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization,tenant_required
identity_api=Blueprint("identity_security_api",__name__)
def org(): return current_organization().organization_id
def svc(): return current_app.container.get("identity_security")
@identity_api.post("/api/identity-security/identities")
@permission_required("identity:manage")
@tenant_required
def create():
 x=svc().add(org(),request.get_json(silent=True) or {}); current_app.container.get("audit_service").record("IDENTITY_CREATED",user_id=session.get("user_id"),details={}); return jsonify(x),201
@identity_api.get("/api/identity-security/identities")
@permission_required("identity:view")
@tenant_required
def identities(): return jsonify({"identities":svc().scoped(org())})
@identity_api.get("/api/identity-security/risk")
@permission_required("identity:view")
@tenant_required
def risk(): return jsonify({"risk":[svc().risk(x) for x in svc().scoped(org())]})
@identity_api.post("/api/identity-security/reviews")
@permission_required("identity:review")
@tenant_required
def review(): return jsonify(svc().review(org(),(request.get_json(silent=True) or {}).get("identity_id",""))),201
@identity_api.get("/workspace/identity-security")
@permission_required("identity:view")
@tenant_required
def workspace(): return render_template("identity_security.html")
