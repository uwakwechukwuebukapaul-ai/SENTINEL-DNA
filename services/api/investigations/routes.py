"""
Sentinel DNA Investigation API Routes.

HTTP interface for Sentinel DNA investigations.

Uses application container dependency injection.
"""

from __future__ import annotations

from flask import (
    Blueprint,
    request,
    jsonify,
    current_app,
)

from .controller import InvestigationController


investigation_bp = Blueprint(
    "investigations",
    __name__,
    url_prefix="/api/investigations",
)


# =====================================================
# DEPENDENCY RESOLUTION
# =====================================================

def get_controller() -> InvestigationController:
    """
    Resolve investigation controller from application container.
    """

    orchestrator = current_app.container.get(
        "investigation_orchestrator"
    )


    return InvestigationController(
        orchestrator=orchestrator,
    )



# =====================================================
# RUN INVESTIGATION
# =====================================================

@investigation_bp.route(
    "/run",
    methods=[
        "POST",
    ],
)
def run_investigation():
    """
    Execute security investigation.
    """


    payload = (
        request.get_json(
            silent=True
        )
        or {}
    )


    artifacts = (
        payload.get(
            "artifacts",
            [],
        )
    )


    case_id = (
        payload.get(
            "case_id",
        )
    )


    controller = get_controller()


    result = controller.run(
        artifacts=artifacts,
        case_id=case_id,
    )


    return jsonify(
        result
    ), 200



# =====================================================
# COMPATIBILITY ROUTE
# =====================================================

@investigation_bp.route(
    "/investigate",
    methods=[
        "POST",
    ],
)
def investigate():
    """
    Legacy compatibility endpoint.

    Maps to /run.
    """

    return run_investigation()