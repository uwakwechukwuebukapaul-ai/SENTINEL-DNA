"""
Sentinel DNA Dashboard Service.

Builds analyst dashboard payloads.
"""

from __future__ import annotations

from typing import Any

from services.intelligence.dashboard.dashboard_repository import (
    DashboardRepository,
)

from services.intelligence.workspace.analyst_workspace import (
    AnalystWorkspace,
)

from services.intelligence.workspace.investigation_view import (
    InvestigationView,
)

from services.intelligence.dashboard.dashboard_adapter import (
    DashboardAdapter,
)



class DashboardService:
    """
    Dashboard orchestration service.
    """


    def __init__(
        self,
    ) -> None:

        self.repository = DashboardRepository()

        self.workspace = AnalystWorkspace()

        self.view = InvestigationView()

        self.adapter = DashboardAdapter()



    def get_dashboard(
        self,
        case_id: str,
    ) -> dict[str, Any]:
        """
        Build dashboard from case id.
        """


        investigation = self.repository.get_investigation(
            case_id
        )


        workspace = self.workspace.load(
            investigation
        )


        analyst_view = self.view.render(
            workspace
        )


        return self.adapter.build(
            analyst_view
        )