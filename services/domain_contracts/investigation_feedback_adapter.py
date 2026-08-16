"""Translation boundary for the existing Command Center feedback repository."""

from __future__ import annotations

from typing import Any

from .investigation_feedback import InvestigationFeedback


class InvestigationFeedbackAdapter:
    """Map without changing semantics or repository ordering behavior."""

    def __init__(self, repository: Any) -> None:
        if repository is None or not all(hasattr(repository, name) for name in ("save", "list", "list_tenant")):
            raise ValueError("feedback_repository_required")
        self.repository = repository

    @staticmethod
    def to_contract(record: Any) -> InvestigationFeedback:
        required = ("feedback_id", "tenant_id", "investigation_id")
        if record is None or any(not hasattr(record, name) for name in required):
            raise TypeError("investigation_feedback_record_required")
        return InvestigationFeedback(
            feedback_id=record.feedback_id,
            tenant_id=record.tenant_id,
            investigation_id=record.investigation_id,
            outcome_reference=record.outcome_reference,
            analyst_reference=record.analyst_reference,
            outcome_agreement=record.outcome_agreement,
            evidence_sufficiency=record.evidence_sufficiency,
            recommendation_usefulness=record.recommendation_usefulness,
            confidence=record.confidence,
            reason_codes=tuple(record.reason_codes),
            supporting_references=tuple(record.supporting_references),
            provenance=record.provenance,
            created_at=record.created_at,
        )

    @staticmethod
    def to_record(value: InvestigationFeedback) -> Any:
        if not isinstance(value, InvestigationFeedback):
            raise TypeError("investigation_feedback_required")
        from services.intelligence.command_center.feedback import AnalystInvestigationFeedback

        return AnalystInvestigationFeedback(
            feedback_id=value.feedback_id,
            tenant_id=value.tenant_id,
            investigation_id=value.investigation_id,
            outcome_reference=value.outcome_reference,
            analyst_reference=value.analyst_reference,
            outcome_agreement=value.outcome_agreement,
            evidence_sufficiency=value.evidence_sufficiency,
            recommendation_usefulness=value.recommendation_usefulness,
            confidence=value.confidence,
            reason_codes=list(value.reason_codes),
            supporting_references=list(value.supporting_references),
            provenance=dict(value.provenance),
            created_at=value.created_at,
        )

    def save(self, value: InvestigationFeedback) -> InvestigationFeedback:
        return self.to_contract(self.repository.save(self.to_record(value)))

    def list(self, tenant_id: str, investigation_id: str) -> list[InvestigationFeedback]:
        tenant_id = str(tenant_id).strip()
        investigation_id = str(investigation_id).strip()
        if not tenant_id:
            raise ValueError("tenant_id_required")
        if not investigation_id:
            raise ValueError("investigation_id_required")
        return [self.to_contract(item) for item in self.repository.list(tenant_id, investigation_id)]

    def list_tenant(self, tenant_id: str) -> list[InvestigationFeedback]:
        tenant_id = str(tenant_id).strip()
        if not tenant_id:
            raise ValueError("tenant_id_required")
        return [self.to_contract(item) for item in self.repository.list_tenant(tenant_id)]
