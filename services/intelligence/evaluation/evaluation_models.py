"""Deterministic models and synthetic dataset for operational accuracy validation."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class EvaluationMode(str, Enum):
    BASELINE = "baseline"
    INVESTIGATION_MEMORY = "investigation_memory"
    ORGANIZATIONAL_MEMORY = "organizational_memory"


@dataclass(frozen=True)
class AnalystGroundTruth:
    expected_verdict: str
    expected_evidence: tuple[str, ...]
    expected_mitre_techniques: tuple[str, ...]
    expected_ioc_relationships: tuple[dict[str, Any], ...]
    analyst_confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InvestigationObservation:
    """Synthetic AI observation; enforced verdict is deliberately separate."""

    advisory_verdict: str
    enforced_verdict: str
    evidence: tuple[str, ...]
    mitre_techniques: tuple[str, ...]
    ioc_relationships: tuple[dict[str, Any], ...]
    ai_confidence: float
    uncertainty_score: float
    reasoning_completeness: float
    provenance_evidence: tuple[str, ...]
    evidence_citations: tuple[str, ...]
    analyst_review_time_ms: float
    repeated_investigation_reuse: int
    knowledge_reuse_rate: float
    execution_latency_ms: float = 1.0
    disagreement_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SyntheticSOCScenario:
    scenario_id: str
    tenant_id: str
    scenario_type: str
    investigation_id: str
    case_id: str
    ground_truth: AnalystGroundTruth
    baseline: InvestigationObservation
    investigation_memory_delta: dict[str, Any] = field(default_factory=dict)
    organizational_memory_delta: dict[str, Any] = field(default_factory=dict)
    authorization_status: str = "blocked_by_policy"
    fail_closed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScenarioEvaluation:
    scenario_id: str
    tenant_id: str
    scenario_type: str
    ground_truth: AnalystGroundTruth
    observations: dict[str, InvestigationObservation]
    metrics: dict[str, dict[str, float | int]]
    safety: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "tenant_id": self.tenant_id,
            "scenario_type": self.scenario_type,
            "ground_truth": self.ground_truth.to_dict(),
            "observations": {key: value.to_dict() for key, value in self.observations.items()},
            "metrics": self.metrics,
            "safety": self.safety,
        }


@dataclass(frozen=True)
class OperationalAccuracyValidationReport:
    report_version: str
    tenant_id: str
    generated_at: str
    scenario_count: int
    scenario_evaluations: tuple[ScenarioEvaluation, ...]
    aggregate_metrics: dict[str, Any]
    memory_benefit_score: float
    latency_impact: dict[str, float]
    safety_validation: dict[str, bool]
    replay_digest: str
    report_digest: str
    immutable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "tenant_id": self.tenant_id,
            "generated_at": self.generated_at,
            "scenario_count": self.scenario_count,
            "scenario_evaluations": [item.to_dict() for item in self.scenario_evaluations],
            "aggregate_metrics": self.aggregate_metrics,
            "memory_benefit_score": self.memory_benefit_score,
            "latency_impact": self.latency_impact,
            "safety_validation": self.safety_validation,
            "replay_digest": self.replay_digest,
            "report_digest": self.report_digest,
            "immutable": self.immutable,
        }

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


SCENARIO_TYPES = (
    "phishing_compromise",
    "credential_theft",
    "malware_execution",
    "suspicious_authentication",
    "lateral_movement",
    "command_and_control",
    "benign_false_positive",
    "multi_ioc_investigation",
)


def _scenario(
    scenario_id: str,
    scenario_type: str,
    expected_verdict: str,
    evidence: tuple[str, ...],
    mitre: tuple[str, ...],
    iocs: tuple[dict[str, Any], ...],
    baseline: InvestigationObservation,
    investigation_delta: dict[str, Any],
    organizational_delta: dict[str, Any],
) -> SyntheticSOCScenario:
    tenant = "tenant-accuracy-validation"
    return SyntheticSOCScenario(
        scenario_id=scenario_id,
        tenant_id=tenant,
        scenario_type=scenario_type,
        investigation_id=f"EVAL-INV-{scenario_id.upper()}",
        case_id=f"EVAL-CASE-{scenario_id.upper()}",
        ground_truth=AnalystGroundTruth(expected_verdict, evidence, mitre, iocs, 0.90),
        baseline=baseline,
        investigation_memory_delta=investigation_delta,
        organizational_memory_delta=organizational_delta,
    )


def default_synthetic_soc_scenarios() -> tuple[SyntheticSOCScenario, ...]:
    """Stable fixtures covering the required SOC investigation classes."""
    return (
        _scenario("phishing", "phishing_compromise", "malicious", ("P-E1", "P-E2"), ("T1566", "T1078"), ({"ioc": "lure.test", "relationship": "credential_lure"},),
            InvestigationObservation("benign", "review_required", ("P-E1",), ("T1566",), (), .55, .55, .45, ("P-E1",), ("P-E1",), 1200, 0, .0),
            {"advisory_verdict": "malicious", "evidence": ("P-E2",), "mitre_techniques": ("T1078",), "ioc_relationships": ({"ioc": "lure.test", "relationship": "credential_lure"},), "ai_confidence": .78, "uncertainty_score": .35, "reasoning_completeness": .70, "provenance_evidence": ("P-E2",), "evidence_citations": ("P-E2",), "analyst_review_time_ms": 900, "repeated_investigation_reuse": 1, "knowledge_reuse_rate": .35},
            {"advisory_verdict": "malicious", "evidence": ("P-E2",), "mitre_techniques": ("T1078",), "ioc_relationships": ({"ioc": "lure.test", "relationship": "credential_lure"},), "ai_confidence": .88, "uncertainty_score": .20, "reasoning_completeness": .90, "provenance_evidence": ("P-E2",), "evidence_citations": ("P-E2",), "analyst_review_time_ms": 650, "repeated_investigation_reuse": 2, "knowledge_reuse_rate": .70}),
        _scenario("credential", "credential_theft", "malicious", ("C-E1", "C-E2"), ("T1003",), ({"ioc": "user@example.test", "relationship": "credential_access"},),
            InvestigationObservation("malicious", "review_required", ("C-E1",), (), (), .66, .45, .50, ("C-E1",), ("C-E1",), 1100, 0, .0),
            {"evidence": ("C-E2",), "mitre_techniques": ("T1003",), "ioc_relationships": ({"ioc": "user@example.test", "relationship": "credential_access"},), "ai_confidence": .80, "uncertainty_score": .30, "reasoning_completeness": .75, "provenance_evidence": ("C-E2",), "evidence_citations": ("C-E2",), "analyst_review_time_ms": 800, "repeated_investigation_reuse": 1, "knowledge_reuse_rate": .40},
            {"evidence": ("C-E2",), "mitre_techniques": ("T1003",), "ioc_relationships": ({"ioc": "user@example.test", "relationship": "credential_access"},), "ai_confidence": .91, "uncertainty_score": .16, "reasoning_completeness": .93, "provenance_evidence": ("C-E2",), "evidence_citations": ("C-E2",), "analyst_review_time_ms": 600, "repeated_investigation_reuse": 2, "knowledge_reuse_rate": .75}),
        _scenario("malware", "malware_execution", "malicious", ("M-E1", "M-E2"), ("T1204", "T1059.001"), ({"ioc": "payload.test", "relationship": "downloaded_payload"},),
            InvestigationObservation("malicious", "review_required", ("M-E1",), ("T1204",), (), .72, .40, .55, ("M-E1",), ("M-E1",), 1000, 0, .0),
            {"evidence": ("M-E2",), "mitre_techniques": ("T1059.001",), "ioc_relationships": ({"ioc": "payload.test", "relationship": "downloaded_payload"},), "ai_confidence": .86, "uncertainty_score": .25, "reasoning_completeness": .82, "provenance_evidence": ("M-E2",), "evidence_citations": ("M-E2",), "analyst_review_time_ms": 700, "repeated_investigation_reuse": 1, "knowledge_reuse_rate": .45},
            {"evidence": ("M-E2",), "mitre_techniques": ("T1059.001",), "ioc_relationships": ({"ioc": "payload.test", "relationship": "downloaded_payload"},), "ai_confidence": .94, "uncertainty_score": .12, "reasoning_completeness": .95, "provenance_evidence": ("M-E2",), "evidence_citations": ("M-E2",), "analyst_review_time_ms": 500, "repeated_investigation_reuse": 2, "knowledge_reuse_rate": .80}),
        _scenario("auth", "suspicious_authentication", "malicious", ("A-E1",), ("T1078",), ({"ioc": "user@example.test", "relationship": "impossible_travel"},),
            InvestigationObservation("malicious", "review_required", ("A-E1",), (), (), .62, .50, .45, (), ("A-E1",), 1300, 0, .0),
            {"mitre_techniques": ("T1078",), "ioc_relationships": ({"ioc": "user@example.test", "relationship": "impossible_travel"},), "ai_confidence": .80, "uncertainty_score": .30, "reasoning_completeness": .75, "provenance_evidence": ("A-E1",), "analyst_review_time_ms": 900, "repeated_investigation_reuse": 1, "knowledge_reuse_rate": .35},
            {"mitre_techniques": ("T1078",), "ioc_relationships": ({"ioc": "user@example.test", "relationship": "impossible_travel"},), "ai_confidence": .89, "uncertainty_score": .17, "reasoning_completeness": .92, "provenance_evidence": ("A-E1",), "analyst_review_time_ms": 650, "repeated_investigation_reuse": 2, "knowledge_reuse_rate": .70}),
        _scenario("lateral", "lateral_movement", "malicious", ("L-E1", "L-E2"), ("T1021",), ({"ioc": "host-2", "relationship": "remote_service"},),
            InvestigationObservation("benign", "review_required", ("L-E1",), (), (), .58, .58, .40, ("L-E1",), ("L-E1",), 1400, 0, .0),
            {"advisory_verdict": "malicious", "evidence": ("L-E2",), "mitre_techniques": ("T1021",), "ioc_relationships": ({"ioc": "host-2", "relationship": "remote_service"},), "ai_confidence": .79, "uncertainty_score": .36, "reasoning_completeness": .72, "provenance_evidence": ("L-E2",), "evidence_citations": ("L-E2",), "analyst_review_time_ms": 1000, "repeated_investigation_reuse": 1, "knowledge_reuse_rate": .30},
            {"advisory_verdict": "malicious", "evidence": ("L-E2",), "mitre_techniques": ("T1021",), "ioc_relationships": ({"ioc": "host-2", "relationship": "remote_service"},), "ai_confidence": .90, "uncertainty_score": .18, "reasoning_completeness": .94, "provenance_evidence": ("L-E2",), "evidence_citations": ("L-E2",), "analyst_review_time_ms": 700, "repeated_investigation_reuse": 2, "knowledge_reuse_rate": .78}),
        _scenario("c2", "command_and_control", "malicious", ("X-E1", "X-E2"), ("T1071.001",), ({"ioc": "c2.test", "relationship": "beaconing"},),
            InvestigationObservation("malicious", "review_required", ("X-E1",), (), (), .68, .48, .48, ("X-E1",), ("X-E1",), 1150, 0, .0),
            {"evidence": ("X-E2",), "mitre_techniques": ("T1071.001",), "ioc_relationships": ({"ioc": "c2.test", "relationship": "beaconing"},), "ai_confidence": .84, "uncertainty_score": .27, "reasoning_completeness": .80, "provenance_evidence": ("X-E2",), "evidence_citations": ("X-E2",), "analyst_review_time_ms": 750, "repeated_investigation_reuse": 1, "knowledge_reuse_rate": .42},
            {"evidence": ("X-E2",), "mitre_techniques": ("T1071.001",), "ioc_relationships": ({"ioc": "c2.test", "relationship": "beaconing"},), "ai_confidence": .93, "uncertainty_score": .14, "reasoning_completeness": .95, "provenance_evidence": ("X-E2",), "evidence_citations": ("X-E2",), "analyst_review_time_ms": 550, "repeated_investigation_reuse": 2, "knowledge_reuse_rate": .82}),
        _scenario("benign", "benign_false_positive", "benign", ("B-E1",), (), (),
            InvestigationObservation("malicious", "review_required", (), (), (), .52, .60, .35, (), (), 1500, 0, .0),
            {"advisory_verdict": "benign", "evidence": ("B-E1",), "ai_confidence": .76, "uncertainty_score": .30, "reasoning_completeness": .75, "provenance_evidence": ("B-E1",), "evidence_citations": ("B-E1",), "analyst_review_time_ms": 900, "repeated_investigation_reuse": 1, "knowledge_reuse_rate": .50},
            {"advisory_verdict": "benign", "evidence": ("B-E1",), "ai_confidence": .91, "uncertainty_score": .12, "reasoning_completeness": .95, "provenance_evidence": ("B-E1",), "evidence_citations": ("B-E1",), "analyst_review_time_ms": 600, "repeated_investigation_reuse": 2, "knowledge_reuse_rate": .85}),
        _scenario("multi-ioc", "multi_ioc_investigation", "malicious", ("I-E1", "I-E2", "I-E3"), ("T1566", "T1071.001"), ({"ioc": "lure.test", "relationship": "delivery"}, {"ioc": "c2.test", "relationship": "beaconing"}),
            InvestigationObservation("benign", "review_required", ("I-E1",), ("T1566",), (), .55, .62, .35, ("I-E1",), ("I-E1",), 1600, 0, .0),
            {"advisory_verdict": "malicious", "evidence": ("I-E2",), "mitre_techniques": ("T1071.001",), "ioc_relationships": ({"ioc": "lure.test", "relationship": "delivery"},), "ai_confidence": .78, "uncertainty_score": .38, "reasoning_completeness": .70, "provenance_evidence": ("I-E2",), "evidence_citations": ("I-E2",), "analyst_review_time_ms": 1100, "repeated_investigation_reuse": 1, "knowledge_reuse_rate": .30},
            {"advisory_verdict": "malicious", "evidence": ("I-E2", "I-E3"), "mitre_techniques": ("T1071.001",), "ioc_relationships": ({"ioc": "lure.test", "relationship": "delivery"}, {"ioc": "c2.test", "relationship": "beaconing"}), "ai_confidence": .89, "uncertainty_score": .20, "reasoning_completeness": .90, "provenance_evidence": ("I-E2", "I-E3"), "evidence_citations": ("I-E2", "I-E3"), "analyst_review_time_ms": 800, "repeated_investigation_reuse": 2, "knowledge_reuse_rate": .72}),
    )


__all__ = [
    "AnalystGroundTruth", "EvaluationMode", "InvestigationObservation",
    "OperationalAccuracyValidationReport", "ScenarioEvaluation",
    "SCENARIO_TYPES", "SyntheticSOCScenario", "default_synthetic_soc_scenarios",
]
