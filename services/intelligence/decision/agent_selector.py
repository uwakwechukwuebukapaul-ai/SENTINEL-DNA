"""
Sentinel DNA Agent Selection Engine

Selects investigation agents based on strategy.
"""

from __future__ import annotations

from typing import Any


class AgentSelector:
    """
    Determines required SOC agents.
    """


    def select(
        self,
        investigation: dict[str, Any],
    ) -> list[str]:
        """
        Select investigation agents.
        """


        agents = []


        category = str(
            investigation.get(
                "category",
                "",
            )
        ).lower()


        alert_type = str(
            investigation.get(
                "type",
                "",
            )
        ).lower()


        if (
            "phish" in category
            or "email" in alert_type
        ):

            agents.extend(
                [
                    "email_analysis_agent",
                    "ioc_enrichment_agent",
                    "threat_intelligence_agent",
                ]
            )


        elif (
            "malware" in category
        ):

            agents.extend(
                [
                    "malware_analysis_agent",
                    "sandbox_agent",
                    "ioc_enrichment_agent",
                ]
            )


        elif (
            "credential" in category
        ):

            agents.extend(
                [
                    "identity_agent",
                    "log_analysis_agent",
                    "threat_hunting_agent",
                ]
            )


        else:

            agents.extend(
                [
                    "evidence_agent",
                    "threat_intelligence_agent",
                ]
            )


        return agents