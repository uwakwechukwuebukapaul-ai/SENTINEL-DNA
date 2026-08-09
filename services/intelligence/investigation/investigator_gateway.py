"""
Sentinel DNA - AI Investigator Gateway

Enterprise execution entry point for autonomous investigations.

Responsibilities:

- Accept investigation requests
- Validate investigation payloads
- Connect scenarios with orchestration
- Execute investigation lifecycle
- Normalize investigation results

This layer prevents direct coupling between
scenario execution and internal orchestration engines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid



class InvestigationGatewayError(Exception):
    """
    Raised when investigator gateway execution fails.
    """



class InvestigatorGateway:
    """
    Enterprise gateway for AI investigation execution.

    Acts as the public service boundary between:

    - SOC alerts
    - scenario simulations
    - orchestration engines
    - reporting systems
    """


    def __init__(
        self,
        orchestrator=None,
        pipeline=None,
        reporter=None,
    ):

        self.orchestrator = orchestrator
        self.pipeline = pipeline
        self.reporter = reporter



    def start_investigation(
        self,
        alert: Dict[str, Any],
        scenario: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Start autonomous investigation workflow.
        """

        investigation_id = self._generate_id()


        request = {
            "investigation_id": investigation_id,
            "created_at": self._timestamp(),
            "scenario": scenario,
            "alert": alert,
            "metadata": metadata or {},
        }


        try:

            context = self._create_context(
                request
            )


            orchestration_result = (
                self._execute_orchestrator(
                    context
                )
            )


            report = (
                self._generate_report(
                    orchestration_result
                )
            )


            return {
                "status": "completed",
                "investigation_id": investigation_id,
                "result": orchestration_result,
                "report": report,
            }


        except Exception as exc:

            return {
                "status": "failed",
                "investigation_id": investigation_id,
                "error": str(exc),
            }



    def _create_context(
        self,
        request: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build investigation execution context.
        """

        return {
            "investigation": request,
            "started": self._timestamp(),
            "phase": "initialization",
        }



    def _execute_orchestrator(
        self,
        context: Dict[str, Any],
    ) -> Any:
        """
        Execute investigation engine.

        Supports:

        - run(context)
        - execute(context)
        - investigate(case_id, alert)
        """

        if not self.orchestrator:

            return {
                "phase": "simulation",
                "message": "No orchestrator configured",
                "context": context,
            }



        if hasattr(
            self.orchestrator,
            "run"
        ):

            return self.orchestrator.run(
                context
            )



        if hasattr(
            self.orchestrator,
            "execute"
        ):

            return self.orchestrator.execute(
                context
            )



        if hasattr(
            self.orchestrator,
            "investigate"
        ):

            investigation = (
                context["investigation"]
            )


            return self.orchestrator.investigate(
                case_id=(
                    investigation[
                        "investigation_id"
                    ]
                ),
                alert=(
                    investigation.get(
                        "alert",
                        {}
                    )
                ),
            )



        raise InvestigationGatewayError(
            "Unsupported orchestrator interface"
        )



    def _generate_report(
        self,
        result: Any,
    ) -> Any:
        """
        Generate investigation report.
        """

        if not self.reporter:

            return {
                "summary":
                    "Investigation completed"
            }



        if hasattr(
            self.reporter,
            "generate"
        ):

            return self.reporter.generate(
                result
            )



        return result



    @staticmethod
    def _generate_id() -> str:

        return (
            "INV-"
            + datetime.now()
            .strftime("%Y%m%d")
            + "-"
            + uuid.uuid4()
            .hex[:6]
            .upper()
        )



    @staticmethod
    def _timestamp() -> str:

        return datetime.now(
            timezone.utc
        ).isoformat()