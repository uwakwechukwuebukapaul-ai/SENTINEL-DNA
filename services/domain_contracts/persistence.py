"""Persistence boundary adapters for canonical contracts.

This module owns translation only. The existing subsystem repository remains
the source of truth and the canonical contracts remain storage-independent.
"""

from __future__ import annotations

from typing import Protocol

from .models import Outcome, OutcomeStatus


class OutcomeRepository(Protocol):
    def save_outcome(self, outcome: object) -> object: ...

    def list_outcomes(self, tenant_id: str) -> list[object]: ...


class OutcomePersistenceBoundary:
    """Translate canonical outcomes to and from the existing outcome store."""

    def __init__(self, repository: OutcomeRepository) -> None:
        if repository is None:
            raise ValueError("repository_required")
        self.repository = repository

    def save(self, outcome: Outcome) -> Outcome:
        if not isinstance(outcome, Outcome):
            raise TypeError("outcome_required")
        from services.intelligence.outcome_learning import OutcomeRecord

        self.repository.save_outcome(OutcomeRecord(
            tenant_id=outcome.tenant_id,
            lifecycle_id=outcome.lifecycle_id,
            case_id=outcome.case_id,
            investigation_id=outcome.investigation_id,
            decision_reference=outcome.decision_reference,
            action_reference=outcome.action_reference,
            verification_status=outcome.verification_status.value,
            evidence_references=list(outcome.evidence_references),
            provenance=dict(outcome.provenance),
            outcome_id=outcome.outcome_id,
        ))
        return outcome

    def list(self, tenant_id: str) -> list[Outcome]:
        tenant_id = str(tenant_id).strip()
        if not tenant_id:
            raise ValueError("tenant_id_required")
        return [self._from_record(record) for record in self.repository.list_outcomes(tenant_id)]

    @staticmethod
    def _from_record(record: object) -> Outcome:
        status_value = str(getattr(record, "verification_status", "UNKNOWN")).upper()
        status = OutcomeStatus._value2member_map_.get(status_value, OutcomeStatus.UNKNOWN)
        return Outcome(
            tenant_id=str(record.tenant_id),
            lifecycle_id=str(record.lifecycle_id),
            outcome_id=str(record.outcome_id),
            status=status,
            case_id=str(getattr(record, "case_id", "")),
            investigation_id=str(getattr(record, "investigation_id", "")),
            verification_status=status,
            decision_reference=str(getattr(record, "decision_reference", "")),
            action_reference=str(getattr(record, "action_reference", "")),
            evidence_references=tuple(getattr(record, "evidence_references", ()) or ()),
            provenance=getattr(record, "provenance", {}) or {},
        )
