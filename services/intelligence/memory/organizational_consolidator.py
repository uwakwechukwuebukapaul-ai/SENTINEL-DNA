"""Deterministic consolidation from completed investigations into org memory."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Iterable

from .models import AnalystFeedbackRecord, InvestigationMemoryRecord
from .organizational_models import (
    AnalystKnowledgeEntry,
    AttackCampaignMemory,
    DetectionLearningRecord,
    InvestigationPattern,
    OrganizationalMemoryRecord,
    ResponsePlaybookMemory,
)
from .organizational_repository import OrganizationalMemoryRepository
from .similarity import DeterministicSimilarityProvider, MemorySimilarityProvider, memory_tokens


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 6)


def _stable_id(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    return f"{prefix}-{digest[:20]}"


def _data(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    return dict(value) if isinstance(value, dict) else dict(vars(value))


@dataclass(frozen=True)
class ConsolidationResult:
    tenant_id: str
    source_investigation_id: str
    records: tuple[OrganizationalMemoryRecord, ...]
    validation_gate: str
    consolidation_digest: str
    advisory_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "source_investigation_id": self.source_investigation_id,
            "records": [record.to_dict() for record in self.records],
            "validation_gate": self.validation_gate,
            "consolidation_digest": self.consolidation_digest,
            "advisory_only": self.advisory_only,
        }


class OrganizationalMemoryConsolidator:
    """Turn validated historical evidence into reusable advisory records."""

    def __init__(
        self,
        repository: OrganizationalMemoryRepository,
        similarity_provider: MemorySimilarityProvider | None = None,
    ) -> None:
        self.repository = repository
        self.similarity_provider = similarity_provider or DeterministicSimilarityProvider()

    @staticmethod
    def _validated_findings(findings: Iterable[Any]) -> list[dict[str, Any]]:
        result = []
        for item in findings or ():
            data = _data(item)
            status = str(data.get("validation_status") or data.get("status") or "unvalidated").lower()
            if status in {"validated", "confirmed", "accepted", "complete", "completed"}:
                result.append(data)
        return result

    @staticmethod
    def _feedback_data(feedback: Iterable[Any]) -> list[dict[str, Any]]:
        return [_data(item) for item in feedback or ()]

    @staticmethod
    def _provenance(record: InvestigationMemoryRecord, *, evidence: list[dict[str, Any]], source: str) -> dict[str, Any]:
        evidence_ids = sorted({
            str(item.get("evidence_id") or item.get("id"))
            for item in evidence
            if item.get("evidence_id") or item.get("id")
        })
        return {
            "source": source,
            "source_investigation_id": record.investigation_id,
            "source_memory_id": record.memory_id,
            "source_memory_audit_hash": record.audit_hash,
            "evidence_references": evidence_ids or list(record.evidence_summary.get("references", [])),
            "evidence_fingerprint": record.evidence_fingerprint,
            "source_provenance": dict(record.provenance),
            "validation_status": record.validation_result,
            "deterministic": True,
            "advisory_only": True,
        }

    def consolidate_completed_investigation(
        self,
        *,
        tenant_id: str,
        investigation: InvestigationMemoryRecord,
        analyst_feedback: Iterable[AnalystFeedbackRecord | dict[str, Any]] = (),
        validated_findings: Iterable[Any] = (),
        mitre_mappings: Iterable[Any] = (),
        ioc_relationships: Iterable[Any] = (),
        created_by: str | None = None,
        observed_at: str | None = None,
    ) -> ConsolidationResult:
        tenant_id = str(tenant_id or "").strip()
        if not tenant_id:
            raise ValueError("organizational_memory_tenant_id_required")
        if investigation.tenant_id != tenant_id:
            raise PermissionError("organizational_memory_tenant_mismatch")
        source_outcome = investigation.outcome if isinstance(investigation.outcome, dict) else {}
        source_completed = str(source_outcome.get("status") or "completed").lower() in {"completed", "complete", "validated"}
        source_successful = source_outcome.get("success", True) is not False
        if investigation.validation_result not in {"validated", "confirmed", "accepted"} or not source_completed or not source_successful:
            return ConsolidationResult(
                tenant_id=tenant_id,
                source_investigation_id=investigation.investigation_id,
                records=(),
                validation_gate="blocked_unvalidated_source",
                consolidation_digest=_stable_id("CON", {"tenant_id": tenant_id, "investigation_id": investigation.investigation_id}),
            )
        findings = self._validated_findings(validated_findings)
        feedback = self._feedback_data(analyst_feedback)
        relationships = [_data(item) for item in ioc_relationships or ()]
        mitre = sorted({
            str(item.get("technique_id") or item.get("id") or item)
            if isinstance(item, dict) else str(item)
            for item in (mitre_mappings or ())
            if item is not None
        })
        evidence = [
            item for item in (
                investigation.evidence_summary.get("items", [])
                if isinstance(investigation.evidence_summary, dict)
                else []
            )
            if isinstance(item, dict)
        ]
        timestamp = str(observed_at or investigation.created_at or _now())
        source_id = str(investigation.investigation_id)
        provenance = self._provenance(investigation, evidence=evidence, source="completed_investigation")
        base_confidence = _clamp(investigation.confidence)
        records: list[OrganizationalMemoryRecord] = []

        pattern_tokens = sorted(memory_tokens(investigation.attack_pattern) | memory_tokens(mitre))
        pattern_key = _stable_id("PATKEY", {"tenant_id": tenant_id, "pattern": pattern_tokens})
        pattern_id = _stable_id("PAT", {"tenant_id": tenant_id, "pattern": pattern_tokens, "source": source_id})
        records.append(InvestigationPattern(
            pattern_id=pattern_id,
            tenant_id=tenant_id,
            source_investigation_id=source_id,
            pattern_key=pattern_key,
            description=f"Validated investigation pattern from {source_id}",
            evidence_provenance=provenance,
            created_by=created_by,
            confidence=base_confidence,
            observed_at=timestamp,
            created_at=timestamp,
            why_stored="validated findings and investigation evidence established a reusable attack pattern",
            attack_pattern=pattern_tokens,
            mitre_techniques=mitre,
        ))

        indicators = sorted({
            str(relationship.get(key))
            for relationship in relationships
            for key in ("ioc", "indicator", "value", "domain", "ip", "hash")
            if relationship.get(key)
        })
        if relationships or indicators:
            campaign_key = _stable_id("CAMKEY", {"tenant_id": tenant_id, "indicators": indicators, "relationships": relationships})
            campaign_id = _stable_id("CAM", {"tenant_id": tenant_id, "indicators": indicators, "relationships": relationships, "source": source_id})
            records.append(AttackCampaignMemory(
                campaign_id=campaign_id,
                tenant_id=tenant_id,
                source_investigation_id=source_id,
                campaign_key=campaign_key,
                description="Related IOC infrastructure and behavior observed in a validated investigation",
                evidence_provenance={**provenance, "ioc_relationships": relationships},
                created_by=created_by,
                confidence=base_confidence,
                observed_at=timestamp,
                created_at=timestamp,
                why_stored="validated IOC relationships support reusable infrastructure correlation",
                indicators=indicators,
                relationships=relationships,
            ))

        for item in feedback:
            feedback_id = str(item.get("feedback_id") or _stable_id("FB", item))
            analyst_id = str(item.get("analyst_id") or item.get("created_by") or created_by or "unknown")
            verdict = str(item.get("verdict") or item.get("decision") or "unknown")
            feedback_confidence = _clamp(float(item.get("confidence") or base_confidence))
            knowledge_key = _stable_id("KNOW", {"tenant_id": tenant_id, "source": source_id, "feedback": feedback_id})
            records.append(AnalystKnowledgeEntry(
                knowledge_id=knowledge_key,
                tenant_id=tenant_id,
                source_investigation_id=source_id,
                knowledge_key=knowledge_key,
                resolution_pattern=str(item.get("reason") or f"Analyst resolution: {verdict}"),
                evidence_provenance={**provenance, "feedback_id": feedback_id},
                created_by=analyst_id,
                confidence=feedback_confidence,
                observed_at=str(item.get("created_at") or timestamp),
                created_at=timestamp,
                why_stored="analyst feedback validated the investigation resolution pattern",
                analyst_id=analyst_id,
                feedback_id=feedback_id,
                analyst_verdict=verdict,
            ))

        detection_items = [item for item in findings if item.get("detection_rule_id") or item.get("rule_id") or item.get("detection_id")]
        for item in detection_items:
            rule_id = str(item.get("detection_rule_id") or item.get("rule_id") or item.get("detection_id"))
            detection_key = _stable_id("DET", {"tenant_id": tenant_id, "rule": rule_id, "source": source_id})
            records.append(DetectionLearningRecord(
                detection_id=detection_key,
                tenant_id=tenant_id,
                source_investigation_id=source_id,
                detection_key=detection_key,
                detection_rule_id=rule_id,
                effectiveness=str(item.get("effectiveness") or "validated"),
                observed_outcome=str(item.get("outcome") or item.get("status") or "effective_in_prior_investigation"),
                evidence_provenance={**provenance, "finding_id": item.get("finding_id") or item.get("id")},
                created_by=created_by,
                confidence=_clamp(float(item.get("confidence") or base_confidence)),
                observed_at=timestamp,
                created_at=timestamp,
                why_stored="validated finding linked an observed outcome to a detection rule",
            ))

        playbook_items = [item for item in findings if item.get("playbook_id") or item.get("response_playbook_id")]
        for item in playbook_items:
            playbook_id = str(item.get("playbook_id") or item.get("response_playbook_id"))
            playbook_key = _stable_id("PLAY", {"tenant_id": tenant_id, "playbook": playbook_id, "source": source_id})
            records.append(ResponsePlaybookMemory(
                playbook_memory_id=playbook_key,
                tenant_id=tenant_id,
                source_investigation_id=source_id,
                playbook_key=playbook_key,
                playbook_id=playbook_id,
                resolution_pattern=str(item.get("resolution_pattern") or item.get("recommendation") or "validated response pattern"),
                success_signal=str(item.get("success_signal") or item.get("outcome") or "analyst_validated"),
                evidence_provenance={**provenance, "finding_id": item.get("finding_id") or item.get("id")},
                created_by=created_by,
                confidence=_clamp(float(item.get("confidence") or base_confidence)),
                observed_at=timestamp,
                created_at=timestamp,
                why_stored="validated finding documented a reusable response resolution pattern",
            ))

        saved = tuple(self.repository.save(item) for item in records)
        digest = hashlib.sha256(
            json.dumps({"tenant_id": tenant_id, "source": source_id, "records": [item.audit_hash for item in saved]}, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return ConsolidationResult(
            tenant_id=tenant_id,
            source_investigation_id=source_id,
            records=saved,
            validation_gate="validated_source_and_findings",
            consolidation_digest=digest,
        )


__all__ = ["ConsolidationResult", "OrganizationalMemoryConsolidator"]
