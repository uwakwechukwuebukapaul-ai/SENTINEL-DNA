"""
Sentinel DNA Dashboard Compatibility Provider.

Temporary provider used until
database-backed case retrieval is connected.
"""

from __future__ import annotations

from typing import Any


class DashboardFallbackProvider:
    """
    Temporary investigation provider.
    """


    def get(
        self,
        case_id: str,
    ) -> dict[str, Any]:

        return {

            "case_id": case_id,

            "investigation_id": (
                f"INV-{case_id}"
            ),

            "status": "completed",

            "risk": {

                "level": "high",

                "score": 90,

            },

            "confidence": 0.95,

            "findings": [],

            "indicators": [],

            "mitre": [],

            "timeline": [],

            "recommendations": [],

            "report": {},

        }