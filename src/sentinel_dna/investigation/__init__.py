"""
Sentinel DNA Investigation Package.

Stable public API boundary.

External callers and tests should import
investigation components from this module.
"""

from sentinel_dna.investigation.context import (
    InvestigationContext,
)

from sentinel_dna.investigation.coordinator import (
    InvestigationCoordinator,
)

from sentinel_dna.investigation.orchestrator import (
    InvestigationOrchestrator,
)

from sentinel_dna.investigation.result import (
    InvestigationResult,
)

from sentinel_dna.investigation.trace import (
    InvestigationTrace,
)

from sentinel_dna.investigation.runtime import (
    RuntimeTask,
    RuntimeTaskExecutor,
)

try:
    from sentinel_dna.investigation.replay import (
        InvestigationReplay,
    )
except ImportError:
    InvestigationReplay = None


__all__ = [
    "InvestigationContext",
    "InvestigationCoordinator",
    "InvestigationOrchestrator",
    "InvestigationResult",
    "InvestigationTrace",
    "RuntimeTask",
    "RuntimeTaskExecutor",
    "InvestigationReplay",
]