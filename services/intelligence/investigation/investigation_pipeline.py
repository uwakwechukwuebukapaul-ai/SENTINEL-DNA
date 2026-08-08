"""
Sentinel DNA Investigation Pipeline

Executes autonomous investigation workflow.
"""

from __future__ import annotations

from typing import Any

from .investigation_result import (
    InvestigationResult,
)


class InvestigationPipeline:
    """
    Coordinates investigation execution.
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

                if hasattr(
                    engine,
                    "analyze",
                ):

                    output = engine.analyze(
                        alert
                    )

                elif hasattr(
                    engine,
                    "execute",
                ):

                    output = engine.execute(
                        alert
                    )

                else:

                    continue


                result.add_finding(
                    name,
                    output,
                )


            except Exception as exc:

                result.add_finding(
                    name,
                    {
                        "error": str(exc)
                    },
                )


        return result