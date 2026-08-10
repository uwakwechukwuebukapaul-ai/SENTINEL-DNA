"""
Sentinel DNA Investigation State Manager.

Controls investigation lifecycle state.
"""

from __future__ import annotations


class InvestigationStateManager:
    """
    Investigation state controller.
    """


    VALID_STATES = [

        "created",

        "running",

        "completed",

        "failed",

    ]



    def __init__(self):

        self.states: dict[str, str] = {}



    def create(
        self,
        investigation_id: str,
    ):

        self.states[investigation_id] = "created"


        return "created"



    def update(
        self,
        investigation_id: str,
        state: str,
    ):

        if state not in self.VALID_STATES:

            raise ValueError(
                f"Invalid state: {state}"
            )


        self.states[investigation_id] = state


        return state



    def get(
        self,
        investigation_id: str,
    ):

        return self.states.get(
            investigation_id,
            "created",
        )



    def is_completed(
        self,
        investigation_id: str,
    ) -> bool:

        return (
            self.get(investigation_id)
            ==
            "completed"
        )