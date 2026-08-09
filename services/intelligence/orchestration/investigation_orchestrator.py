"""
Investigation Orchestrator

Coordinates autonomous investigation execution.

Responsibilities:
- manage investigation lifecycle
- coordinate investigation agents
- maintain execution history
- track execution state
"""


from typing import Any

from .execution_state import ExecutionState


class InvestigationOrchestrator:
    """
    Main investigation workflow coordinator.
    """


    def __init__(self):

        self.agents: dict[str, Any] = {}

        self.history: list[dict[str, Any]] = []



    def register_agent(
        self,
        agent: Any,
    ) -> None:
        """
        Register investigation agent.
        """

        name = getattr(
            agent,
            "name",
            agent.__class__.__name__,
        )


        self.agents[name] = agent



    def execute(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute investigation workflow.
        """

        state = ExecutionState(
            investigation_id=
                investigation.get(
                    "id",
                    "UNKNOWN",
                )
        )


        state.start()



        findings = []


        for agent in self.agents.values():

            if hasattr(
                agent,
                "investigate",
            ):

                result = agent.investigate(
                    investigation
                )


                if "findings" in result:
                    findings.extend(
                        result["findings"]
                    )



        state.complete()



        result = {

            "investigation_id":
                investigation.get(
                    "id",
                    "UNKNOWN",
                ),


            "findings":
                findings,


            "state":
                state.to_dict(),

        }



        self.history.append(
            result
        )


        return result



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
        Clear execution history.
        """

        self.history.clear()