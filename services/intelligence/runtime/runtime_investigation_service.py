"""
Runtime Investigation Service

Coordinates investigation execution.
"""

from typing import Any


from services.intelligence.runtime.runtime_investigation_context import (
    RuntimeInvestigationContext,
)


from services.intelligence.runtime.runtime_investigation_result import (
    RuntimeInvestigationResult,
)



class RuntimeInvestigationService:


    def __init__(
        self,
        intelligence_service,
    ):

        self.intelligence_service = (
            intelligence_service
        )



    def investigate(
        self,
        investigation_id: str,
        signals: list[dict[str, Any]],
    ):


        context = RuntimeInvestigationContext(

            investigation_id=
                investigation_id,

            signals=
                signals,

        )


        context.add_event(
            {
                "stage":
                    "started",

                "signal_count":
                    len(signals),
            }
        )


        intelligence = (
            self.intelligence_service.investigate(
                signals,
                case_id=investigation_id,
            )
        )


        context.intelligence_result = intelligence


        context.add_event(
            {
                "stage":
                    "intelligence_completed",
            }
        )


        return self._build_result(
            context
        )



    def _build_result(
        self,
        context,
    ):


        intelligence = (
            context.intelligence_result
        )


        return RuntimeInvestigationResult(

            success=True,

            investigation_id=
                context.investigation_id,

            risk=
                getattr(
                    intelligence,
                    "risk",
                    "unknown",
                ),

            confidence=
                getattr(
                    intelligence,
                    "confidence",
                    0.0,
                ),

            intelligence=
                intelligence,

            timeline=
                context.timeline,

            metadata=
                {
                    "signals":
                        len(context.signals)
                },
        )