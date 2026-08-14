from flask import Blueprint,current_app,jsonify,render_template
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization,tenant_required
graph_api=Blueprint("graph_api",__name__)
def org(): return current_organization().organization_id
@graph_api.get("/api/graph/entity/<entity_id>")
@permission_required("graph:view")
@tenant_required
def entity(entity_id): return jsonify(current_app.container.get("graph_analyzer").entity(org(),entity_id))
@graph_api.get("/api/graph/path/<incident_id>")
@permission_required("graph:view")
@tenant_required
def path(incident_id): return jsonify(current_app.container.get("graph_analyzer").path(org(),incident_id))
@graph_api.get("/api/graph/blast-radius/<entity_id>")
@permission_required("graph:view")
@tenant_required
def blast(entity_id): return jsonify(current_app.container.get("graph_analyzer").blast_radius(org(),entity_id))
@graph_api.get("/workspace/threat-graph")
@permission_required("graph:view")
@tenant_required
def workspace(): return render_template("threat_graph.html")
