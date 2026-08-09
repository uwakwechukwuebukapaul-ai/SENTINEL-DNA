"""
Runtime Intelligence Service

Coordinates:
- providers
- correlation
- fusion
- intelligence output
"""

from typing import Any

from services.intelligence.runtime.runtime_intelligence_context import (
    RuntimeIntelligenceContext,
)

from services.intelligence.runtime.runtime_intelligence_result import (
    RuntimeIntelligenceResult,
)


class RuntimeIntelligenceService:


    def __init__(
        self,
        providers=None,
        correlation_engine=None,
        fusion_engine=None,
    ):

        self.providers = providers or []

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


        provider_names = []


        #
        # Intelligence Providers
        #

        for provider in self.providers:

            records = provider.enrich(
                signals
            )

            context.intelligence_records.extend(
                records
            )

            provider_names.append(
                provider.__class__.__name__
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


        return self._build_result(
            context,
            provider_names,
        )


    def _build_result(
        self,
        context,
        providers,
    ):


        risk = "unknown"

        confidence = 0.0

        mitre = []


        if context.fusion_results:

            fusion = (
                context.fusion_results[0]
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

            metadata={
                "case_id": context.case_id,
                "signal_count": len(
                    context.signals
                ),
            },
        )