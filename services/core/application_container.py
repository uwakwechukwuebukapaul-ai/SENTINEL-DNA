"""
Sentinel DNA Application Container.

Builds and manages the enterprise
service dependency graph.

The container owns construction of shared
application services and guarantees that
dependent services receive the same
runtime instances.
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
    Build and return the Sentinel DNA service container.

    Dependency graph:

        CaseManager
             |
             v
        InvestigationOrchestrator

        DashboardService

    All shared application services are instantiated
    once and registered in the service registry.
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
