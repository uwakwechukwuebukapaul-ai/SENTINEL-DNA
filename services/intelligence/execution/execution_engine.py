"""
Execution Engine

Provides:
- Investigation action planning
- Intelligence task execution
- Execution history tracking
- SOC workflow integration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any



@dataclass
class ExecutionResult:
    """
    Represents execution output.
    """

    case_id: str = ""

    status: str = "completed"

    actions: list[dict[str, Any]] = field(
        default_factory=list
    )

    executed: list[str] = field(
        default_factory=list
    )

    recommendations: list[str] = field(
        default_factory=list
    )

    created_at: str = field(
        default_factory=lambda:
        datetime.now(
            timezone.utc
        ).isoformat()
    )


    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Serialize execution result.
        """

        return {

            "case_id":
                self.case_id,

            "status":
                self.status,

            "actions":
                self.actions,

            "executed":
                self.executed,

            "recommendations":
                self.recommendations,

            "created_at":
                self.created_at,
        }



class ExecutionEngine:
    """
    Autonomous SOC execution engine.

    Converts investigation decisions into
    structured execution workflows.
    """


    def __init__(
        self,
        dispatcher=None,
    ):

        self.dispatcher = dispatcher

        self.history = []



    def execute(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute investigation workflow.
        """

        if investigation is None:
            investigation = {}


        case_id = (
            investigation.get(
                "case_id",
                "",
            )
        )


        decision = (
            investigation.get(
                "decision",
                {},
            )
        )


        actions = (
            self._build_actions(
                investigation
            )
        )


        executed = []


        for action in actions:

            result = (
                self._execute_action(
                    action
                )
            )

            executed.append(
                result
            )


        recommendations = (
            self._generate_recommendations(
                decision
            )
        )


        execution = ExecutionResult(

            case_id=case_id,

            actions=actions,

            executed=executed,

            recommendations=
                recommendations,
        )


        output = execution.to_dict()


        self.history.append(
            output
        )


        return output



    def _build_actions(
        self,
        investigation,
    ):
        """
        Build SOC execution plan.
        """

        correlation = (
            investigation.get(
                "correlation",
                {},
            )
        )


        actions = []


        indicators = (
            correlation.get(
                "indicators",
                [],
            )
        )


        for indicator in indicators:

            actions.append(
                {
                    "type":
                        "ioc_enrichment",

                    "target":
                        indicator,
                }
            )


        decision = (
            investigation.get(
                "decision",
                {},
            )
        )


        if (
            decision.get(
                "decision"
            )
            ==
            "respond"
        ):

            actions.append(
                {
                    "type":
                        "containment",

                    "target":
                        "affected_asset",
                }
            )


        return actions



    def _execute_action(
        self,
        action,
    ):
        """
        Execute single action.

        Dispatcher support allows future
        SOAR integration.
        """

        if self.dispatcher:

            return self.dispatcher.execute(
                action
            )


        return (
            f"{action['type']}:"
            f"{action.get('target')}"
        )



    def _generate_recommendations(
        self,
        decision,
    ):

        response = (
            decision.get(
                "decision",
                "monitor",
            )
            if isinstance(
                decision,
                dict,
            )
            else "monitor"
        )


        if response == "respond":

            return [
                "Initiate incident response workflow",
                "Collect additional forensic evidence",
                "Review affected assets",
            ]


        return [
            "Continue monitoring activity",
            "Review threat intelligence context",
        ]



    def get_history(
        self,
    ):

        return list(
            self.history
        )



    def clear_history(
        self,
    ):

        self.history.clear()