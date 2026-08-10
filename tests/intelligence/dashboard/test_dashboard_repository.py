"""
Dashboard Repository Tests.
"""

from services.intelligence.dashboard.dashboard_repository import (
    DashboardRepository,
)



def test_repository_creation():

    repository = DashboardRepository()

    assert repository is not None



def test_repository_returns_case():

    repository = DashboardRepository()

    result = repository.get_investigation(
        "CASE-001"
    )

    assert result["case_id"] == "CASE-001"



def test_repository_has_risk():

    repository = DashboardRepository()

    result = repository.get_investigation(
        "CASE-001"
    )

    assert "risk" in result