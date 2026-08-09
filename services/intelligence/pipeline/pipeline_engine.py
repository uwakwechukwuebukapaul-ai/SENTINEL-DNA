"""
Pipeline Engine

Coordinates investigation execution,
intelligence integration, reporting,
and execution history.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class PipelineEngine:
    """
    Investigation pipeline execution engine.

    Responsibilities:
    - Accept investigation artifacts
    - Execute intelligence integration
    - Generate reports
    - Maintain execution history
    """

    def __init__(
        self,
        integrator=None,
        reporter=None,
    ):
        self.integrator = integrator
        self.reporter = reporter

        self.history: list[dict[str, Any]] = []


    def execute(
        self,
        artifacts: list[dict[str, Any]] | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute investigation pipeline.
        """

        if artifacts is None:
            artifacts = []


        if isinstance(
            artifacts,
            dict,
        ):
            artifacts = [artifacts]


        intelligence_result = None


        if self.integrator:

            if hasattr(
                self.integrator,
                "analyze",
            ):
                intelligence_result = (
                    self.integrator.analyze(
                        artifacts
                    )
                )

            elif hasattr(
                self.integrator,
                "process",
            ):
                intelligence_result = (
                    self.integrator.process(
                        artifacts
                    )
                )

            elif hasattr(
                self.integrator,
                "execute",
            ):
                intelligence_result = (
                    self.integrator.execute(
                        artifacts
                    )
                )


        report = None


        if self.reporter:

            if hasattr(
                self.reporter,
                "generate",
            ):
                report = (
                    self.reporter.generate(
                        intelligence_result
                    )
                )

            elif hasattr(
                self.reporter,
                "create",
            ):
                report = (
                    self.reporter.create(
                        intelligence_result
                    )
                )


        result = {

            "status":
                "completed",

            "artifacts":
                artifacts,

            "intelligence":
                intelligence_result,

            "report":
                report,

            "timestamp":
                datetime.now(
                    timezone.utc
                ).isoformat(),
        }


        self.history.append(
            result
        )


        return result



    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return execution history.
        """

        return self.history.copy()



    def clear_history(
        self,
    ) -> None:
        """
        Clear execution history.
        """

        self.history.clear()