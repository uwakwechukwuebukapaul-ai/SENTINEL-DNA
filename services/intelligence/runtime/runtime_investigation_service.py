"""
Runtime Investigation Service

Coordinates investigation execution.

Supports:
- Runtime context creation
- Investigation orchestration
- Intelligence execution
- Result generation
"""

from __future__ import annotations

from typing import Any

from services.intelligence.runtime.runtime_investigation_context import (
    RuntimeInvestigationContext,
)

from services.intelligence.runtime.runtime_investigation_result import (
    RuntimeInvestigationResult,
)


class RuntimeInvestigationService:
    """
    Runtime investigation execution boundary.
    """

    def __init__(
        self,
        intelligence_service=None,
        investigation_orchestrator=None,
    ) -> None:

        self.intelligence_service = (
            intelligence_service
        )

        self.investigation_orchestrator = (
            investigation_orchestrator
        )


    # =====================================================
    # MAIN INVESTIGATION ENTRY
    # =====================================================

    def investigate(
        self,
        investigation_id: str,
        signals: list[dict[str, Any]],
    ) -> RuntimeInvestigationResult:
        """
        Execute investigation workflow.
        """

        context = RuntimeInvestigationContext(

            investigation_id=(
                investigation_id
            ),

            signals=(
                signals
            ),

        )


        context.add_event(
            {
                "stage": "started",

                "signal_count": len(signals),
            }
        )


        intelligence = (
            self._execute_investigation(
                investigation_id,
                signals,
            )
        )


        context.intelligence_result = (
            intelligence
        )


        context.add_event(
            {
                "stage":
                    "investigation_completed",
            }
        )


        return self._build_result(
            context
        )


    # =====================================================
    # EXECUTION ROUTER
    # =====================================================

    def _execute_investigation(
        self,
        investigation_id: str,
        signals: list[dict[str, Any]],
    ):
        """
        Prefer orchestrated execution.

        Falls back to intelligence service
        for compatibility.
        """

        if self.investigation_orchestrator:

            return (
                self.investigation_orchestrator.investigate(
                    investigation_id,
                    signals,
                )
            )


        if self.intelligence_service:

            return (
                self.intelligence_service.investigate(
                    signals,
                    case_id=investigation_id,
                )
            )


        return {

            "risk":
                "unknown",

            "confidence":
                0.0,

            "findings":
                [],

        }


    # =====================================================
    # RESULT BUILDER
    # =====================================================

    def _build_result(
        self,
        context: RuntimeInvestigationContext,
    ) -> RuntimeInvestigationResult:
        """
        Convert runtime context into result.
        """

        intelligence = (
            context.intelligence_result
        )


        return RuntimeInvestigationResult(

            success=True,

            investigation_id=(
                context.investigation_id
            ),

            risk=(
                self._extract_value(
                    intelligence,
                    "risk",
                    "unknown",
                )
            ),

            confidence=(
                self._extract_value(
                    intelligence,
                    "confidence",
                    0.0,
                )
            ),

            intelligence=(
                intelligence
            ),

            timeline=(
                context.timeline
            ),

            metadata={

                "signals":
                    len(context.signals),

                "orchestrated":
                    self.investigation_orchestrator
                    is not None,

            },

        )


    # =====================================================
    # SAFE VALUE EXTRACTION
    # =====================================================

    @staticmethod
    def _extract_value(
        source,
        key,
        default,
    ):

        if isinstance(
            source,
            dict,
        ):

            return source.get(
                key,
                default,
            )


        return getattr(
            source,
            key,
            default,
        )