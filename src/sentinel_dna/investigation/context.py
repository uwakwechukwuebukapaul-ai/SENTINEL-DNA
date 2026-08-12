from dataclasses import dataclass, field
from typing import Any

from sentinel_dna.case_management.models import Case
from sentinel_dna.evidence.models import Evidence
from sentinel_dna.investigation.trace import InvestigationTrace


@dataclass
class InvestigationContext:
    case_id: str
    alert: dict[str, Any]
    case: Case | None = None
    evidence_items: list[Evidence] = field(default_factory=list)
    iocs: list[str] = field(default_factory=list)
    intelligence: dict[str, Any] = field(default_factory=dict)
    correlations: list[dict[str, Any]] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    mitre_attack: list[dict[str, str]] = field(default_factory=list)
    threat_classification: dict[str, Any] = field(default_factory=dict)
    risk: Any | None = None
    confidence: dict[str, Any] = field(default_factory=dict)
    reasoning: dict[str, Any] = field(default_factory=dict)
    decision_intelligence: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    report: dict[str, Any] = field(default_factory=dict)
    task_results: list[dict[str, Any]] = field(default_factory=list)
    audit_trail: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    trace: InvestigationTrace | None = None
