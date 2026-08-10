"""
Dashboard Adapter Tests.
"""

from services.intelligence.dashboard.dashboard_adapter import (
    DashboardAdapter,
)



def sample_view():

    return {

        "case_id": "CASE-001",

        "investigation_id": "INV-001",

        "status": "completed",

        "risk": "high",

        "confidence": 0.95,

        "summary": {

            "finding_count": 2,

            "indicator_count": 4,

        },

        "mitre": [

            "T1566",

        ],

        "timeline": [

            {
                "event_type": "investigation_started"
            }

        ],

        "recommendations": [

            "Reset credentials"

        ],

    }



def test_adapter_creation():

    adapter = DashboardAdapter()

    assert adapter is not None



def test_dashboard_build():

    adapter = DashboardAdapter()

    result = adapter.build(
        sample_view()
    )

    assert result["case"]["case_id"] == "CASE-001"



def test_dashboard_risk():

    adapter = DashboardAdapter()

    result = adapter.build(
        sample_view()
    )

    assert result["risk"]["level"] == "high"



def test_dashboard_metrics():

    adapter = DashboardAdapter()

    result = adapter.build(
        sample_view()
    )

    assert result["metrics"]["findings"] == 2