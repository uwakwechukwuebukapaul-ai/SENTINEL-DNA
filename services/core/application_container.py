"""
Sentinel DNA Application Container.

Builds and manages enterprise
service dependency graph.
"""

from __future__ import annotations

from services.core.service_registry import (
    ServiceRegistry,
)

from services.intelligence.cases.case_manager import (
    CaseManager,
)

from services.intelligence.orchestration.investigation_orchestrator import (
    InvestigationOrchestrator,
)

from services.intelligence.dashboard.dashboard_service import (
    DashboardService,
)



def build_container() -> ServiceRegistry:
    """
    Build Sentinel DNA service container.
    """


    registry = ServiceRegistry()


    # ==================================
    # Core Intelligence Services
    # ==================================

    case_manager = CaseManager()


    orchestrator = InvestigationOrchestrator(
        case_manager=case_manager,
    )


    dashboard_service = DashboardService()



    # ==================================
    # Register Services
    # ==================================

    registry.register(
        "case_manager",
        case_manager,
    )


    registry.register(
        "investigation_orchestrator",
        orchestrator,
    )


    registry.register(
        "dashboard_service",
        dashboard_service,
    )


    return registry