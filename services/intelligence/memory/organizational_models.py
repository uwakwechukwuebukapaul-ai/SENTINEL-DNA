"""Tenant-scoped organizational cyber memory domain records.

These records are reusable evidence summaries, never authoritative decisions.
They are immutable at the domain boundary and receive a content hash at the
repository boundary before append-only persistence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import json
from typing import Any


class OrganizationalMemoryRecord:
    """Common serialization contract for organizational memory records."""

    memory_type = "organizational_memory"

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["memory_type"] = self.memory_type
        return value

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, default=str)


@dataclass(frozen=True)
class InvestigationPattern(OrganizationalMemoryRecord):
    pattern_id: str
    tenant_id: str
    source_investigation_id: str
    pattern_key: str
    description: str
    evidence_provenance: dict[str, Any]
    created_by: str | None
    confidence: float
    observed_at: str
    created_at: str
    why_stored: str
    audit_hash: str = ""
    attack_pattern: list[str] | tuple[str, ...] = ()
    mitre_techniques: list[str] | tuple[str, ...] = ()
    validation_status: str = "validated"
    advisory_only: bool = True

    memory_type = "investigation_pattern"


@dataclass(frozen=True)
class AttackCampaignMemory(OrganizationalMemoryRecord):
    campaign_id: str
    tenant_id: str
    source_investigation_id: str
    campaign_key: str
    description: str
    evidence_provenance: dict[str, Any]
    created_by: str | None
    confidence: float
    observed_at: str
    created_at: str
    why_stored: str
    audit_hash: str = ""
    indicators: list[str] | tuple[str, ...] = ()
    relationships: list[dict[str, Any]] | tuple[dict[str, Any], ...] = ()
    validation_status: str = "validated"
    advisory_only: bool = True

    memory_type = "attack_campaign_memory"


@dataclass(frozen=True)
class AnalystKnowledgeEntry(OrganizationalMemoryRecord):
    knowledge_id: str
    tenant_id: str
    source_investigation_id: str
    knowledge_key: str
    resolution_pattern: str
    evidence_provenance: dict[str, Any]
    created_by: str | None
    confidence: float
    observed_at: str
    created_at: str
    why_stored: str
    audit_hash: str = ""
    analyst_id: str | None = None
    feedback_id: str | None = None
    analyst_verdict: str = ""
    validation_status: str = "validated"
    advisory_only: bool = True

    memory_type = "analyst_knowledge_entry"


@dataclass(frozen=True)
class DetectionLearningRecord(OrganizationalMemoryRecord):
    detection_id: str
    tenant_id: str
    source_investigation_id: str
    detection_key: str
    detection_rule_id: str
    effectiveness: str
    observed_outcome: str
    evidence_provenance: dict[str, Any]
    created_by: str | None
    confidence: float
    observed_at: str
    created_at: str
    why_stored: str
    audit_hash: str = ""
    validation_status: str = "validated"
    advisory_only: bool = True

    memory_type = "detection_learning_record"


@dataclass(frozen=True)
class ResponsePlaybookMemory(OrganizationalMemoryRecord):
    playbook_memory_id: str
    tenant_id: str
    source_investigation_id: str
    playbook_key: str
    playbook_id: str
    resolution_pattern: str
    success_signal: str
    evidence_provenance: dict[str, Any]
    created_by: str | None
    confidence: float
    observed_at: str
    created_at: str
    why_stored: str
    audit_hash: str = ""
    validation_status: str = "validated"
    advisory_only: bool = True

    memory_type = "response_playbook_memory"


ORGANIZATIONAL_MEMORY_TYPES = {
    item.memory_type: item
    for item in (
        InvestigationPattern,
        AttackCampaignMemory,
        AnalystKnowledgeEntry,
        DetectionLearningRecord,
        ResponsePlaybookMemory,
    )
}


__all__ = [
    "AttackCampaignMemory",
    "AnalystKnowledgeEntry",
    "DetectionLearningRecord",
    "InvestigationPattern",
    "ORGANIZATIONAL_MEMORY_TYPES",
    "OrganizationalMemoryRecord",
    "ResponsePlaybookMemory",
]
