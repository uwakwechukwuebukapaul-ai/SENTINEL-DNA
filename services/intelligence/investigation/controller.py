"""
Sentinel DNA Investigation Controller

Central controller responsible for
starting and managing autonomous investigations.
"""

from __future__ import annotations

from typing import Any


class InvestigationController:
    """
    High-level AI investigation controller.

    Responsibilities:

    - receive investigation requests
    - validate inputs
    - coordinate execution
    - expose investigation lifecycle
    """


    def __init__(
        self,
        execution_orchestrator=None,
        decision_engine=None,
    ) -> None:

        self.execution_orchestrator = (
            execution_orchestrator
        )

        self.decision_engine = (
            decision_engine
        )

        self.active_investigations: dict[
            str,
            dict[str, Any],
        ] = {}


    def investigate(
        self,
        case_id: str,
        alert: dict[str, Any],
    ) -> Any:
        """
        Start autonomous investigation.
        """


        self.active_investigations[
            case_id
        ] = {
            "status": "started",
            "alert": alert,
        }


        if self.decision_engine:

            decision = (
                self.decision_engine.evaluate(
                    alert
                )
            )

        else:

            decision = {
                "execution": "standard"
            }


        self.active_investigations[
            case_id
        ]["decision"] = decision


        if not self.execution_orchestrator:

            raise RuntimeError(
                "Execution orchestrator unavailable"
            )


        result = (
            self.execution_orchestrator
            .execute_investigation(
                case_id=case_id,
                alert=alert,
            )
        )


        self.active_investigations[
            case_id
        ]["status"] = "completed"


        self.active_investigations[
            case_id
        ]["result"] = result


        return result


    def get_status(
        self,
        case_id: str,
    ) -> dict[str, Any]:

        return (
            self.active_investigations.get(
                case_id,
                {
                    "status": "unknown"
                },
            )
        )


    def clear(
        self,
        case_id: str,
    ) -> None:

        self.active_investigations.pop(
            case_id,
            None,
        )