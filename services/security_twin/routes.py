from flask import Blueprint,current_app,jsonify,request,session,render_template
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization,tenant_required
twin_api=Blueprint("security_twin_api",__name__)
def org(): return current_organization().organization_id
def service(): return current_app.container.get("security_twin_service")
@twin_api.post("/api/security-twin/assets")
@permission_required("security_twin:analyze")
@tenant_required
def add():
 x=service().add_asset(org(),request.get_json(silent=True) or {}); return jsonify(x.public()),201
@twin_api.get("/api/security-twin/assets")
@permission_required("security_twin:view")
@tenant_required
def assets():
 r=service().repository; return jsonify({"assets":[x.public() for x in r.scoped(r.assets,org())]})
@twin_api.get("/api/security-twin/context/<asset_id>")
@permission_required("security_twin:view")
@tenant_required
def context(asset_id):
 x=service().context(org(),asset_id); return jsonify(x) if x else (jsonify({"error":"asset_not_found"}),404)
@twin_api.get("/api/security-twin/attack-path/<asset_id>")
@permission_required("security_twin:view")
@tenant_required
def paths(asset_id): return context(asset_id)
@twin_api.get("/api/security-twin/blast-radius/<asset_id>")
@permission_required("security_twin:view")
@tenant_required
def blast(asset_id):
 x=service().context(org(),asset_id); return jsonify(x.get("blast_radius",{})) if x else (jsonify({"error":"asset_not_found"}),404)
@twin_api.post("/api/security-twin/simulate")
@permission_required("security_twin:simulate")
@tenant_required
def simulate():
 x=service().context(org(),(request.get_json(silent=True) or {}).get("asset_id","")); return jsonify(x) if x else (jsonify({"error":"asset_not_found"}),404)
@twin_api.get("/workspace/security-twin")
@permission_required("security_twin:view")
@tenant_required
def workspace(): return render_template("security_twin.html")
