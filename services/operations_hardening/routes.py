from flask import Blueprint,current_app,jsonify,render_template
from services.auth.permissions import permission_required
from services.tenancy.context import tenant_required
ops_api=Blueprint("operations_hardening_api",__name__)
@ops_api.get("/api/operations/health")
@permission_required("operations:view")
@tenant_required
def health(): return jsonify(current_app.container.get("operations_hardening").health())
@ops_api.get("/api/operations/diagnostics")
@permission_required("operations:view")
@tenant_required
def diagnostics(): return jsonify(current_app.container.get("operations_hardening").diagnostics())
@ops_api.get("/api/operations/metrics")
@permission_required("operations:view")
@tenant_required
def metrics(): return jsonify({"metrics":current_app.container.get("operations_hardening").metrics})
@ops_api.get("/workspace/operations")
@permission_required("operations:view")
@tenant_required
def workspace(): return render_template("operations.html")
