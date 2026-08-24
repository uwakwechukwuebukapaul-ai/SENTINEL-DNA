"""Durable investigation lifecycle contract for the V2.1 foundation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class InvestigationLifecycleState(str, Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_FOR_EVIDENCE = "WAITING_FOR_EVIDENCE"
    FOLLOW_UP = "FOLLOW_UP"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    ESCALATED = "ESCALATED"
    BLOCKED = "BLOCKED"


TERMINAL_STATES = frozenset({
    InvestigationLifecycleState.COMPLETED,
    InvestigationLifecycleState.FAILED,
    InvestigationLifecycleState.TIMED_OUT,
    InvestigationLifecycleState.CANCELLED,
    InvestigationLifecycleState.ESCALATED,
    InvestigationLifecycleState.BLOCKED,
})


_ALLOWED_TRANSITIONS = {
    None: frozenset({InvestigationLifecycleState.PENDING}),
    InvestigationLifecycleState.PENDING: frozenset({
        InvestigationLifecycleState.QUEUED,
        InvestigationLifecycleState.BLOCKED,
        InvestigationLifecycleState.CANCELLED,
    }),
    InvestigationLifecycleState.QUEUED: frozenset({
        InvestigationLifecycleState.RUNNING,
        InvestigationLifecycleState.CANCELLED,
        InvestigationLifecycleState.BLOCKED,
    }),
    InvestigationLifecycleState.RUNNING: frozenset({
        InvestigationLifecycleState.QUEUED,
        InvestigationLifecycleState.WAITING_FOR_EVIDENCE,
        InvestigationLifecycleState.FOLLOW_UP,
        InvestigationLifecycleState.COMPLETED,
        InvestigationLifecycleState.FAILED,
        InvestigationLifecycleState.TIMED_OUT,
        InvestigationLifecycleState.CANCELLED,
        InvestigationLifecycleState.ESCALATED,
        InvestigationLifecycleState.BLOCKED,
    }),
    InvestigationLifecycleState.WAITING_FOR_EVIDENCE: frozenset({
        InvestigationLifecycleState.FOLLOW_UP,
        InvestigationLifecycleState.ESCALATED,
        InvestigationLifecycleState.FAILED,
        InvestigationLifecycleState.TIMED_OUT,
        InvestigationLifecycleState.CANCELLED,
    }),
    InvestigationLifecycleState.FOLLOW_UP: frozenset({
        InvestigationLifecycleState.QUEUED,
        InvestigationLifecycleState.ESCALATED,
        InvestigationLifecycleState.BLOCKED,
    }),
}


class InvalidInvestigationTransition(ValueError):
    """Raised when a durable investigation changes state illegally."""


def _state(value: InvestigationLifecycleState | str | None) -> InvestigationLifecycleState | None:
    if value is None:
        return None
    try:
        return value if isinstance(value, InvestigationLifecycleState) else InvestigationLifecycleState(str(value).upper())
    except ValueError as exc:
        raise InvalidInvestigationTransition(f"unknown investigation state: {value}") from exc


def validate_transition(
    previous: InvestigationLifecycleState | str | None,
    next_state: InvestigationLifecycleState | str,
    *,
    recovery_authorized: bool = False,
) -> None:
    previous_state = _state(previous)
    target_state = _state(next_state)
    if target_state is None or target_state not in _ALLOWED_TRANSITIONS.get(previous_state, frozenset()):
        raise InvalidInvestigationTransition(
            f"illegal investigation transition: {previous_state} -> {target_state}"
        )
    if previous_state == InvestigationLifecycleState.RUNNING and target_state == InvestigationLifecycleState.QUEUED and not recovery_authorized:
        raise InvalidInvestigationTransition("RUNNING -> QUEUED requires recovery or retry authorization")


@dataclass(frozen=True)
class LifecycleTransition:
    previous_state: str | None
    next_state: str
    timestamp: str
    tenant_id: str
    case_id: str
    investigation_id: str
    execution_id: str
    job_id: str
    actor_id: str | None
    service_identity: str | None
    correlation_id: str | None
    reason: str
    attempt: int
    iteration: int

    @classmethod
    def create(
        cls,
        *,
        previous_state: InvestigationLifecycleState | str | None,
        next_state: InvestigationLifecycleState | str,
        tenant_id: str,
        case_id: str,
        investigation_id: str,
        execution_id: str,
        job_id: str,
        actor_id: str | None,
        service_identity: str | None,
        correlation_id: str | None,
        reason: str,
        attempt: int,
        iteration: int,
        recovery_authorized: bool = False,
    ) -> "LifecycleTransition":
        validate_transition(previous_state, next_state, recovery_authorized=recovery_authorized)
        identity = (tenant_id, case_id, investigation_id, execution_id, job_id)
        if any(not isinstance(item, str) or not item.strip() for item in identity):
            raise ValueError("complete investigation identity is required")
        if not actor_id and not service_identity:
            raise PermissionError("actor or service identity is required")
        if int(attempt) < 0 or int(iteration) < 0:
            raise ValueError("attempt and iteration must be non-negative")
        return cls(
            previous_state=_state(previous_state).value if _state(previous_state) else None,
            next_state=_state(next_state).value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tenant_id=tenant_id,
            case_id=case_id,
            investigation_id=investigation_id,
            execution_id=execution_id,
            job_id=job_id,
            actor_id=actor_id,
            service_identity=service_identity,
            correlation_id=correlation_id,
            reason=str(reason or "state transition")[:256],
            attempt=int(attempt),
            iteration=int(iteration),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "previous_state": self.previous_state,
            "next_state": self.next_state,
            "timestamp": self.timestamp,
            "tenant_id": self.tenant_id,
            "case_id": self.case_id,
            "investigation_id": self.investigation_id,
            "execution_id": self.execution_id,
            "job_id": self.job_id,
            "actor_id": self.actor_id,
            "service_identity": self.service_identity,
            "correlation_id": self.correlation_id,
            "reason": self.reason,
            "attempt": self.attempt,
            "iteration": self.iteration,
        }


__all__ = [
    "InvestigationLifecycleState",
    "LifecycleTransition",
    "InvalidInvestigationTransition",
    "TERMINAL_STATES",
    "validate_transition",
]
