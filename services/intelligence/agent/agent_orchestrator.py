"""
Agent Orchestrator.

Coordinates autonomous SOC investigation workflow.

Flow:

Alert
 -> Correlation
 -> Pipeline
 -> Decision
 -> Final Report
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any



class AgentOrchestrator:
    """
    Autonomous investigation workflow coordinator.
    """

    def __init__(
        self,
        correlation_engine=None,
        investigation_pipeline=None,
        decision_engine=None,
    ):

        self.correlation_engine = (
            correlation_engine
        )

        self.investigation_pipeline = (
            investigation_pipeline
        )

        self.decision_engine = (
            decision_engine
        )

        self.history: list[
            dict[str, Any]
        ] = []



    def investigate(
        self,
        alert: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute autonomous investigation.
        """

        case_id = (
            alert.get(
                "case_id",
                "UNKNOWN",
            )
        )


        indicators = (
            alert.get(
                "indicators",
                [],
            )
        )


        techniques = (
            alert.get(
                "techniques",
                [],
            )
        )


        correlation = None

        if self.correlation_engine:

            correlation = (
                self.correlation_engine.correlate(
                    case_id=case_id,
                    indicators=indicators,
                    techniques=techniques,
                )
            )



        pipeline_result = None

        if self.investigation_pipeline:

            pipeline_result = (
                self.investigation_pipeline.execute(
                    alert
                )
            )



        decision = None

        if self.decision_engine:

            decision = (
                self.decision_engine.decide(
                    {
                        "case_id": case_id,

                        "indicators": indicators,

                        "confidence":
                            (
                                correlation.get(
                                    "confidence",
                                    0,
                                )
                                if isinstance(
                                    correlation,
                                    dict,
                                )
                                else 0
                            ),
                    }
                )
            )



        report = {

            "case_id":
                case_id,


            "status":
                "completed",


            "correlation":
                correlation,


            "pipeline":
                pipeline_result,


            "decision":
                decision,


            "generated_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),
        }


        self.history.append(
            report
        )


        return report



    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return investigation history.
        """

        return self.history.copy()



    def clear_history(
        self,
    ) -> None:
        """
        Clear stored investigations.
        """

        self.history.clear()