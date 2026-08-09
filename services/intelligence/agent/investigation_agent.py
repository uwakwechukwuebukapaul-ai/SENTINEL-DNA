"""
Autonomous Investigation Agent.

Coordinates investigation execution.
"""

from __future__ import annotations

from typing import Any

from .agent_state import AgentState
from .investigation_memory import InvestigationMemory
from .agent_executor import AgentExecutor



class InvestigationAgent:
    """
    Sentinel DNA autonomous investigator.
    """

    def __init__(
        self,
        executor: AgentExecutor | None = None,
        memory: InvestigationMemory | None = None,
    ):

        self.executor = (
            executor
            or AgentExecutor()
        )

        self.memory = (
            memory
            or InvestigationMemory()
        )



    def investigate(
        self,
        alert: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Run autonomous investigation.
        """

        case_id = (
            alert.get(
                "case_id",
                "UNKNOWN",
            )
        )


        state = AgentState(
            case_id=case_id
        )


        artifacts = (
            alert.get(
                "indicators",
                [],
            )
        )


        self.executor.execute(
            state,
            artifacts,
        )


        self.memory.remember(
            case_id,
            state.export(),
        )


        return {

            "case_id":
                case_id,


            "status":
                state.status,


            "investigation":
                {
                    "findings":
                        state.findings,

                    "confidence":
                        0.9,
                },


            "timeline":
                state.timeline,


            "memory":
                len(
                    self.memory.recall(
                        case_id
                    )
                ),
        }