from flask import Blueprint,current_app,jsonify,request,render_template
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization,tenant_required
prevention_api=Blueprint("prevention_api",__name__)
def org(): return current_organization().organization_id
def repo(): return current_app.container.get("prevention_repository")
@prevention_api.post("/api/prevention/analyze")
@permission_required("prevention:analyze")
@tenant_required
def analyze():
 x=current_app.container.get("prevention_engine").analyze(org(),request.get_json(silent=True) or {}); return jsonify(x.public()),201
@prevention_api.get("/api/prevention/recommendations")
@permission_required("prevention:view")
@tenant_required
def recommendations():
 r=repo(); return jsonify({"recommendations":[x.public() for x in r.scoped(r.recommendations,org())]})
@prevention_api.post("/api/prevention/approve")
@permission_required("prevention:approve")
@tenant_required
def approve():
 p=request.get_json(silent=True) or {}; r=repo(); x=next((x for x in r.scoped(r.recommendations,org()) if x.id==p.get("id")),None)
 if not x:return jsonify({"error":"recommendation_not_found"}),404
 return jsonify(current_app.container.get("approval_manager").approve(x).public())
@prevention_api.post("/api/prevention/execute")
@permission_required("prevention:execute")
@tenant_required
def execute():
 p=request.get_json(silent=True) or {}; r=repo(); a=next((x for x in r.scoped(r.actions,org()) if x.id==p.get("action_id")),None)
 if not a:return jsonify({"error":"action_not_found"}),404
 return jsonify(current_app.container.get("control_executor").execute(a))
@prevention_api.get("/api/prevention/history")
@permission_required("prevention:view")
@tenant_required
def history():
 r=repo(); return jsonify({"outcomes":[x.public() for x in r.scoped(r.outcomes,org())]})
@prevention_api.get("/api/prevention/metrics")
@permission_required("prevention:view")
@tenant_required
def metrics():
 r=repo().scoped(repo().outcomes,org()); return jsonify({"actions":len(r),"success_rate":sum(x.result=="SUCCESS" for x in r)/len(r) if r else 0})
@prevention_api.get("/workspace/prevention")
@permission_required("prevention:view")
@tenant_required
def workspace(): return render_template("prevention.html")
