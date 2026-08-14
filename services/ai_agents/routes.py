from flask import Blueprint, current_app, jsonify, request, render_template
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization, tenant_required
agent_api = Blueprint("agent_api", __name__)
def org(): return current_organization().organization_id
@agent_api.get("/api/agents")
@permission_required("agents:view")
@tenant_required
def agents():
    r=current_app.container.get("agent_registry"); return jsonify({"agents":[x.public() for x in r.scoped(org())]})
@agent_api.post("/api/agents/run")
@permission_required("agents:execute")
@tenant_required
def run(): return jsonify(current_app.container.get("agent_supervisor").run(org(),request.get_json(silent=True) or {}))
@agent_api.get("/workspace/agents")
@permission_required("agents:view")
@tenant_required
def workspace(): return render_template("agents.html")
