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
from services.intelligence.threat_intelligence.ioc_extractor import IOCExtractor


class AgentRuntimeAdapter:
    """
    Registers AI agents into runtime execution layer.
    """


    def __init__(
        self,
        runtime_executor,
    ) -> None:

        self.runtime_executor = runtime_executor
        self.ioc_extractor = IOCExtractor()



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
        evidence = []
        timeline = []

        evidence.extend(payload.get("artifacts", []) or [])


        if investigation_context:

            for ioc in getattr(
                investigation_context,
                "iocs",
                [],
            ):
                if isinstance(ioc, dict):
                    value = ioc.get("value") or ioc.get("indicator")
                    if value:
                        iocs.append(str(value))
                elif ioc:
                    iocs.append(str(ioc))


            evidence.extend(getattr(
                investigation_context,
                "evidence",
                [],
            ))

            timeline.extend(getattr(
                investigation_context,
                "timeline",
                [],
            ))


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

                # Evidence envelopes contain integrity/provenance hashes.
                # Extract observables from content fields only; audit hashes
                # must never become investigation IOCs.
                content = item.get("data") or item.get("value") or item.get("raw") or item.get("description") or "" if isinstance(item, dict) else item
                for indicator in self.ioc_extractor.extract(content):
                    iocs.append(indicator.get("value"))



        indicator = alert.get(
            "indicator"
        )


        if indicator:

            iocs.append(
                indicator
            )



        # Remove duplicate IOCs

        iocs = list(dict.fromkeys(iocs))



        return AgentContext(
            investigation_id=case_id,

            case_id=case_id,

            alert=alert,

            evidence=evidence,

            iocs=iocs,

            timeline=timeline,

            shared_data={
                "case_id": case_id,

                "alert": alert,

                "iocs": iocs,

                "evidence": evidence,

                "timeline": timeline,
            },
        )
