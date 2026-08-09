"""
Sentinel DNA Workflow State

Tracks investigation orchestration lifecycle.

Enterprise workflow state manager.
"""

from enum import Enum



class WorkflowPhase(Enum):
    """
    Investigation workflow phases.
    """

    CREATED = "created"

    RUNNING = "running"

    INVESTIGATING = "investigating"

    EXECUTING = "executing"

    COMPLETED = "completed"

    FAILED = "failed"




class WorkflowState:
    """
    Runtime state tracker for investigation workflows.

    Provides compatibility with:

    - orchestration engine
    - tests
    - reporting layer
    - future APIs
    """


    def __init__(self):

        self.case_id = None

        self.phase = WorkflowPhase.CREATED

        self.history = []

        self.error = None



    # --------------------------------------------------
    # Workflow lifecycle
    # --------------------------------------------------

    def start(
        self,
        case_id=None,
    ):
        """
        Start investigation workflow.
        """

        self.case_id = case_id

        self.phase = WorkflowPhase.RUNNING

        self.history.append(
            {
                "phase": self.phase.value,
                "case_id": case_id,
            }
        )



    def advance(
        self,
        phase,
    ):
        """
        Move workflow into another phase.
        """

        self.phase = phase

        self.history.append(
            {
                "phase": self.phase.value,
            }
        )



    def complete(
        self,
        result=None,
    ):
        """
        Mark workflow completed.
        """

        self.phase = WorkflowPhase.COMPLETED

        self.history.append(
            {
                "phase": self.phase.value,
                "result": result,
            }
        )



    def fail(
        self,
        error,
    ):
        """
        Mark workflow failed.
        """

        self.phase = WorkflowPhase.FAILED

        self.error = error

        self.history.append(
            {
                "phase": self.phase.value,
                "error": str(error),
            }
        )



    # --------------------------------------------------
    # Compatibility API
    # --------------------------------------------------

    def status(self):
        """
        Return current workflow status.

        Compatibility:

        Tests:
            state.status()

        Runtime:
            state.status()
        """

        return self.phase.value



    def is_completed(self):

        return (
            self.phase
            ==
            WorkflowPhase.COMPLETED
        )



    def is_failed(self):

        return (
            self.phase
            ==
            WorkflowPhase.FAILED
        )



    # --------------------------------------------------
    # Serialization
    # --------------------------------------------------

    def to_dict(self):

        return {

            "case_id":
                self.case_id,

            "phase":
                self.phase.value,

            "status":
                self.phase.value,

            "error":
                self.error,

            "history":
                self.history,

        }