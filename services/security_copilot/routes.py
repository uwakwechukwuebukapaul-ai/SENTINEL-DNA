from flask import Blueprint,current_app,jsonify,request,session,render_template
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization,tenant_required
copilot_ai_api=Blueprint("security_copilot_api",__name__)
def org(): return current_organization().organization_id
@copilot_ai_api.post("/api/security-copilot/ask")
@permission_required("copilot:use")
@tenant_required
def ask():
 p=request.get_json(silent=True) or {}; x=current_app.container.get("security_copilot").ask(org(),session.get("user_id",""),p.get("prompt",""),p.get("context",{})); current_app.container.get("audit_service").record("COPILOT_CONVERSATION",user_id=session.get("user_id"),details={"conversation_id":x["id"]}); return jsonify(x),201
@copilot_ai_api.get("/api/security-copilot/history")
@permission_required("copilot:view")
@tenant_required
def history(): return jsonify({"conversations":current_app.container.get("security_copilot").scoped(org())})
@copilot_ai_api.get("/workspace/security-copilot")
@permission_required("copilot:view")
@tenant_required
def workspace(): return render_template("security_copilot.html")
