"""
Sentinel DNA IOC Investigator

Analyzes indicators of compromise.
"""

from __future__ import annotations

from typing import Any


class IOCInvestigator:
    """
    IOC enrichment and analysis engine.
    """


    def execute(
        self,
        case_id: str,
        alert: dict[str, Any],
    ) -> dict[str, Any]:

        source = alert.get(
            "source",
            "unknown",
        )

        iocs = []

        if source == "email":
            iocs.append(
                {
                    "type": "domain",
                    "value": "evil-login.com",
                    "reputation": "malicious",
                    "confidence": 0.95,
                }
            )


        return {
            "case_id": case_id,
            "ioc_count": len(iocs),
            "iocs": iocs,
        }