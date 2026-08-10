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


    service = get_dashboard_service()


    investigation = {

        "case_id": "CASE-001",

        "investigation_id": "INV-001",

        "status": "completed",


        "risk": {

            "level": "high",

            "score": 90,

        },


        "confidence": 0.95,


        "findings": [

            "Suspicious authentication activity",

        ],


        "indicators": [

            "evil.com",

        ],


        "mitre": [

            "T1566",

        ],


        "timeline": [],


        "recommendations": [

            "Reset credentials",

        ],


        "report": {},

    }


    result = service.build(
        investigation
    )


    return jsonify(
        result
    ), 200