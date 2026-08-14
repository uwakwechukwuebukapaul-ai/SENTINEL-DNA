from flask import Blueprint, current_app, jsonify, request, session, render_template
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization, tenant_required
hunting_ai_api=Blueprint("autonomous_hunting_api",__name__)
def org(): return current_organization().organization_id
def repo(): return current_app.container.get("autonomous_hunting_repository")
@hunting_ai_api.get("/api/hunting/ai/hypotheses")
@permission_required("hunting:view")
@tenant_required
def hypotheses():
    r=repo(); return jsonify({"hypotheses":[x.public() for x in r.scoped(r.hypotheses,org())]})
@hunting_ai_api.get("/api/hunting/ai/history")
@permission_required("hunting:view")
@tenant_required
def history():
    r=repo(); return jsonify({"executions":[x.public() for x in r.scoped(r.executions,org())]})
@hunting_ai_api.get("/api/hunting/ai/findings")
@permission_required("hunting:view")
@tenant_required
def findings():
    r=repo(); return jsonify({"findings":[x.public() for x in r.scoped(r.findings,org())]})
@hunting_ai_api.post("/api/hunting/ai/start")
@permission_required("hunting:execute")
@tenant_required
def start():
    h=current_app.container.get("autonomous_hypothesis_engine").generate(org()); repo().hypotheses.append(h); return jsonify(h.public()),201
@hunting_ai_api.get("/workspace/autonomous-hunting")
@permission_required("hunting:view")
@tenant_required
def workspace(): return render_template("autonomous_hunting.html")
