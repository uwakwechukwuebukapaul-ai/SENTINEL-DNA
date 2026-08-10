"""
Sentinel DNA Application Container.

Builds production service graph.
"""

from .service_registry import (
    ServiceRegistry,
)

from ..intelligence.cases.case_manager import (
    CaseManager,
)


from ..intelligence.orchestration.investigation_orchestrator import (
    InvestigationOrchestrator,
)



def build_container():

    registry = ServiceRegistry()


    case_manager = CaseManager()


    orchestrator = InvestigationOrchestrator(
        case_manager=case_manager,
    )


    registry.register(
        "case_manager",
        case_manager,
    )


    registry.register(
        "investigation_orchestrator",
        orchestrator,
    )


    return registry