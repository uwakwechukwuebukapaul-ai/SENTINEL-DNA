"""
Sentinel DNA Dashboard API.

Provides analyst dashboard payloads.
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from services.intelligence.dashboard.dashboard_adapter import (
    DashboardAdapter,
)


dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/api/dashboard",
)


adapter = DashboardAdapter()



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

    sample_view = {

        "case_id": "CASE-001",

        "investigation_id": "INV-001",

        "status": "completed",

        "risk": "high",

        "confidence": 0.95,

        "summary": {

            "finding_count": 2,

            "indicator_count": 4,

        },

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


    result = adapter.build(
        sample_view
    )


    return jsonify(
        result
    ), 200