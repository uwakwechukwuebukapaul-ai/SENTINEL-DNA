from flask import Blueprint,current_app,jsonify,request,render_template
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization,tenant_required
memory_api=Blueprint("security_memory_api",__name__)
def org(): return current_organization().organization_id
def graph(): return current_app.container.get("knowledge_graph")
@memory_api.post("/api/memory/entities")
@permission_required("memory:manage")
@tenant_required
def entity(): return jsonify(graph().add_entity(org(),request.get_json(silent=True) or {}).public()),201
@memory_api.get("/api/memory/search")
@permission_required("memory:search")
@tenant_required
def search(): return jsonify({"entities":[x.public() for x in graph().search(org(),request.args.get("q",""))]})
@memory_api.get("/api/memory/related/<entity_id>")
@permission_required("memory:view")
@tenant_required
def related(entity_id): return jsonify({"relationships":[x.public() for x in current_app.container.get("memory_relationship_manager").related(org(),entity_id)]})
@memory_api.post("/api/memory/learn")
@permission_required("memory:learn")
@tenant_required
def learn(): return jsonify(current_app.container.get("memory_learning_engine").learn(org(),request.get_json(silent=True) or {})),201
@memory_api.get("/api/memory/insights")
@permission_required("memory:view")
@tenant_required
def insights(): return jsonify({"insights":[x for x in current_app.container.get("memory_learning_engine").insights if x["organization_id"]==org()]})
@memory_api.get("/workspace/security-memory")
@permission_required("memory:view")
@tenant_required
def workspace(): return render_template("security_memory.html")
