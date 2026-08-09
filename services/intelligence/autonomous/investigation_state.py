"""
Investigation State Management

Tracks autonomous investigation lifecycle.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone



class InvestigationPhase(str, Enum):
    """
    Autonomous investigation phases.
    """

    INITIALIZED = "initialized"

    RUNNING = "running"

    ANALYZING = "analyzing"

    DECIDING = "deciding"

    EXECUTING = "executing"

    COMPLETED = "completed"

    FAILED = "failed"



@dataclass
class InvestigationState:
    """
    Runtime investigation state.
    """

    phase: InvestigationPhase = (
        InvestigationPhase.INITIALIZED
    )

    error: str | None = None

    created_at: str = field(
        default_factory=lambda:
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    updated_at: str | None = None



    @property
    def status(self):

        return self.phase.value



    def start(self):

        self.phase = (
            InvestigationPhase.RUNNING
        )

        self._touch()

        return self



    def analyze(self):

        self.phase = (
            InvestigationPhase.ANALYZING
        )

        self._touch()

        return self



    def decide(self):

        self.phase = (
            InvestigationPhase.DECIDING
        )

        self._touch()

        return self



    def execute(self):

        self.phase = (
            InvestigationPhase.EXECUTING
        )

        self._touch()

        return self



    def complete(self):

        self.phase = (
            InvestigationPhase.COMPLETED
        )

        self._touch()

        return self



    def fail(
        self,
        error: str,
    ):

        self.phase = (
            InvestigationPhase.FAILED
        )

        self.error = error

        self._touch()

        return self



    def _touch(self):

        self.updated_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )



    def to_dict(self):

        return {

            "phase":
                self.phase.value,

            "status":
                self.status,

            "error":
                self.error,

            "created_at":
                self.created_at,

            "updated_at":
                self.updated_at,
        }