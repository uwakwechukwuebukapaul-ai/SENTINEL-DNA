"""Safe durable investigation job model for the V2.1 foundation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .investigation_lifecycle import InvestigationLifecycleState


def _required(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 256 or any(ord(char) < 32 for char in text):
        raise ValueError(f"{field_name} is invalid")
    return text


@dataclass
class InvestigationJob:
    job_id: str
    tenant_id: str
    case_id: str
    investigation_id: str
    execution_id: str
    trigger_id: str
    idempotency_key: str
    actor_id: str | None
    service_identity: str | None
    correlation_id: str
    state: InvestigationLifecycleState | str = InvestigationLifecycleState.PENDING
    priority: str = "normal"
    attempts: int = 0
    max_attempts: int = 3
    iteration: int = 0
    created_at: str | None = None
    available_at: str | None = None
    claimed_at: str | None = None
    lease_until: str | None = None
    heartbeat_at: str | None = None
    completed_at: str | None = None
    failure_code: str | None = None
    failure_reason: str | None = None
    snapshot_id: str | None = None
    snapshot_digest: str | None = None
    cancel_requested: bool = False
    state_history: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.job_id = _required(self.job_id, "job_id")
        self.tenant_id = _required(self.tenant_id, "tenant_id")
        self.case_id = _required(self.case_id, "case_id")
        self.investigation_id = _required(self.investigation_id, "investigation_id")
        self.execution_id = _required(self.execution_id, "execution_id")
        self.trigger_id = _required(self.trigger_id, "trigger_id")
        self.idempotency_key = _required(self.idempotency_key, "idempotency_key")
        self.correlation_id = _required(self.correlation_id, "correlation_id")
        if not self.actor_id and not self.service_identity:
            raise PermissionError("actor or service identity is required")
        state_value = self.state.value if isinstance(self.state, InvestigationLifecycleState) else str(self.state).upper()
        self.state = InvestigationLifecycleState(state_value)
        if int(self.attempts) < 0 or int(self.iteration) < 0 or int(self.max_attempts) < 1:
            raise ValueError("invalid job attempt or iteration values")
        self.attempts = int(self.attempts)
        self.iteration = int(self.iteration)
        self.max_attempts = int(self.max_attempts)
        self.cancel_requested = bool(self.cancel_requested)

    def identity(self) -> tuple[str, str, str, str]:
        return self.tenant_id, self.case_id, self.investigation_id, self.execution_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "case_id": self.case_id,
            "investigation_id": self.investigation_id,
            "execution_id": self.execution_id,
            "trigger_id": self.trigger_id,
            "idempotency_key": self.idempotency_key,
            "actor_id": self.actor_id,
            "service_identity": self.service_identity,
            "correlation_id": self.correlation_id,
            "state": self.state.value,
            "priority": self.priority,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "iteration": self.iteration,
            "created_at": self.created_at,
            "available_at": self.available_at,
            "claimed_at": self.claimed_at,
            "lease_until": self.lease_until,
            "heartbeat_at": self.heartbeat_at,
            "completed_at": self.completed_at,
            "failure_code": self.failure_code,
            "failure_reason": self.failure_reason,
            "snapshot_id": self.snapshot_id,
            "snapshot_digest": self.snapshot_digest,
            "cancel_requested": self.cancel_requested,
            "state_history": list(self.state_history),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "InvestigationJob":
        return cls(**dict(value))


__all__ = ["InvestigationJob"]
