"""
Sentinel DNA Dashboard Service.

Coordinates dashboard data retrieval
and analyst payload generation.
"""

from __future__ import annotations

from typing import Any

from services.intelligence.dashboard.dashboard_repository import (
    DashboardRepository,
)

from services.intelligence.dashboard.dashboard_adapter import (
    DashboardAdapter,
)


class DashboardService:
    """
    Dashboard application service.
    """



    def __init__(
        self,
        repository: DashboardRepository | None = None,
        adapter: DashboardAdapter | None = None,
    ) -> None:


        self.repository = (
            repository
            or DashboardRepository()
        )


        self.adapter = (
            adapter
            or DashboardAdapter()
        )



    # =====================================================
    # BUILD DASHBOARD
    # =====================================================

    def build(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build dashboard payload.
        """


        return self.adapter.build(
            investigation
        )



    # =====================================================
    # GET DASHBOARD
    # =====================================================

    def get_dashboard(
        self,
        case_id: str,
    ) -> dict[str, Any]:
        """
        Retrieve case and build dashboard.
        """


        investigation = (
            self.repository.get_investigation(
                case_id
            )
        )


        return self.build(
            investigation
        )



    # =====================================================
    # COMPATIBILITY
    # =====================================================

    def get(
        self,
        case_id: str,
    ) -> dict[str, Any]:

        return self.get_dashboard(
            case_id
        )