"""
Sentinel DNA Agent Runtime Adapter

Bridges Intelligence Agents with RuntimeTaskExecutor.

Responsibilities:

- Register agents into runtime
- Translate orchestration context
  into agent execution context
- Execute agent capabilities
"""

from __future__ import annotations

from typing import Any

from services.intelligence.agents.base_agent import (
    BaseAgent,
)

from services.intelligence.agents.agent_context import (
    AgentContext,
)


class AgentRuntimeAdapter:
    """
    Registers AI agents into runtime execution layer.
    """


    def __init__(
        self,
        runtime_executor,
    ) -> None:

        self.runtime_executor = runtime_executor



    def register_agent(
        self,
        agent: BaseAgent,
    ) -> None:
        """
        Register agent capabilities.
        """

        for capability in agent.capabilities:

            capability_name = getattr(
                capability,
                "value",
                None,
            )


            if capability_name is None:

                capability_name = getattr(
                    capability,
                    "name",
                    None,
                )


            if not capability_name:
                continue


            self.runtime_executor.register(
                capability_name,
                self._create_handler(
                    agent,
                    capability_name,
                ),
            )



    def _create_handler(
        self,
        agent: BaseAgent,
        capability_name: str,
    ):

        def handler(
            payload: dict[str, Any],
        ):

            context = (
                self._build_agent_context(
                    payload
                )
            )


            return agent.execute(
                context
            )


        return handler



    def _build_agent_context(
        self,
        payload: dict[str, Any],
    ) -> AgentContext:
        """
        Convert orchestration context
        into agent execution context.
        """

        investigation_context = payload.get(
            "context"
        )


        case_id = payload.get(
            "case_id",
            "unknown",
        )


        alert = payload.get(
            "alert",
            {},
        )


        iocs = []


        if investigation_context:

            iocs.extend(
                getattr(
                    investigation_context,
                    "iocs",
                    [],
                )
            )


            evidence = getattr(
                investigation_context,
                "evidence",
                [],
            )


            for item in evidence:

                if isinstance(
                    item,
                    dict,
                ):

                    indicator = item.get(
                        "indicator"
                    )

                    if indicator:
                        iocs.append(
                            indicator
                        )



        indicator = alert.get(
            "indicator"
        )


        if indicator:

            iocs.append(
                indicator
            )



        # Remove duplicate IOCs

        iocs = list(
            dict.fromkeys(
                iocs
            )
        )



        return AgentContext(
            investigation_id=case_id,

            case_id=case_id,

            alert=alert,

            iocs=iocs,

            shared_data={
                "case_id": case_id,

                "alert": alert,

                "iocs": iocs,
            },
        )