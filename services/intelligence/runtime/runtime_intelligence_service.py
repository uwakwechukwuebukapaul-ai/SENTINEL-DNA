"""
Runtime Intelligence Service

Coordinates:

- intelligence providers
- correlation engine
- fusion engine
- runtime intelligence context
- final intelligence output
"""

from typing import Any


from services.intelligence.runtime.runtime_intelligence_context import (
    RuntimeIntelligenceContext,
)


from services.intelligence.runtime.runtime_intelligence_result import (
    RuntimeIntelligenceResult,
)



class RuntimeIntelligenceService:
    """
    Main orchestration service for intelligence execution.
    """


    def __init__(
        self,
        providers=None,
        correlation_engine=None,
        fusion_engine=None,
    ):

        self.providers = (
            providers
            or []
        )


        self.correlation_engine = (
            correlation_engine
        )


        self.fusion_engine = (
            fusion_engine
        )



    def investigate(
        self,
        signals: list[dict[str, Any]],
        case_id: str | None = None,
    ) -> RuntimeIntelligenceResult:

        context = RuntimeIntelligenceContext(

            case_id=case_id,

            signals=signals,

        )


        context.update_status(
            "running"
        )


        provider_names = []


        #
        # Intelligence Providers
        #

        for provider in self.providers:

            records = (
                provider.enrich(
                    signals
                )
            )


            if records:

                context.intelligence_records.extend(
                    records
                )


            provider_names.append(
                provider.__class__.__name__
            )


            context.add_event(

                {

                    "stage":
                        "provider",

                    "provider":
                        provider.__class__.__name__,

                    "records":
                        len(records),

                }

            )


        #
        # Correlation
        #

        if self.correlation_engine:


            correlation = (
                self.correlation_engine.correlate(
                    signals
                )
            )


            context.add_correlation(
                correlation
            )


            context.add_event(

                {

                    "stage":
                        "correlation",

                }

            )


        #
        # Fusion
        #

        if self.fusion_engine:


            fusion = (
                self.fusion_engine.fuse(
                    context
                )
            )


            context.add_fusion_result(
                fusion
            )


            context.add_event(

                {

                    "stage":
                        "fusion",

                }

            )


        context.update_status(
            "completed"
        )


        return self._build_result(
            context,
            provider_names,
        )



    def _build_result(
        self,
        context: RuntimeIntelligenceContext,
        providers: list[str],
    ):

        risk = "unknown"

        confidence = 0.0

        mitre = []


        fusion_results = (
            context.fusion_results
        )


        if fusion_results:


            fusion = (
                fusion_results[0]
            )


            risk = getattr(
                fusion,
                "risk",
                risk,
            )


            confidence = getattr(
                fusion,
                "confidence",
                confidence,
            )


            mitre = getattr(
                fusion,
                "mitre",
                [],
            )



        return RuntimeIntelligenceResult(

            success=True,

            risk=risk,

            confidence=confidence,

            mitre=mitre,

            providers=providers,

            correlations=context.correlations,

            intelligence_records=(
                context.intelligence_records
            ),

            fusion_results=(
                context.fusion_results
            ),

            metadata={

                "case_id":
                    context.case_id,

                "signal_count":
                    len(
                        context.signals
                    ),

                "status":
                    context.status,

                "timeline":
                    context.timeline,

            },

        )