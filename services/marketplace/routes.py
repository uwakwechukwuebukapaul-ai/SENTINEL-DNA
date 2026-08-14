from flask import Blueprint, current_app, jsonify, request, session, render_template
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required, current_organization
marketplace_api = Blueprint("marketplace_api", __name__, url_prefix="/api/marketplace")
@marketplace_api.get("")
@permission_required("marketplace:read")
@tenant_required
def listing():
    return jsonify({"packages": current_app.container.get("marketplace_service").list(current_organization().organization_id)})
@marketplace_api.post("/packages")
@permission_required("marketplace:publish")
@tenant_required
def publish():
 x=current_app.container.get("marketplace_publisher").publish(current_organization().organization_id,request.get_json(silent=True) or {}); return jsonify(x.public()),201
@marketplace_api.get("/packages")
@permission_required("marketplace:view")
@tenant_required
def packages():
 r=current_app.container.get("marketplace_repository"); return jsonify({"packages":[x.public() for x in r.scoped(r.packages,current_organization().organization_id)]})
@marketplace_api.post("/install")
@permission_required("marketplace:install")
@tenant_required
def install():
 p=request.get_json(silent=True) or {}; x=current_app.container.get("marketplace_installer").install(current_organization().organization_id,p.get("package_id",""),session.get("user_id","")); return jsonify(x.public()) if x else (jsonify({"error":"package_not_found"}),404)
@marketplace_api.get("/installed")
@permission_required("marketplace:view")
@tenant_required
def installed():
 r=current_app.container.get("marketplace_repository"); return jsonify({"installations":[x.public() for x in r.scoped(r.installations,current_organization().organization_id)]})
@marketplace_api.post("/rating")
@permission_required("marketplace:view")
@tenant_required
def rating():
 p=request.get_json(silent=True) or {}; return jsonify(current_app.container.get("marketplace_rating_engine").rate(current_app.container.get("marketplace_repository"),current_organization().organization_id,p.get("package_id",""),p.get("rating",1),p.get("feedback",""))),201
@marketplace_api.get("/workspace")
@permission_required("marketplace:view")
@tenant_required
def workspace(): return render_template("marketplace.html")
