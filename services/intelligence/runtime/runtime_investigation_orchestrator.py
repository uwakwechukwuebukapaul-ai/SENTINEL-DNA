"""
Runtime Investigation Orchestrator

High-level runtime coordinator.

Connects runtime execution
with investigation orchestration.
"""

from __future__ import annotations


class RuntimeInvestigationOrchestrator:
    """
    Runtime orchestration adapter.
    """


    def __init__(
        self,
        investigation_service,
    ) -> None:

        self.investigation_service = (
            investigation_service
        )


    def execute(
        self,
        investigation_id: str,
        signals: list[dict],
    ):

        return (
            self.investigation_service.investigate(
                investigation_id,
                signals,
            )
        )