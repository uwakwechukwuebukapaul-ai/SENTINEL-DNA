"""
Sentinel DNA Investigation API Routes.

HTTP interface for Sentinel DNA investigations.

Uses the application service container to resolve
the canonical InvestigationCoordinator.

Architecture:

HTTP Request
    |
    v
Investigation API
    |
    v
InvestigationController
    |
    v
InvestigationCoordinator
    |
    v
InvestigationOrchestrator
    |
    v
RuntimeTaskExecutor
"""

from __future__ import annotations

from typing import Any

from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
)

from .controller import InvestigationController
from services.intelligence.orchestration import (
    InvestigationCoordinator,
)


investigation_bp = Blueprint(
    "investigations",
    __name__,
    url_prefix="/api/investigations",
)


# ============================================================
# DEPENDENCY RESOLUTION
# ============================================================

def get_coordinator() -> InvestigationCoordinator:
    """
    Resolve the canonical InvestigationCoordinator
    from the application service container.
    """

    container = getattr(
        current_app,
        "container",
        None,
    )

    if container is None:
        raise RuntimeError(
            "Sentinel DNA application container is not configured."
        )

    coordinator = container.get(
        "investigation_coordinator"
    )

    if coordinator is None:
        raise RuntimeError(
            "InvestigationCoordinator is not registered "
            "in the application container."
        )

    if not isinstance(
        coordinator,
        InvestigationCoordinator,
    ):
        raise RuntimeError(
            "Registered investigation_coordinator is not "
            "an InvestigationCoordinator instance."
        )

    return coordinator


def get_controller() -> InvestigationController:
    """
    Resolve the API controller using the canonical
    application InvestigationCoordinator.
    """

    return InvestigationController(
        coordinator=get_coordinator(),
    )


# ============================================================
# RUN INVESTIGATION
# ============================================================

@investigation_bp.route(
    "/run",
    methods=[
        "POST",
    ],
)
def run_investigation():
    """
    Execute a security investigation.
    """

    payload: dict[str, Any] = (
        request.get_json(
            silent=True
        )
        or {}
    )

    artifacts = payload.get(
        "artifacts",
        [],
    )

    if not isinstance(
        artifacts,
        list,
    ):
        return jsonify(
            {
                "success": False,
                "status": "failed",
                "error": (
                    "artifacts must be an array"
                ),
            }
        ), 400

    case_id = payload.get(
        "case_id",
    )

    alert = payload.get(
        "alert",
        {},
    )

    if alert is None:
        alert = {}

    if not isinstance(
        alert,
        dict,
    ):
        return jsonify(
            {
                "success": False,
                "status": "failed",
                "error": (
                    "alert must be an object"
                ),
            }
        ), 400

    controller = get_controller()

    result = controller.run(
        artifacts=artifacts,
        case_id=case_id,
        alert=alert,
    )

    return jsonify(
        result
    ), 200


# ============================================================
# COMPATIBILITY ROUTE
# ============================================================

@investigation_bp.route(
    "/investigate",
    methods=[
        "POST",
    ],
)
def investigate():
    """
    Legacy compatibility endpoint.

    Maps to /run while preserving the historical
    /api/investigations/investigate endpoint.
    """

    return run_investigation()


__all__ = [
    "investigation_bp",
    "get_coordinator",
    "get_controller",
    "run_investigation",
    "investigate",
]