"""
Investigation API Routes.

HTTP interface for Sentinel DNA investigations.
"""

from __future__ import annotations

from flask import (
    Blueprint,
    request,
    jsonify,
)

from .controller import InvestigationController


investigation_bp = Blueprint(
    "investigations",
    __name__,
    url_prefix="/api/investigations",
)


controller = InvestigationController()


# =================================================
# RUN INVESTIGATION
# =================================================

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
            "case_id"
        )
    )


    result = controller.run(
        artifacts=artifacts,
        case_id=case_id,
    )


    return jsonify(
        result
    ), 200



# =================================================
# COMPATIBILITY ROUTE
# =================================================

@investigation_bp.route(
    "/investigate",
    methods=[
        "POST",
    ],
)
def investigate():

    return run_investigation()