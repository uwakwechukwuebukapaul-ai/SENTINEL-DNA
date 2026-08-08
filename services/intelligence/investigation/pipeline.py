"""
Sentinel DNA Autonomous Investigation Pipeline
"""

from __future__ import annotations

from typing import Any

from .pipeline_context import (
    InvestigationPipelineContext,
)

from .agent_factory import (
    InvestigationAgentFactory,
)

from .agent_result_collector import (
    AgentResultCollector,
)



class InvestigationPipeline:
    """
    End-to-end investigation workflow.
    """

    def __init__(self) -> None:

        self.factory = (
            InvestigationAgentFactory()
        )

        self.registry = (
            self.factory
            .register_default_agents()
        )

        self.collector = (
            AgentResultCollector()
        )



    def run(
        self,
        case_id: str,
        alert: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute investigation.
        """

        context = InvestigationPipelineContext(
            case_id,
            alert,
        )


        for agent in (
            self.registry.list_agents()
        ):

            result = (
                agent["handler"](
                    alert
                )
            )


            collected = (
                self.collector.add_result(
                    agent["name"],
                    result,
                )
            )


            context.add_result(
                collected
            )


        context.complete()


        return context.export()