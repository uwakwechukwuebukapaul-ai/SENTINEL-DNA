"""
Sentinel DNA Runtime Task

Enterprise execution unit.

Responsibilities:

- Store runtime workload
- Track lifecycle
- Manage retries
- Serialize task state
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from .task_status import TaskStatus
from .task_priority import TaskPriority


@dataclass
class Task:
    """
    Runtime execution task.
    """

    capability: str

    payload: dict[str, Any]

    priority: TaskPriority = TaskPriority.NORMAL

    status: TaskStatus = TaskStatus.PENDING

    result: Any = None

    error: str | None = None

    task_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    retry_count: int = 0

    max_retries: int = 3

    created_at: datetime = field(
        default_factory=lambda:
            datetime.now(timezone.utc)
    )

    started_at: datetime | None = None

    completed_at: datetime | None = None


    @property
    def retries(self) -> int:
        """
        Compatibility alias.

        Exposes retry count using
        legacy runtime naming.
        """

        return self.retry_count


    @property
    def can_retry(self) -> bool:
        """
        Check retry availability.
        """

        return (
            self.retry_count < self.max_retries
        )


    def queue(self) -> None:
        """
        Mark task queued.
        """

        self.status = TaskStatus.QUEUED


    def start(self) -> None:
        """
        Start execution.
        """

        self.status = TaskStatus.RUNNING

        self.started_at = datetime.now(
            timezone.utc
        )


    def complete(
        self,
        result: Any = None,
    ) -> None:
        """
        Complete task.
        """

        self.result = result

        self.status = TaskStatus.COMPLETED

        self.completed_at = datetime.now(
            timezone.utc
        )


    def fail(
        self,
        error: str = "Unknown error",
    ) -> None:
        """
        Mark task failed.
        """

        self.error = error

        self.status = TaskStatus.FAILED


    def increment_retry(self) -> None:
        """
        Increment retry counter.
        """

        self.retry_count += 1

        self.status = TaskStatus.PENDING


    def to_dict(self) -> dict[str, Any]:
        """
        Serialize task.
        """

        return {
            "task_id": self.task_id,
            "capability": self.capability,
            "priority": self.priority.value,
            "status": self.status.value,
            "payload": self.payload,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
            "started_at":
                self.started_at.isoformat()
                if self.started_at
                else None,
            "completed_at":
                self.completed_at.isoformat()
                if self.completed_at
                else None,
        }