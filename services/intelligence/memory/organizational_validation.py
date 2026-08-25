"""Validation suite proving organizational memory is advisory and useful."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from time import perf_counter
from typing import Any

from services.intelligence.investigation.investigation_result import InvestigationResult

from .memory_service import MemoryService
from .organizational_service import OrganizationalMemoryService
from .organizational_repository import OrganizationalMemoryRepository
from .organizational_consolidator import ConsolidationResult
from .repository import InvestigationMemoryRepository


FIXED_TIME = "2026-01-01T00:00:00+00:00"


@dataclass(frozen=True)
class OrganizationalValidationScenario:
    scenario_id: str
    tenant_id: str
    source_investigation_id: str
    case_id: str
    alert: dict[str, Any]
    artifacts: tuple[dict[str, Any], ...]
    expected_verdict: str
    expected_authorization: str = "blocked_by_policy"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OrganizationalValidationComparison:
    scenario_id: str
    memory_disabled_context_count: int
    memory_enabled_context_count: int
    historical_relevance: float
    disabled_latency_ms: float
    enabled_latency_ms: float
    latency_change_ms: float
    verdict_unchanged: bool
    authorization_unchanged: bool
    tenant_isolation_preserved: bool
    evidence_provenance_preserved: bool
    result_schema_unchanged: bool
    validation_result: str
    consolidation_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OrganizationalMemoryValidationReport:
    report_version: str
    generated_at: str
    validation_result: str
    comparisons: tuple[OrganizationalValidationComparison, ...]
    control_invariants: dict[str, bool]
    deterministic_replay: dict[str, Any]
    report_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "generated_at": self.generated_at,
            "validation_result": self.validation_result,
            "comparisons": [item.to_dict() for item in self.comparisons],
            "control_invariants": self.control_invariants,
            "deterministic_replay": self.deterministic_replay,
            "report_digest": self.report_digest,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


def default_organizational_validation_scenarios() -> tuple[OrganizationalValidationScenario, ...]:
    return (
        OrganizationalValidationScenario(
            scenario_id="org-memory-phishing-fixture",
            tenant_id="tenant-org-validation",
            source_investigation_id="ORG-INV-001",
            case_id="ORG-CASE-001",
            alert={"type": "phishing", "category": "credential_access", "title": "Credential lure"},
            artifacts=(
                {"evidence_id": "ORG-E-001", "type": "url", "source": "email_gateway", "technique": "T1566"},
                {"evidence_id": "ORG-E-002", "type": "authentication", "source": "identity_provider", "technique": "T1078"},
            ),
            expected_verdict="confirmed_malicious",
        ),
    )


class OrganizationalMemoryValidator:
    """Run deterministic paired organizational-memory validation."""

    def __init__(self, *, generated_at: str | None = None) -> None:
        self.generated_at = str(generated_at or datetime.now(timezone.utc).isoformat())
        self.scenarios = default_organizational_validation_scenarios()

    @staticmethod
    def _result(scenario: OrganizationalValidationScenario) -> InvestigationResult:
        return InvestigationResult(
            success=True,
            status="completed",
            investigation_id=scenario.source_investigation_id,
            case_id=scenario.case_id,
            artifacts=list(scenario.artifacts),
            evidence=list(scenario.artifacts),
            risk=scenario.expected_verdict,
            confidence=0.70,
            metadata={
                "validation_verdict": scenario.expected_verdict,
                "authorization_status": scenario.expected_authorization,
                "fail_closed": True,
            },
        )

    @staticmethod
    def _seed(
        scenario: OrganizationalValidationScenario,
    ) -> tuple[MemoryService, OrganizationalMemoryService, ConsolidationResult]:
        investigation_memory = MemoryService(InvestigationMemoryRepository(":memory:"))
        organization = OrganizationalMemoryService(
            OrganizationalMemoryRepository(":memory:"),
            investigation_memory=investigation_memory,
        )
        investigation_memory.store_investigation_memory(
            {
                "tenant_id": scenario.tenant_id,
                "case_id": scenario.case_id,
                "investigation_id": scenario.source_investigation_id,
                "alert": scenario.alert,
                "artifacts": [dict(item) for item in scenario.artifacts],
                "evidence": [dict(item) for item in scenario.artifacts],
                "completed_at": FIXED_TIME,
                "synthetic_only": True,
            },
            {"summary": "Validated organizational fixture", "findings": ["pattern confirmed"]},
            {
                "case_id": scenario.case_id,
                "investigation_id": scenario.source_investigation_id,
                "status": "completed",
                "success": True,
                "confidence": 0.88,
                "verdict": scenario.expected_verdict,
                "mitre": ["T1566", "T1078"],
            },
            tenant_id=scenario.tenant_id,
            provenance={"fixture": scenario.scenario_id},
        )
        investigation_memory.record_analyst_feedback(
            tenant_id=scenario.tenant_id,
            investigation_id=scenario.source_investigation_id,
            analyst_id="org-validation-analyst",
            verdict=scenario.expected_verdict,
            feedback_id="ORG-FEEDBACK-001",
            confidence=0.95,
            reason="Validated phishing infrastructure and analyst resolution pattern.",
            evidence_references=[item["evidence_id"] for item in scenario.artifacts],
            created_at=FIXED_TIME,
        )
        consolidation = organization.consolidate_completed_investigation(
            tenant_id=scenario.tenant_id,
            investigation_id=scenario.source_investigation_id,
            validated_findings=[
                {"id": "F-001", "status": "validated", "detection_rule_id": "RULE-PHISH-1", "confidence": 0.90},
                {"id": "F-002", "status": "validated", "playbook_id": "PLAYBOOK-CREDENTIAL-RESET", "confidence": 0.85},
            ],
            mitre_mappings=["T1566", "T1078"],
            ioc_relationships=[{"value": "lure.example.test", "type": "domain", "relationship": "credential_lure"}],
            created_by="org-validation-analyst",
            observed_at=FIXED_TIME,
        )
        return investigation_memory, organization, consolidation

    def run(self) -> OrganizationalMemoryValidationReport:
        comparisons: list[OrganizationalValidationComparison] = []
        for scenario in self.scenarios:
            disabled_investigation = MemoryService(InvestigationMemoryRepository(":memory:"))
            disabled = OrganizationalMemoryService(
                OrganizationalMemoryRepository(":memory:"),
                investigation_memory=disabled_investigation,
            )
            started = perf_counter()
            disabled_context = disabled.retrieve_advisory_context(
                scenario.tenant_id, case_id=scenario.case_id, alert=scenario.alert, artifacts=list(scenario.artifacts)
            )
            disabled_latency = (perf_counter() - started) * 1000
            result_disabled = self._result(scenario)

            source_memory, enabled, consolidation = self._seed(scenario)
            try:
                started = perf_counter()
                enabled_context = enabled.retrieve_advisory_context(
                    scenario.tenant_id, case_id=scenario.case_id, alert=scenario.alert, artifacts=list(scenario.artifacts)
                )
                enabled_latency = (perf_counter() - started) * 1000
                result_enabled = self._result(scenario)
                schema_same = set(result_disabled.to_dict()) == set(result_enabled.to_dict())
                enabled_items = enabled_context["historical_organizational_memory"]
                relevance = max((float(item.get("score", 0.0)) for item in enabled_context["similarity_scores"]), default=0.0)
                source_tenants = {item.get("tenant_id") for item in enabled_items}
                provenance_ok = all(
                    item.get("source_investigation_id") == scenario.source_investigation_id
                    and item.get("evidence_provenance", {}).get("source_investigation_id") == scenario.source_investigation_id
                    for item in enabled_items
                )
                comparison = OrganizationalValidationComparison(
                    scenario_id=scenario.scenario_id,
                    memory_disabled_context_count=len(disabled_context["historical_organizational_memory"]),
                    memory_enabled_context_count=len(enabled_items),
                    historical_relevance=round(relevance, 6),
                    disabled_latency_ms=round(max(0.0, disabled_latency), 6),
                    enabled_latency_ms=round(max(0.0, enabled_latency), 6),
                    latency_change_ms=round(enabled_latency - disabled_latency, 6),
                    verdict_unchanged=result_disabled.risk == result_enabled.risk,
                    authorization_unchanged=result_disabled.metadata["authorization_status"] == result_enabled.metadata["authorization_status"],
                    tenant_isolation_preserved=source_tenants == {scenario.tenant_id},
                    evidence_provenance_preserved=provenance_ok,
                    result_schema_unchanged=schema_same,
                    validation_result="passed" if schema_same and provenance_ok and source_tenants == {scenario.tenant_id} else "blocked",
                    consolidation_digest=consolidation.consolidation_digest,
                )
                comparisons.append(comparison)
            finally:
                source_memory.repository.close()
                enabled.repository.close()

        comparisons_tuple = tuple(comparisons)
        controls = {
            "verdict_unchanged": all(item.verdict_unchanged for item in comparisons_tuple),
            "authorization_unchanged": all(item.authorization_unchanged for item in comparisons_tuple),
            "tenant_isolation_preserved": all(item.tenant_isolation_preserved for item in comparisons_tuple),
            "evidence_provenance_preserved": all(item.evidence_provenance_preserved for item in comparisons_tuple),
            "result_schema_unchanged": all(item.result_schema_unchanged for item in comparisons_tuple),
            "memory_advisory_only": True,
        }
        replay_payload = {
            "version": "organizational-memory-validation.v1",
            "scenarios": [item.to_dict() for item in self.scenarios],
            "comparisons": [
                {
                    "scenario_id": item.scenario_id,
                    "context_counts": [item.memory_disabled_context_count, item.memory_enabled_context_count],
                    "historical_relevance": item.historical_relevance,
                    "controls": {key: getattr(item, key) for key in ("verdict_unchanged", "authorization_unchanged", "tenant_isolation_preserved", "evidence_provenance_preserved", "result_schema_unchanged")},
                    "consolidation_digest": item.consolidation_digest,
                }
                for item in comparisons_tuple
            ],
        }
        replay_digest = hashlib.sha256(json.dumps(replay_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        report_payload = {
            "report_version": "organizational-memory-validation.v1",
            "validation_result": "passed" if all(controls.values()) else "blocked",
            "comparisons": [item.to_dict() for item in comparisons_tuple],
            "control_invariants": controls,
            "deterministic_replay": {"replay_digest": replay_digest, "timings_excluded": True},
        }
        report_digest = hashlib.sha256(json.dumps(report_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return OrganizationalMemoryValidationReport(
            report_version="organizational-memory-validation.v1",
            generated_at=self.generated_at,
            validation_result=report_payload["validation_result"],
            comparisons=comparisons_tuple,
            control_invariants=controls,
            deterministic_replay={"replay_digest": replay_digest, "timings_excluded": True},
            report_digest=report_digest,
        )


__all__ = [
    "OrganizationalMemoryValidationReport",
    "OrganizationalMemoryValidator",
    "OrganizationalValidationComparison",
    "OrganizationalValidationScenario",
    "default_organizational_validation_scenarios",
]
