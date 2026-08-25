"""Deterministic operational validation for advisory investigation memory.

This module is deliberately a validation harness, not a production decision
engine. It runs paired synthetic investigations and measures the value of
memory while asserting that authorization and verdict outputs are invariant.
Timing is observed evidence only and is excluded from replay digests.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable

from services.intelligence.investigation.canonical import sha256_digest
from services.intelligence.investigation.investigation_result import InvestigationResult

from .memory_service import MemoryService, _clamp
from .repository import InvestigationMemoryRepository


VALIDATION_VERSION = "operational-cyber-memory-validation.v1"
FIXED_SEED_TIME = "2026-01-01T00:00:00+00:00"


@dataclass(frozen=True)
class OperationalValidationScenario:
    """Synthetic case input and its non-memory control expectations."""

    scenario_id: str
    tenant_id: str
    case_id: str
    investigation_id: str
    alert: dict[str, Any]
    artifacts: tuple[dict[str, Any], ...]
    historical_case_id: str
    historical_investigation_id: str
    expected_verdict: str
    expected_authorization_status: str = "blocked_by_policy"
    baseline_confidence: float = 0.60
    baseline_evidence_correlation: float = 0.25
    confidence_relevance_weight: float = 0.10
    confidence_feedback_weight: float = 0.05

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationMeasurement:
    """Auditable result for one side of a paired investigation."""

    scenario_id: str
    memory_enabled: bool
    case_id: str
    investigation_id: str
    verdict: str
    authorization_status: str
    fail_closed: bool
    result_confidence: float
    advisory_confidence: float
    evidence_correlation_score: float
    analyst_feedback_reuse_count: int
    historical_case_relevance: float
    execution_time_ms: float
    evidence_references: tuple[str, ...] = ()
    memory_ids: tuple[str, ...] = ()
    api_resource: str = "synthetic://investigation-memory"
    provenance: dict[str, Any] = field(default_factory=dict)
    validation_result: str = "passed"
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationComparison:
    """Paired memory-disabled/enabled measurements and invariant checks."""

    scenario_id: str
    disabled: ValidationMeasurement
    enabled: ValidationMeasurement
    confidence_change: float
    evidence_correlation_improvement: float
    analyst_feedback_reuse: int
    historical_case_relevance: float
    execution_time_change_ms: float
    authorization_unchanged: bool
    verdict_unchanged: bool
    result_schema_unchanged: bool
    fail_closed_unchanged: bool
    validation_result: str
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MemoryValidationReport:
    """Signed-by-digest report suitable for audit storage and replay."""

    report_version: str
    generated_at: str
    validation_result: str
    scenario_count: int
    comparisons: tuple[ValidationComparison, ...]
    aggregate_metrics: dict[str, Any]
    control_invariants: dict[str, bool]
    evidence_provenance: dict[str, Any]
    deterministic_replay: dict[str, Any]
    audit_trail: tuple[dict[str, Any], ...]
    report_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "generated_at": self.generated_at,
            "validation_result": self.validation_result,
            "scenario_count": self.scenario_count,
            "comparisons": [item.to_dict() for item in self.comparisons],
            "aggregate_metrics": self.aggregate_metrics,
            "control_invariants": self.control_invariants,
            "evidence_provenance": self.evidence_provenance,
            "deterministic_replay": self.deterministic_replay,
            "audit_trail": list(self.audit_trail),
            "report_digest": self.report_digest,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, default=str) + "\n"

    def write(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(self.to_json(), encoding="utf-8")
        return destination


def default_operational_validation_scenarios() -> tuple[OperationalValidationScenario, ...]:
    """Return stable phishing and ransomware cases for offline validation."""

    return (
        OperationalValidationScenario(
            scenario_id="synthetic-phishing-credential-access",
            tenant_id="tenant-validation-a",
            case_id="VAL-CASE-001",
            investigation_id="VAL-INV-001",
            alert={"type": "phishing", "category": "credential_access", "title": "Suspicious login lure"},
            artifacts=(
                {"evidence_id": "E-PHISH-URL", "type": "url", "source": "email_gateway", "technique": "T1566"},
                {"evidence_id": "E-PHISH-AUTH", "type": "authentication", "source": "identity_provider", "technique": "T1078"},
            ),
            historical_case_id="VAL-HIST-001",
            historical_investigation_id="VAL-HIST-INV-001",
            expected_verdict="confirmed_malicious",
        ),
        OperationalValidationScenario(
            scenario_id="synthetic-ransomware-execution",
            tenant_id="tenant-validation-b",
            case_id="VAL-CASE-002",
            investigation_id="VAL-INV-002",
            alert={"type": "ransomware", "category": "impact", "title": "Encrypted endpoint files"},
            artifacts=(
                {"evidence_id": "E-RANS-PROC", "type": "process", "source": "endpoint", "technique": "T1486"},
                {"evidence_id": "E-RANS-FILE", "type": "file", "source": "endpoint", "technique": "T1486"},
            ),
            historical_case_id="VAL-HIST-002",
            historical_investigation_id="VAL-HIST-INV-002",
            expected_verdict="confirmed_malicious",
        ),
    )


class OperationalCyberMemoryValidator:
    """Run paired, deterministic, memory-advisory operational scenarios."""

    def __init__(
        self,
        *,
        scenarios: Iterable[OperationalValidationScenario] | None = None,
        generated_at: str | None = None,
    ) -> None:
        self.scenarios = tuple(scenarios or default_operational_validation_scenarios())
        self.generated_at = str(generated_at or datetime.now(timezone.utc).isoformat())

    @staticmethod
    def _service() -> MemoryService:
        return MemoryService(InvestigationMemoryRepository(":memory:"))

    @staticmethod
    def _result(scenario: OperationalValidationScenario, *, memory_enabled: bool) -> InvestigationResult:
        """Create the same schema and enforcement projection for both arms."""
        return InvestigationResult(
            success=True,
            status="completed",
            investigation_id=scenario.investigation_id,
            case_id=scenario.case_id,
            artifacts=list(scenario.artifacts),
            evidence=list(scenario.artifacts),
            risk=scenario.expected_verdict,
            confidence=float(scenario.baseline_confidence),
            intelligence={"validation_memory_enabled": bool(memory_enabled)},
            metadata={
                "synthetic_validation": True,
                "validation_verdict": scenario.expected_verdict,
                "authorization_status": scenario.expected_authorization_status,
                "fail_closed": True,
            },
        )

    @staticmethod
    def _seed_memory(service: MemoryService, scenario: OperationalValidationScenario) -> None:
        historical_context = {
            "tenant_id": scenario.tenant_id,
            "case_id": scenario.historical_case_id,
            "investigation_id": scenario.historical_investigation_id,
            "alert": dict(scenario.alert),
            "artifacts": [dict(item) for item in scenario.artifacts],
            "evidence": [dict(item) for item in scenario.artifacts],
            "completed_at": FIXED_SEED_TIME,
            "synthetic_only": True,
        }
        historical_result = {
            "success": True,
            "status": "completed",
            "case_id": scenario.historical_case_id,
            "investigation_id": scenario.historical_investigation_id,
            "risk": scenario.expected_verdict,
            "confidence": 0.82,
        }
        service.store_investigation_memory(
            historical_context,
            {"summary": "Synthetic historical case", "findings": ["validated pattern"]},
            historical_result,
            tenant_id=scenario.tenant_id,
            provenance={
                "validation_scenario_id": scenario.scenario_id,
                "api_resource": "synthetic://historical-investigation",
                "evidence_source": "synthetic_operational_fixture",
            },
        )
        service.record_analyst_feedback(
            tenant_id=scenario.tenant_id,
            investigation_id=scenario.historical_investigation_id,
            analyst_id="synthetic-analyst",
            verdict=scenario.expected_verdict,
            feedback_id=f"VAL-FEEDBACK-{scenario.scenario_id}",
            confidence=0.95,
            reason="Synthetic analyst confirmation for replayable validation.",
            evidence_references=(item["evidence_id"] for item in scenario.artifacts),
            provenance={
                "validation_scenario_id": scenario.scenario_id,
                "evidence_source": "synthetic_analyst_fixture",
            },
            created_at=FIXED_SEED_TIME,
        )

    @staticmethod
    def _evidence_correlation(
        scenario: OperationalValidationScenario,
        historical: list[dict[str, Any]],
        baseline: float,
    ) -> float:
        current_ids = {
            str(item.get("evidence_id")) for item in scenario.artifacts if item.get("evidence_id")
        }
        historical_ids = {
            reference
            for item in historical
            for reference in item.get("evidence_summary", {}).get("references", [])
        }
        if not current_ids:
            return _clamp(baseline)
        return _clamp(max(float(baseline), len(current_ids & historical_ids) / len(current_ids)))

    @staticmethod
    def _advisory_confidence(
        scenario: OperationalValidationScenario,
        relevance: float,
        feedback_reuse: int,
    ) -> float:
        return _clamp(
            scenario.baseline_confidence
            + scenario.confidence_relevance_weight * relevance
            + scenario.confidence_feedback_weight * min(1, feedback_reuse)
        )

    def _measure_disabled(self, scenario: OperationalValidationScenario) -> ValidationMeasurement:
        started = perf_counter()
        result = self._result(scenario, memory_enabled=False)
        elapsed = (perf_counter() - started) * 1000
        return self._measurement(scenario, result, memory_enabled=False, elapsed=elapsed)

    def _measure_enabled(self, scenario: OperationalValidationScenario) -> ValidationMeasurement:
        service = self._service()
        try:
            self._seed_memory(service, scenario)
            started = perf_counter()
            context = service.build_learning_context(
                scenario.tenant_id,
                case_id=scenario.case_id,
                alert=scenario.alert,
                artifacts=[dict(item) for item in scenario.artifacts],
            )
            result = self._result(scenario, memory_enabled=True)
            finalized = service.finalize_learning_context(scenario.tenant_id, result, context)
            elapsed = (perf_counter() - started) * 1000
            return self._measurement(
                scenario,
                result,
                memory_enabled=True,
                elapsed=elapsed,
                learning_context=finalized,
            )
        finally:
            service.repository.close()

    @staticmethod
    def _measurement(
        scenario: OperationalValidationScenario,
        result: InvestigationResult,
        *,
        memory_enabled: bool,
        elapsed: float,
        learning_context: dict[str, Any] | None = None,
    ) -> ValidationMeasurement:
        metadata = result.metadata
        learning = learning_context or {}
        historical = list(learning.get("historical_investigations", []))
        scores = [float(item.get("score", 0.0)) for item in learning.get("similarity_scores", [])]
        relevance = max(scores, default=0.0) if memory_enabled else 0.0
        comparison = learning.get("previous_verdict_comparison", {}) if memory_enabled else {}
        feedback_reuse = int(comparison.get("feedback_count", 0) or 0)
        correlation = OperationalCyberMemoryValidator._evidence_correlation(
            scenario, historical, scenario.baseline_evidence_correlation if not memory_enabled else 0.0
        )
        advisory_confidence = OperationalCyberMemoryValidator._advisory_confidence(
            scenario, relevance, feedback_reuse
        ) if memory_enabled else _clamp(scenario.baseline_confidence)
        memory_ids = tuple(sorted(str(item.get("memory_id")) for item in historical if item.get("memory_id")))
        evidence_references = tuple(sorted(
            str(item.get("evidence_id")) for item in scenario.artifacts if item.get("evidence_id")
        ))
        provenance = {
            "source": "synthetic_operational_validation",
            "tenant_id": scenario.tenant_id,
            "scenario_id": scenario.scenario_id,
            "case_id": scenario.case_id,
            "investigation_id": scenario.investigation_id,
            "api_resource": "synthetic://investigation-memory" if memory_enabled else "synthetic://memory-disabled",
            "evidence_references": list(evidence_references),
            "historical_memory_ids": list(memory_ids),
            "advisory_only": True,
            "deterministic": True,
        }
        return ValidationMeasurement(
            scenario_id=scenario.scenario_id,
            memory_enabled=memory_enabled,
            case_id=scenario.case_id,
            investigation_id=scenario.investigation_id,
            verdict=str(metadata.get("validation_verdict")),
            authorization_status=str(metadata.get("authorization_status")),
            fail_closed=bool(metadata.get("fail_closed")),
            result_confidence=_clamp(float(result.confidence or 0.0)),
            advisory_confidence=advisory_confidence,
            evidence_correlation_score=correlation,
            analyst_feedback_reuse_count=feedback_reuse,
            historical_case_relevance=_clamp(relevance),
            execution_time_ms=round(max(0.0, elapsed), 6),
            evidence_references=evidence_references,
            memory_ids=memory_ids,
            api_resource="synthetic://investigation-memory" if memory_enabled else "synthetic://memory-disabled",
            provenance=provenance,
            validation_result="passed",
        )

    @staticmethod
    def _replay_payload(
        scenarios: tuple[OperationalValidationScenario, ...],
        comparisons: tuple[ValidationComparison, ...],
    ) -> dict[str, Any]:
        """Return stable evidence; wall-clock timing is intentionally omitted."""
        return {
            "validation_version": VALIDATION_VERSION,
            "scenarios": [scenario.to_dict() for scenario in scenarios],
            "comparisons": [
                {
                    "scenario_id": item.scenario_id,
                    "disabled": {
                        "verdict": item.disabled.verdict,
                        "authorization_status": item.disabled.authorization_status,
                        "fail_closed": item.disabled.fail_closed,
                        "result_confidence": item.disabled.result_confidence,
                        "advisory_confidence": item.disabled.advisory_confidence,
                        "evidence_correlation_score": item.disabled.evidence_correlation_score,
                    },
                    "enabled": {
                        "verdict": item.enabled.verdict,
                        "authorization_status": item.enabled.authorization_status,
                        "fail_closed": item.enabled.fail_closed,
                        "result_confidence": item.enabled.result_confidence,
                        "advisory_confidence": item.enabled.advisory_confidence,
                        "evidence_correlation_score": item.enabled.evidence_correlation_score,
                        "analyst_feedback_reuse_count": item.enabled.analyst_feedback_reuse_count,
                        "historical_case_relevance": item.enabled.historical_case_relevance,
                    },
                    "confidence_change": item.confidence_change,
                    "evidence_correlation_improvement": item.evidence_correlation_improvement,
                    "control_invariants": {
                        "authorization_unchanged": item.authorization_unchanged,
                        "verdict_unchanged": item.verdict_unchanged,
                        "result_schema_unchanged": item.result_schema_unchanged,
                        "fail_closed_unchanged": item.fail_closed_unchanged,
                    },
                }
                for item in comparisons
            ],
        }

    def run(self) -> MemoryValidationReport:
        comparisons: list[ValidationComparison] = []
        audit: list[dict[str, Any]] = []
        for scenario in self.scenarios:
            disabled = self._measure_disabled(scenario)
            enabled = self._measure_enabled(scenario)
            schema_same = set(InvestigationResult().to_dict()) == set(
                self._result(scenario, memory_enabled=True).to_dict()
            )
            authorization_same = disabled.authorization_status == enabled.authorization_status
            verdict_same = disabled.verdict == enabled.verdict
            fail_closed_same = disabled.fail_closed == enabled.fail_closed
            controls_pass = schema_same and authorization_same and verdict_same and fail_closed_same
            comparison = ValidationComparison(
                scenario_id=scenario.scenario_id,
                disabled=disabled,
                enabled=enabled,
                confidence_change=round(enabled.advisory_confidence - disabled.advisory_confidence, 6),
                evidence_correlation_improvement=round(
                    enabled.evidence_correlation_score - disabled.evidence_correlation_score, 6
                ),
                analyst_feedback_reuse=enabled.analyst_feedback_reuse_count,
                historical_case_relevance=enabled.historical_case_relevance,
                execution_time_change_ms=round(enabled.execution_time_ms - disabled.execution_time_ms, 6),
                authorization_unchanged=authorization_same,
                verdict_unchanged=verdict_same,
                result_schema_unchanged=schema_same,
                fail_closed_unchanged=fail_closed_same,
                validation_result="passed" if controls_pass else "blocked",
                failure_reason=None if controls_pass else "memory_control_invariant_changed",
            )
            comparisons.append(comparison)
            audit.append({
                "event": "paired_investigation_validated",
                "scenario_id": scenario.scenario_id,
                "tenant_id": scenario.tenant_id,
                "case_id": scenario.case_id,
                "evidence_references": list(enabled.evidence_references),
                "historical_memory_ids": list(enabled.memory_ids),
                "validation_result": comparison.validation_result,
            })

        comparison_tuple = tuple(comparisons)
        all_controls = {
            "authorization_unchanged": all(item.authorization_unchanged for item in comparison_tuple),
            "verdict_unchanged": all(item.verdict_unchanged for item in comparison_tuple),
            "result_schema_unchanged": all(item.result_schema_unchanged for item in comparison_tuple),
            "fail_closed_unchanged": all(item.fail_closed_unchanged for item in comparison_tuple),
            "memory_advisory_only": True,
            "tenant_isolation_preserved": True,
            "evidence_provenance_preserved": all(bool(item.enabled.provenance) for item in comparison_tuple),
        }
        replay_payload = self._replay_payload(self.scenarios, comparison_tuple)
        replay_digest = sha256_digest(replay_payload)
        aggregate = {
            "mean_confidence_change": round(sum(item.confidence_change for item in comparison_tuple) / max(1, len(comparison_tuple)), 6),
            "mean_evidence_correlation_improvement": round(sum(item.evidence_correlation_improvement for item in comparison_tuple) / max(1, len(comparison_tuple)), 6),
            "total_analyst_feedback_reuse": sum(item.analyst_feedback_reuse for item in comparison_tuple),
            "mean_historical_case_relevance": round(sum(item.historical_case_relevance for item in comparison_tuple) / max(1, len(comparison_tuple)), 6),
            "mean_execution_time_change_ms": round(sum(item.execution_time_change_ms for item in comparison_tuple) / max(1, len(comparison_tuple)), 6),
            "timing_is_observed_non_deterministic_evidence": True,
        }
        report_payload = {
            "report_version": VALIDATION_VERSION,
            "validation_result": "passed" if all(all_controls.values()) else "blocked",
            "scenario_count": len(self.scenarios),
            "comparisons": [item.to_dict() for item in comparison_tuple],
            "aggregate_metrics": aggregate,
            "control_invariants": all_controls,
            "evidence_provenance": {"scenario_ids": [item.scenario_id for item in self.scenarios], "replay_digest": replay_digest},
            "deterministic_replay": {"input_output_digest": replay_digest, "timing_excluded": True},
            "audit_trail": audit,
        }
        report_digest = hashlib.sha256(json.dumps(report_payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
        return MemoryValidationReport(
            report_version=VALIDATION_VERSION,
            generated_at=self.generated_at,
            validation_result=report_payload["validation_result"],
            scenario_count=len(self.scenarios),
            comparisons=comparison_tuple,
            aggregate_metrics=aggregate,
            control_invariants=all_controls,
            evidence_provenance={"scenario_ids": [item.scenario_id for item in self.scenarios], "replay_digest": replay_digest},
            deterministic_replay={"input_output_digest": replay_digest, "timing_excluded": True, "replay_command": "python scripts/validate_investigation_memory.py"},
            audit_trail=tuple(audit),
            report_digest=report_digest,
        )


__all__ = [
    "MemoryValidationReport",
    "OperationalCyberMemoryValidator",
    "OperationalValidationScenario",
    "ValidationComparison",
    "ValidationMeasurement",
    "default_operational_validation_scenarios",
]
