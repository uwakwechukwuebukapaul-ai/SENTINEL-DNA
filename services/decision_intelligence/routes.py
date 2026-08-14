from flask import Blueprint,current_app,jsonify,request,render_template,session
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization,tenant_required
decision_api=Blueprint("decision_intelligence_api",__name__)
def org(): return current_organization().organization_id
@decision_api.post("/api/decisions/analyze")
@permission_required("decision:analyze")
@tenant_required
def analyze():
 x=current_app.container.get("decision_intelligence").decide(org(),request.get_json(silent=True) or {}); current_app.container.get("audit_service").record("SECURITY_DECISION_CREATED",user_id=session.get("user_id"),details={}); return jsonify(x),201
@decision_api.get("/api/decisions")
@permission_required("decision:view")
@tenant_required
def decisions(): return jsonify({"decisions":current_app.container.get("decision_intelligence").scoped(org())})
@decision_api.get("/workspace/decision-intelligence")
@permission_required("decision:view")
@tenant_required
def workspace(): return render_template("decision_intelligence.html")
