"""
Runtime Investigation Bridge

Connects Investigation Runtime
with Intelligence Runtime execution.
"""

from typing import Any

from services.intelligence.runtime.runtime_intelligence_service import (
    RuntimeIntelligenceService,
)


class RuntimeInvestigationBridge:
    """
    Bridge between investigation execution
    and intelligence analysis.
    """


    def __init__(
        self,
        intelligence_service: RuntimeIntelligenceService,
    ):

        self.intelligence_service = (
            intelligence_service
        )


    def analyze_investigation(
        self,
        investigation_id: str,
        signals: list[dict[str, Any]],
    ):

        result = (
            self.intelligence_service.investigate(
                signals,
                case_id=investigation_id,
            )
        )


        return result