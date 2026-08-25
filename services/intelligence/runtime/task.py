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
from enum import Enum

from .task_status import TaskStatus
from .task_priority import TaskPriority


class RuntimeTaskState(str, Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"
    BLOCKED = "BLOCKED"


@dataclass
class Task:
    """
    Runtime execution task.
    """

    capability: str

    payload: dict[str, Any]

    priority: TaskPriority = TaskPriority.NORMAL

    status: TaskStatus = TaskStatus.PENDING

    # Product-level execution status is distinct from the legacy lifecycle
    # status above.  The lifecycle remains backward compatible while callers
    # can now distinguish unavailable, blocked, and failed execution.
    execution_status: str = "pending"

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

    # Durable-execution foundation. These fields are additive and allow a
    # future worker to claim the same task without changing the contract.
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)
    attempt: int = 0

    # V2.1 lineage fields are optional so existing synchronous callers retain
    # the current task construction and execution contract.
    parent_task_id: str | None = None
    job_id: str | None = None
    tenant_id: str | None = None
    case_id: str | None = None
    investigation_id: str | None = None
    objective: str | None = None
    required_evidence: list[str] = field(default_factory=list)
    iteration: int = 0
    authorization_reference: str | None = None
    budget_cost: float = 0.0
    available_at: datetime | None = None
    deadline_at: datetime | None = None
    cancelled_at: datetime | None = None


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
        self.execution_status = "queued"


    def start(self) -> None:
        """
        Start execution.
        """

        self.status = TaskStatus.RUNNING
        self.execution_status = "running"
        self.attempt += 1

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
        self.execution_status = "success"

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
        self.execution_status = "failed"
        self.completed_at = datetime.now(timezone.utc)

    def mark_unavailable(self, error: str = "Capability unavailable") -> None:
        self.error = error
        self.status = TaskStatus.FAILED
        self.execution_status = "unavailable"
        self.completed_at = datetime.now(timezone.utc)

    def mark_blocked(self, error: str = "Task execution blocked") -> None:
        self.error = error
        self.status = TaskStatus.FAILED
        self.execution_status = "blocked"
        self.completed_at = datetime.now(timezone.utc)

    @property
    def execution_state(self) -> RuntimeTaskState:
        return RuntimeTaskState(self.execution_status.upper())


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
            "execution_id": self.execution_id,
            "capability": self.capability,
            "priority": self.priority.value,
            "status": self.status.value,
            "execution_status": self.execution_status,
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
            "execution_state": self.execution_state.value,
            "metadata": dict(self.metadata),
            "attempt": self.attempt,
            "parent_task_id": self.parent_task_id,
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "case_id": self.case_id,
            "investigation_id": self.investigation_id,
            "objective": self.objective,
            "required_evidence": list(self.required_evidence),
            "iteration": self.iteration,
            "authorization_reference": self.authorization_reference,
            "budget_cost": self.budget_cost,
            "available_at": self.available_at.isoformat() if self.available_at else None,
            "deadline_at": self.deadline_at.isoformat() if self.deadline_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
        }
