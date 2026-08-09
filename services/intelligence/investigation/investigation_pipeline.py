"""
Sentinel DNA Investigation Pipeline

Executes intelligence-driven investigation workflow.
"""

from __future__ import annotations

from typing import Any

from .investigation_result import (
    InvestigationResult,
)


class InvestigationPipeline:
    """
    Coordinates investigation intelligence engines.
    """

    def __init__(
        self,
        engines: dict[str, Any] | None = None,
    ) -> None:

        self.engines = engines or {}


    def register_engine(
        self,
        name: str,
        engine: Any,
    ) -> None:

        self.engines[name] = engine


    def execute(
        self,
        case_id: str,
        alert: dict[str, Any],
    ) -> InvestigationResult:

        result = InvestigationResult(
            case_id=case_id
        )


        for name, engine in self.engines.items():

            try:

                output = None


                if hasattr(
                    engine,
                    "analyze"
                ):
                    output = engine.analyze(
                        alert
                    )


                elif hasattr(
                    engine,
                    "execute"
                ):
                    output = engine.execute(
                        alert
                    )


                if output is None:
                    continue


                result.add_finding(
                    name,
                    output,
                )


                if name == "mitre":

                    techniques = (
                        output.get(
                            "techniques",
                            []
                        )
                        if isinstance(output, dict)
                        else []
                    )

                    for technique in techniques:
                        result.add_mitre(
                            technique
                        )


                if name == "risk":

                    if isinstance(output, dict):

                        result.set_risk(
                            output.get(
                                "score",
                                0
                            ),
                            output.get(
                                "confidence",
                                0.0
                            ),
                        )


                if name == "recommendation":

                    recommendations = (
                        output.get(
                            "recommendations",
                            []
                        )
                        if isinstance(output, dict)
                        else []
                    )

                    for item in recommendations:
                        result.add_recommendation(
                            item
                        )


            except Exception as exc:

                result.add_finding(
                    name,
                    {
                        "error": str(exc)
                    },
                )


        return result