"""
Sentinel DNA Dashboard API Routes.

Provides analyst dashboard payloads.

Uses application container dependency injection.
"""

from __future__ import annotations

from flask import (
    Blueprint,
    jsonify,
    current_app,
)
from services.core.security_context import authorize_investigation, request_context


dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/api/dashboard",
)



# =====================================================
# DEPENDENCY RESOLUTION
# =====================================================

def get_dashboard_service():
    """
    Resolve dashboard service from application container.
    """

    return current_app.container.get(
        "dashboard_service"
    )



# =====================================================
# INVESTIGATION DASHBOARD
# =====================================================

@dashboard_bp.route(
    "/investigation",
    methods=[
        "GET",
    ],
)
def investigation_dashboard():
    """
    Return dashboard-ready investigation payload.
    """


    context = request_context()
    allowed, error = authorize_investigation(
        {"metadata": {"tenant_id": context.tenant_id}}, write=False
    )
    if not allowed:
        return jsonify({"error": error}), 401 if error == "authentication_required" else 403
    if not context.tenant_id:
        return jsonify({"error": "organization_context_required"}), 403

    # Do not synthesize a dashboard record here.  The browser workspace and
    # the API must expose the same tenant-scoped persisted read model.
    snapshot = current_app.container.require("investigation_coordinator").get_workspace_snapshot(context.tenant_id)
    return jsonify({
        "tenant_id": context.tenant_id,
        "overview": snapshot["overview"],
        "investigations": snapshot["investigations"],
        "visualizations": snapshot["visualizations"],
    }), 200
