"""
Investigation Pipeline

High-level autonomous investigation workflow.

Connects:

- Investigator Agent
- Analyzer compatibility layer
- Agent Orchestrator
- Investigation Memory
- Correlation Engine
- Response Orchestrator
"""

from __future__ import annotations

from typing import Any


class InvestigationPipeline:
    """
    Autonomous investigation execution pipeline.
    """

    def __init__(
        self,
        investigator=None,
        orchestrator=None,
        memory=None,
        correlation_engine=None,
        response_orchestrator=None,
        analyzer=None,
    ):
        """
        Initialize investigation pipeline.

        Supports both:

        Production:
            investigator=InvestigatorAgent()

        Testing/API:
            analyzer=Analyzer()
        """

        self.investigator = (
            investigator
            or analyzer
        )

        self.analyzer = (
            analyzer
            or investigator
        )

        self.orchestrator = (
            orchestrator
        )

        self.memory = (
            memory
        )

        self.correlation_engine = (
            correlation_engine
        )

        self.response_orchestrator = (
            response_orchestrator
        )

        self.history: list[
            dict[str, Any]
        ] = []


    def ingest(
        self,
        artifacts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Accept investigation artifacts.
        """

        return {
            "status": "accepted",
            "artifact_count": len(
                artifacts
            ),
            "artifacts": artifacts,
        }


    def run(
        self,
        artifacts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Compatibility execution entrypoint.

        Used by:
        - API layer
        - tests
        - lightweight execution flows
        """

        analysis = {}

        if self.analyzer and hasattr(
            self.analyzer,
            "analyze",
        ):
            analysis = (
                self.analyzer.analyze(
                    artifacts
                )
            )

        elif self.investigator and hasattr(
            self.investigator,
            "investigate",
        ):
            analysis = (
                self.investigator.investigate(
                    artifacts
                )
            )


        execution = {}

        if self.orchestrator and hasattr(
            self.orchestrator,
            "execute",
        ):
            execution = (
                self.orchestrator.execute(
                    artifacts
                )
            )


        result = {
            "status": "completed",

            "analysis": analysis,

            "execution": execution,
        }


        self.history.append(
            result
        )


        return result


    def execute(
        self,
        artifacts: list[dict[str, Any]],
        case_id: str = "AUTO-CASE",
    ) -> dict[str, Any]:
        """
        Full autonomous investigation execution.
        """

        ingestion = self.ingest(
            artifacts
        )


        analysis = self.run(
            artifacts
        )


        memory_result = (
            self._store_memory(
                case_id,
                artifacts,
            )
        )


        correlation_result = (
            self._run_correlation(
                case_id,
                artifacts,
            )
        )


        response_result = (
            self._run_response(
                correlation_result
            )
        )


        report = {
            "status": "completed",

            "case_id": case_id,

            "ingestion": ingestion,

            "analysis": analysis,

            "memory": memory_result,

            "correlation": correlation_result,

            "response": response_result,
        }


        self.history.append(
            report
        )


        return report


    def _store_memory(
        self,
        case_id,
        artifacts,
    ):
        """
        Store investigation memory.
        """

        if self.memory is None:
            return {
                "status": "skipped",
            }


        if hasattr(
            self.memory,
            "store",
        ):
            return self.memory.store(
                case_id,
                artifacts,
            )


        return {
            "status": "completed",
        }


    def _run_correlation(
        self,
        case_id,
        artifacts,
    ):
        """
        Execute intelligence correlation.
        """

        if self.correlation_engine is None:
            return {
                "status": "skipped",
            }


        indicators = [
            item
            for item in artifacts
            if item.get("type")
            == "ioc"
        ]


        techniques = [
            item
            for item in artifacts
            if item.get("type")
            == "technique"
        ]


        return (
            self.correlation_engine.correlate(
                case_id=case_id,
                indicators=indicators,
                techniques=techniques,
            )
        )


    def _run_response(
        self,
        correlation,
    ):
        """
        Execute response actions.
        """

        if self.response_orchestrator is None:
            return {
                "status": "skipped",
            }


        if hasattr(
            self.response_orchestrator,
            "execute",
        ):
            return (
                self.response_orchestrator.execute(
                    correlation
                )
            )


        return {
            "status": "completed",
        }


    def get_history(
        self,
    ):
        """
        Return pipeline execution history.
        """

        return self.history.copy()