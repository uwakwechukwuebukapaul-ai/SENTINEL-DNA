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

from services.intelligence.orchestration.investigation_coordinator import (
    InvestigationCoordinator,
)

from services.intelligence.agents.agent_registry import (
    AgentRegistry,
)

from services.intelligence.agents.bootstrap import (
    bootstrap_agents,
)

from services.intelligence.agents.runtime_adapter import (
    AgentRuntimeAdapter,
)

from services.intelligence.runtime.runtime_task_executor import (
    RuntimeTaskExecutor,
)

from services.intelligence.dashboard.dashboard_service import (
    DashboardService,
)


def build_container() -> ServiceRegistry:
    """
    Build and return the Sentinel DNA service container.

    Dependency graph:

        CaseManager

        AgentRegistry
             |
             v
        RuntimeTaskExecutor
             |
             v
        InvestigationCoordinator
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

    agent_registry = AgentRegistry()

    runtime_executor = RuntimeTaskExecutor()

    runtime_adapter = AgentRuntimeAdapter(
        runtime_executor,
    )

    bootstrap_agents(
        agent_registry,
        runtime_adapter=runtime_adapter,
    )

    orchestrator = InvestigationOrchestrator(
        case_manager=case_manager,
    )

    coordinator = InvestigationCoordinator(
        registry=agent_registry,
        runtime=runtime_executor,
        orchestrator=orchestrator,
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
        "agent_registry",
        agent_registry,
    )

    registry.register(
        "runtime_task_executor",
        runtime_executor,
    )

    registry.register(
        "investigation_coordinator",
        coordinator,
    )

    registry.register(
        "investigation_orchestrator",
        coordinator,
    )

    registry.register(
        "dashboard_service",
        dashboard_service,
    )

    return registry
