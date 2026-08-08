"""
Sentinel DNA Runtime Task Status

Central task lifecycle state definitions.

Used by:
- Runtime Engine
- Scheduler
- Workers
- Executors
- Workflow execution

Keeps task state management consistent
across the intelligence runtime layer.
"""

from __future__ import annotations

from enum import Enum


class TaskStatus(str, Enum):
    """
    Enterprise runtime task lifecycle states.
    """

    PENDING = "pending"

    QUEUED = "queued"

    RUNNING = "running"

    COMPLETED = "completed"

    FAILED = "failed"


    def is_terminal(self) -> bool:
        """
        Check whether task execution
        has reached a final state.
        """

        return self in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
        }


    def is_active(self) -> bool:
        """
        Check whether task is currently
        executing.
        """

        return self in {
            TaskStatus.QUEUED,
            TaskStatus.RUNNING,
        }


    def can_execute(self) -> bool:
        """
        Determine if task can enter execution.
        """

        return self in {
            TaskStatus.PENDING,
            TaskStatus.QUEUED,
        }


    def __str__(self) -> str:
        return self.value