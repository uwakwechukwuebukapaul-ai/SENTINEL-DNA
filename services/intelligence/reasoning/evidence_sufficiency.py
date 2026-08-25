"""Deterministic evidence sufficiency contract for bounded investigations.

This module is deliberately separate from the decision engine.  It evaluates
only the evidence and explicit sufficiency metadata emitted by the canonical
investigation runtime.  It never creates evidence or calls a provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from collections.abc import Mapping
from typing import Any

from services.intelligence.investigation.canonical import canonical_json, sha256_digest


class SufficiencyStatus(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"


EVALUATOR_VERSION = "evidence-sufficiency-v1"
_MAX_TEXT = 512
_MAX_ITEMS = 100


def _text(value: Any, field_name: str, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise ValueError(f"{field_name} is required")
        return None
    result = str(value).strip()
    if required and not result:
        raise ValueError(f"{field_name} is required")
    if len(result) > _MAX_TEXT or any(ord(char) < 32 for char in result):
        raise ValueError(f"{field_name} is invalid")
    return result or None


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _list_of_text(value: Any, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise ValueError(f"{field_name} must be a sequence")
    values = []
    for item in list(value)[:_MAX_ITEMS]:
        candidate = _text(item, field_name)
        if candidate:
            values.append(candidate)
    return tuple(sorted(set(values)))


def _result_mapping(result: Any) -> Mapping[str, Any]:
    if isinstance(result, Mapping):
        return result
    if hasattr(result, "to_dict"):
        value = result.to_dict()
        if isinstance(value, Mapping):
            return value
    return {
        key: getattr(result, key, None)
        for key in ("success", "status", "evidence", "artifacts", "metadata", "reasoning")
    }


def _evidence_id(item: Any) -> str | None:
    if not isinstance(item, Mapping):
        return None
    for key in ("evidence_id", "evidence_reference", "artifact_id", "reference", "id"):
        value = _text(item.get(key), key)
        if value:
            return value
    return None


@dataclass(frozen=True)
class EvidenceSufficiencyResult:
    status: SufficiencyStatus
    case_id: str
    investigation_id: str
    tenant_id: str
    evidence_gaps: tuple[str, ...] = ()
    supporting_evidence_ids: tuple[str, ...] = ()
    unresolved_hypotheses: tuple[str, ...] = ()
    confidence: float = 0.0
    rationale: str = ""
    recommended_follow_up: Mapping[str, Any] | None = None
    evaluator_version: str = EVALUATOR_VERSION
    input_evidence_digest: str = ""
    reasoning_reference: str = ""
    correlation_id: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.case_id or not self.investigation_id or not self.tenant_id:
            raise ValueError("sufficiency identity is required")
        if not isinstance(self.status, SufficiencyStatus):
            object.__setattr__(self, "status", SufficiencyStatus(str(self.status).upper()))
        confidence = float(self.confidence)
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(self, "confidence", confidence)
        if not self.input_evidence_digest:
            raise ValueError("input evidence digest is required")
        if self.status == SufficiencyStatus.INSUFFICIENT and not self.evidence_gaps:
            raise ValueError("insufficient evidence must identify an evidence gap")
        if self.status == SufficiencyStatus.INSUFFICIENT and not self.recommended_follow_up:
            raise ValueError("insufficient evidence must include a follow-up recommendation")

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "case_id": self.case_id,
            "investigation_id": self.investigation_id,
            "tenant_id": self.tenant_id,
            "evidence_gaps": list(self.evidence_gaps),
            "supporting_evidence_ids": list(self.supporting_evidence_ids),
            "unresolved_hypotheses": list(self.unresolved_hypotheses),
            "confidence": self.confidence,
            "rationale": self.rationale,
            "recommended_follow_up": dict(self.recommended_follow_up or {}),
            "evaluator_version": self.evaluator_version,
            "input_evidence_digest": self.input_evidence_digest,
            "reasoning_reference": self.reasoning_reference,
            "correlation_id": self.correlation_id,
            "provenance": dict(self.provenance),
        }


class EvidenceSufficiencyEvaluator:
    """Evaluate one canonical result without side effects or provider calls."""

    version = EVALUATOR_VERSION

    def evaluate(
        self,
        result: Any,
        *,
        case_id: str,
        investigation_id: str,
        tenant_id: str,
        correlation_id: str | None = None,
        observed_evidence: Any = None,
    ) -> EvidenceSufficiencyResult:
        try:
            return self._evaluate(
                result,
                case_id=_text(case_id, "case_id", required=True) or "",
                investigation_id=_text(investigation_id, "investigation_id", required=True) or "",
                tenant_id=_text(tenant_id, "tenant_id", required=True) or "",
                correlation_id=_text(correlation_id, "correlation_id"),
                observed_evidence=observed_evidence,
            )
        except Exception as exc:
            return self._blocked(
                case_id=str(case_id or ""), investigation_id=str(investigation_id or ""),
                tenant_id=str(tenant_id or ""), correlation_id=correlation_id,
                rationale=f"sufficiency contract rejected its input: {type(exc).__name__}",
                digest=sha256_digest({"invalid_input": type(exc).__name__}),
            )

    def _evaluate(
        self, result: Any, *, case_id: str, investigation_id: str, tenant_id: str,
        correlation_id: str | None, observed_evidence: Any,
    ) -> EvidenceSufficiencyResult:
        data = _result_mapping(result)
        metadata = _mapping(data.get("metadata"))
        explicit = data.get("evidence_sufficiency")
        if explicit is None:
            explicit = data.get("sufficiency_status")
        if explicit is None:
            explicit = metadata.get("evidence_sufficiency", metadata.get("sufficiency_status"))

        evidence_items = observed_evidence
        if evidence_items is None:
            evidence_items = list(data.get("evidence") or []) + list(data.get("artifacts") or [])
        if not isinstance(evidence_items, (list, tuple)):
            raise ValueError("observed evidence must be a sequence")
        actual_ids = tuple(sorted({item_id for item_id in (_evidence_id(item) for item in evidence_items) if item_id}))

        gaps = _list_of_text(data.get("evidence_gaps", metadata.get("evidence_gaps")), "evidence_gaps")
        hypotheses = _list_of_text(
            data.get("unresolved_hypotheses", metadata.get("unresolved_hypotheses")),
            "unresolved_hypotheses",
        )
        supporting = _list_of_text(
            data.get("supporting_evidence_ids", metadata.get("supporting_evidence_ids")),
            "supporting_evidence_ids",
        )
        if any(item not in actual_ids for item in supporting):
            return self._blocked(
                case_id=case_id, investigation_id=investigation_id, tenant_id=tenant_id,
                correlation_id=correlation_id, rationale="supporting evidence references an unobserved evidence ID",
                digest=sha256_digest({"actual": actual_ids, "supporting": supporting}),
            )

        raw_status = explicit
        if raw_status is None:
            raw_status = (
                SufficiencyStatus.SUFFICIENT.value
                if data.get("success") is True or str(data.get("status", "")).lower() == "completed"
                else SufficiencyStatus.UNKNOWN.value
            )
        try:
            status = SufficiencyStatus(str(raw_status).upper())
        except ValueError:
            return self._blocked(
                case_id=case_id, investigation_id=investigation_id, tenant_id=tenant_id,
                correlation_id=correlation_id, rationale="unrecognized sufficiency status",
                digest=sha256_digest({"status": str(raw_status)}),
            )
        if not supporting and status == SufficiencyStatus.SUFFICIENT:
            supporting = actual_ids

        recommendation = data.get("recommended_follow_up", metadata.get("recommended_follow_up"))
        if recommendation is not None and not isinstance(recommendation, Mapping):
            return self._blocked(
                case_id=case_id, investigation_id=investigation_id, tenant_id=tenant_id,
                correlation_id=correlation_id, rationale="follow-up recommendation is not structured",
                digest=sha256_digest({"recommendation_type": type(recommendation).__name__}),
            )
        recommendation = dict(recommendation or {})
        confidence = data.get("confidence")
        if confidence is None:
            confidence = data.get("ai_confidence")
        if confidence is None:
            confidence = metadata.get("confidence", 0.0)
        rationale = _text(data.get("rationale", metadata.get("rationale")), "rationale") or (
            "canonical investigation completed without recorded evidence gaps"
            if status == SufficiencyStatus.SUFFICIENT
            else "canonical investigation requires bounded evidence evaluation"
        )
        provenance = _mapping(data.get("provenance", metadata.get("provenance")))
        safe_provenance = {
            key: _text(provenance[key], key)
            for key in ("source", "source_reference", "runtime", "provider_replay")
            if provenance.get(key) is not None
        }
        digest_input = {
            "evidence_ids": actual_ids,
            "supporting_evidence_ids": supporting,
            "evidence_gaps": gaps,
            "unresolved_hypotheses": hypotheses,
            "status": status.value,
            "result_reference": _text(data.get("reasoning_reference"), "reasoning_reference"),
        }
        digest = sha256_digest(digest_input)
        if status == SufficiencyStatus.INSUFFICIENT and (not gaps or not recommendation):
            return self._blocked(
                case_id=case_id, investigation_id=investigation_id, tenant_id=tenant_id,
                correlation_id=correlation_id, rationale="insufficient result lacks a safe gap and recommendation",
                digest=digest,
            )
        return EvidenceSufficiencyResult(
            status=status, case_id=case_id, investigation_id=investigation_id, tenant_id=tenant_id,
            evidence_gaps=gaps, supporting_evidence_ids=supporting,
            unresolved_hypotheses=hypotheses, confidence=float(confidence), rationale=rationale,
            recommended_follow_up=recommendation, evaluator_version=self.version,
            input_evidence_digest=digest,
            reasoning_reference=_text(data.get("reasoning_reference"), "reasoning_reference") or f"SUFF-{digest[:16]}",
            correlation_id=correlation_id, provenance=safe_provenance,
        )

    @staticmethod
    def _blocked(*, case_id: str, investigation_id: str, tenant_id: str,
                 correlation_id: str | None, rationale: str, digest: str) -> EvidenceSufficiencyResult:
        return EvidenceSufficiencyResult(
            status=SufficiencyStatus.BLOCKED, case_id=case_id, investigation_id=investigation_id,
            tenant_id=tenant_id, rationale=rationale, evaluator_version=EVALUATOR_VERSION,
            input_evidence_digest=digest, reasoning_reference=f"SUFF-{digest[:16]}",
            correlation_id=correlation_id,
        )


__all__ = ["EvidenceSufficiencyEvaluator", "EvidenceSufficiencyResult", "SufficiencyStatus", "EVALUATOR_VERSION"]
