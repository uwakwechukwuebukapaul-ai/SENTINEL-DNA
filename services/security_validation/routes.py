from flask import Blueprint,current_app,jsonify,request,render_template
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization,tenant_required
validation_ai_api=Blueprint("security_validation_api",__name__)
def org(): return current_organization().organization_id
def repo(): return current_app.container.get("security_validation_repository")
@validation_ai_api.post("/api/security-validation/scenarios")
@validation_ai_api.post("/api/validation/scenarios")
@permission_required("validation:execute")
@tenant_required
def create():
 p=request.get_json(silent=True) or {}; x=current_app.container.get("security_validation_service").scenario(org(),p); return jsonify(x.public()),201
@validation_ai_api.get("/api/validation/scenarios")
@permission_required("validation:view")
@tenant_required
def scenarios():
 r=repo(); return jsonify({"scenarios":[x.public() for x in r.scoped(r.scenarios,org())]})
@validation_ai_api.post("/api/security-validation/run")
@validation_ai_api.post("/api/validation/run")
@permission_required("validation:execute")
@tenant_required
def run():
 p=request.get_json(silent=True) or {}; x=current_app.container.get("security_validation_service").run(org(),p.get("scenario_id")); return jsonify(x),201
@validation_ai_api.get("/api/security-validation/results")
@validation_ai_api.get("/api/validation/results")
@permission_required("validation:read")
@tenant_required
def results():
 r=repo(); return jsonify({"results":[x.public() for x in r.scoped(r.results,org())]})
@validation_ai_api.get("/api/validation/report/<result_id>")
@permission_required("validation:view")
@tenant_required
def report(result_id):
 r=repo(); x=next((x for x in r.scoped(r.results,org()) if x.id==result_id),None)
 if not x:return jsonify({"error":"result_not_found"}),404
 return jsonify({"report":x.public(),"executive_summary":"Security validation posture measured through synthetic attack simulation.","recommendations":x.recommendations})
@validation_ai_api.get("/api/validation/security-score")
@permission_required("validation:view")
@tenant_required
def score():
 r=repo().scoped(repo().results,org()); return jsonify({"security_score":round(sum(x.overall_score for x in r)/len(r),2) if r else 0,"runs":len(r)})
@validation_ai_api.get("/workspace/security-validation")
@permission_required("validation:view")
@tenant_required
def dashboard(): return render_template("security_validation.html")
