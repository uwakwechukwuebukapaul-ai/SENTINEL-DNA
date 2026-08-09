"""
Sentinel DNA Investigation Orchestrator

Central AI investigation coordinator.

Responsibilities:

- Coordinate investigation workflow
- Normalize intelligence execution
- Connect correlation, fusion, reasoning layers
- Manage investigation context
- Produce analyst-ready investigation results

Flow:

Alert / Case
      |
      v
Investigation Orchestrator
      |
      +--> Correlation Engine
      |
      +--> Threat Fusion Engine
      |
      +--> Reasoning Engine
      |
      v
Investigation Result
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid


from services.intelligence.correlation.correlation_engine import (
    CorrelationEngine,
)

from services.intelligence.fusion import (
    FusionEngine,
)

from services.intelligence.investigation.investigation_result import (
    InvestigationResult,
)


class InvestigationOrchestrator:
    """
    Enterprise investigation execution coordinator.
    """


    def __init__(
        self,
        correlation_engine: CorrelationEngine | None = None,
        fusion_engine: FusionEngine | None = None,
        reasoning_engine: Any | None = None,
    ) -> None:

        self.correlation_engine = (
            correlation_engine
            if correlation_engine is not None
            else CorrelationEngine()
        )

        self.fusion_engine = (
            fusion_engine
            if fusion_engine is not None
            else FusionEngine()
        )

        self.reasoning_engine = reasoning_engine



    # =====================================================
    # INVESTIGATION EXECUTION
    # =====================================================

    def investigate(
        self,
        artifacts: list[dict[str, Any]],
        case_id: str | None = None,
    ) -> InvestigationResult:
        """
        Execute full investigation workflow.
        """


        investigation_id = (
            f"INV-{uuid.uuid4().hex[:8].upper()}"
        )


        indicators = self._extract_indicators(
            artifacts
        )


        correlation = (
            self.correlation_engine.correlate(
                indicators,
                case_id=case_id,
            )
        )


        fusion = (
            self._run_fusion(
                case_id,
                correlation,
            )
        )


        reasoning = (
            self._run_reasoning(
                artifacts,
                correlation,
                fusion,
            )
        )


        return InvestigationResult(

            investigation_id=investigation_id,

            case_id=case_id,

            status="completed",

            correlation=(
                correlation.to_dict()
                if hasattr(
                    correlation,
                    "to_dict",
                )
                else correlation
            ),

            fusion=fusion,

            reasoning=reasoning,

            created_at=(
                datetime.utcnow()
                .isoformat()
            ),

        )



    # =====================================================
    # INDICATOR EXTRACTION
    # =====================================================

    def _extract_indicators(
        self,
        artifacts,
    ) -> list[dict[str, Any]]:
        """
        Convert artifacts into correlation inputs.
        """

        indicators = []


        for artifact in artifacts:

            artifact_type = (
                artifact.get(
                    "type"
                )
            )

            value = (
                artifact.get(
                    "value"
                )
            )


            if not value:
                continue


            indicators.append(

                {

                    "type":
                        artifact_type,

                    "value":
                        value,

                    "confidence":
                        artifact.get(
                            "confidence",
                            50,
                        ),

                }

            )


        return indicators



    # =====================================================
    # FUSION
    # =====================================================

    def _run_fusion(
        self,
        case_id,
        correlation,
    ) -> dict[str, Any]:
        """
        Execute threat fusion layer.
        """

        try:

            return self.fusion_engine.fuse(

                {
                    "case_id":
                        case_id,
                },

                {

                    "risk_score":
                        self._risk_score(
                            correlation
                        ),

                    "indicators":
                        correlation.entities
                        if hasattr(
                            correlation,
                            "entities",
                        )
                        else [],

                },

            )


        except Exception as exc:

            return {

                "error":
                    str(exc),

            }



    # =====================================================
    # REASONING
    # =====================================================

    def _run_reasoning(
        self,
        artifacts,
        correlation,
        fusion,
    ):

        if self.reasoning_engine is None:

            return {

                "reasoning_status":
                    "completed",

                "summary":
                    "Investigation completed using intelligence pipeline.",

            }


        try:

            return (
                self.reasoning_engine.analyze(
                    {
                        "artifacts":
                            artifacts,

                        "correlation":
                            correlation,

                        "fusion":
                            fusion,

                    }
                )
            )


        except Exception as exc:

            return {

                "reasoning_status":
                    "failed",

                "error":
                    str(exc),

            }



    # =====================================================
    # RISK
    # =====================================================

    def _risk_score(
        self,
        correlation,
    ) -> int:

        confidence = getattr(
            correlation,
            "confidence",
            0,
        )


        return int(
            confidence * 100
        )