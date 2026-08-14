from flask import Blueprint,current_app,jsonify,request,render_template
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization,tenant_required
advisor_api=Blueprint("security_advisor_api",__name__)
def org(): return current_organization().organization_id
def repo(): return current_app.container.get("advisor_repository")
def posture():
 r=repo(); x=r.scoped(r.postures,org()); return x[-1] if x else current_app.container.get("posture_engine").calculate(org())
@advisor_api.get("/api/advisor/posture")
@permission_required("advisor:view")
@tenant_required
def posture_api(): return jsonify(posture().public())
@advisor_api.get("/api/advisor/risks")
@permission_required("advisor:view")
@tenant_required
def risks():
 r=repo(); return jsonify({"risks":[x.public() for x in r.scoped(r.risks,org())]})
@advisor_api.get("/api/advisor/recommendations")
@permission_required("advisor:view")
@tenant_required
def recommendations():
 r=repo(); return jsonify({"recommendations":[x.public() for x in r.scoped(r.recommendations,org())]})
@advisor_api.post("/api/advisor/report")
@permission_required("advisor:report")
@tenant_required
def report():
 p=posture(); r=repo(); return jsonify(current_app.container.get("advisor_report_engine").generate(p,r.scoped(r.risks,org()),r.scoped(r.recommendations,org())))
@advisor_api.get("/api/advisor/forecast")
@permission_required("advisor:view")
@tenant_required
def forecast(): return jsonify({"forecast":current_app.container.get("risk_forecast_engine").forecast()})
@advisor_api.get("/workspace/security-advisor")
@permission_required("advisor:view")
@tenant_required
def workspace(): return render_template("security_advisor.html")
