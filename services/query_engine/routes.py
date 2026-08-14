from flask import Blueprint,current_app,jsonify,request
from services.auth.permissions import permission_required
from services.tenancy.context import current_organization,tenant_required
query_api=Blueprint("query_api",__name__)
def org(): return current_organization().organization_id
@query_api.post("/api/query/run")
@permission_required("query:view")
@tenant_required
def run(): return jsonify(current_app.container.get("security_query_executor").run(org(),(request.get_json(silent=True) or {}).get("query","")))
@query_api.get("/api/query/history")
@permission_required("query:view")
@tenant_required
def history(): return jsonify({"history":current_app.container.get("security_query_executor").history})
@query_api.get("/api/query/templates")
@permission_required("query:view")
@tenant_required
def templates(): return jsonify({"templates":["FROM events WHERE severity=high WITHIN 24h"]})
