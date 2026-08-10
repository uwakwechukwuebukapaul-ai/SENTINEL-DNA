"""
Sentinel DNA Dashboard API.

Provides analyst dashboard payloads.
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from services.intelligence.dashboard.dashboard_service import (
    DashboardService,
)


dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/api/dashboard",
)


service = DashboardService()



@dashboard_bp.route(
    "/investigation/<case_id>",
    methods=[
        "GET",
    ],
)
def investigation_dashboard(
    case_id: str,
):
    """
    Return dashboard-ready investigation payload.
    """


    result = service.get_dashboard(
        case_id
    )


    return jsonify(
        result
    ), 200