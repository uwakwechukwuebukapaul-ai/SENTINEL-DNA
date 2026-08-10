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

from services.intelligence.dashboard.fallback_provider import (
    DashboardFallbackProvider,
)



class DashboardService:
    """
    Dashboard application service.

    Responsibilities:

    - Retrieve investigation data
    - Transform investigation data
    - Provide dashboard payloads
    """



    def __init__(
        self,
        repository: DashboardRepository | None = None,
        adapter: DashboardAdapter | None = None,
    ) -> None:


        self.repository = (
            repository
            or DashboardRepository(
                fallback_provider=DashboardFallbackProvider()
            )
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
        Build dashboard payload from investigation data.
        """


        return self.adapter.build(
            investigation
        )



    # =====================================================
    # GET INVESTIGATION DASHBOARD
    # =====================================================

    def get_dashboard(
        self,
        case_id: str,
    ) -> dict[str, Any]:
        """
        Retrieve and build dashboard payload.
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
    # COMPATIBILITY ALIAS
    # =====================================================

    def get(
        self,
        case_id: str,
    ) -> dict[str, Any]:
        """
        Compatibility alias.
        """

        return self.get_dashboard(
            case_id
        )