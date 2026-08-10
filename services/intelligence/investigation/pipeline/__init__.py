"""
Sentinel DNA Investigation Pipeline.
"""

from .models import (
    InvestigationPipelineResult,
)

from .orchestrator import (
    InvestigationPipelineOrchestrator,
)


class InvestigationPipeline(
    InvestigationPipelineOrchestrator
):
    """
    Backward compatible investigation pipeline API.

    Delegates execution to the orchestrator.
    """

    pass


__all__ = [
    "InvestigationPipeline",
    "InvestigationPipelineResult",
    "InvestigationPipelineOrchestrator",
]