from flask import Blueprint,current_app,jsonify,request,render_template
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization,tenant_required
soc_api=Blueprint("soc_manager_api",__name__)
def org(): return current_organization().organization_id
def repo(): return current_app.container.get("soc_repository")
@soc_api.post("/api/soc/tasks")
@permission_required("soc:manage")
@tenant_required
def create(): return jsonify(current_app.container.get("soc_task_manager").create(org(),request.get_json(silent=True) or {}).public()),201
@soc_api.get("/api/soc/tasks")
@permission_required("soc:view")
@tenant_required
def tasks():
 r=repo(); return jsonify({"tasks":[x.public() for x in r.scoped(r.tasks,org())]})
@soc_api.get("/api/soc/tasks/<task_id>")
@permission_required("soc:view")
@tenant_required
def task(task_id):
 r=repo(); x=next((x for x in r.scoped(r.tasks,org()) if x.id==task_id),None); return jsonify(x.public()) if x else (jsonify({"error":"task_not_found"}),404)
@soc_api.post("/api/soc/tasks/<task_id>/assign")
@permission_required("soc:assign")
@tenant_required
def assign(task_id):
 r=repo(); x=next((x for x in r.scoped(r.tasks,org()) if x.id==task_id),None); x.assigned_agent=(request.get_json(silent=True) or {}).get("agent_id",""); x.status="ASSIGNED"; return jsonify(x.public())
@soc_api.get("/api/soc/agents")
@permission_required("soc:view")
@tenant_required
def agents():
 r=repo(); return jsonify({"agents":[x.public() for x in r.scoped(r.agents,org())]})
@soc_api.get("/api/soc/performance")
@permission_required("soc:view")
@tenant_required
def performance():
 r=repo(); return jsonify(current_app.container.get("soc_performance_engine").metrics(r.scoped(r.tasks,org())))
@soc_api.get("/api/soc/decisions")
@permission_required("soc:view")
@tenant_required
def decisions():
 r=repo(); return jsonify({"decisions":[x.public() for x in r.scoped(r.decisions,org())]})
@soc_api.get("/workspace/soc-command-center")
@permission_required("soc:view")
@tenant_required
def workspace(): return render_template("soc_command_center.html")
