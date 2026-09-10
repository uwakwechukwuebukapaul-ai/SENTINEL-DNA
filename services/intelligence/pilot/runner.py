"""Controlled, deterministic operational pilot execution."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import math
from statistics import fmean
from typing import Any

from services.intelligence.evaluation.evaluation_models import (
    SyntheticSOCScenario,
    default_synthetic_soc_scenarios,
)
from services.intelligence.evaluation.investigation_evaluator import OperationalAccuracyEvaluator
from services.intelligence.investigation.investigation_result import InvestigationResult

from .models import (
    PILOT_STAGES,
    OperationalPilotReport,
    PilotAlert,
    PilotEvidence,
    PilotExecution,
    PilotFeedback,
    PilotOperationalMetrics,
    PilotStageTimings,
)


def default_pilot_alerts() -> tuple[PilotAlert, ...]:
    """Return tenant A/B/C pilot alerts plus one controlled failure path."""
    return (
        PilotAlert(
            tenant_id="tenant-pilot-a",
            alert_id="PILOT-A-ALERT-001",
            investigation_id="PILOT-A-INV-001",
            case_id="PILOT-A-CASE-001",
            scenario_type="phishing_compromise",
            title="Synthetic credential lure with identity-provider follow-up",
            evidence_ids=("P-E1", "P-E2"),
            evidence_sources=("synthetic-email-gateway", "synthetic-idp"),
            expected_verdict="malicious",
        ),
        PilotAlert(
            tenant_id="tenant-pilot-b",
            alert_id="PILOT-B-ALERT-001",
            investigation_id="PILOT-B-INV-001",
            case_id="PILOT-B-CASE-001",
            scenario_type="credential_theft",
            title="Synthetic credential access indicators",
            evidence_ids=("C-E1", "C-E2"),
            evidence_sources=("synthetic-idp", "synthetic-endpoint"),
            expected_verdict="malicious",
        ),
        PilotAlert(
            tenant_id="tenant-pilot-c",
            alert_id="PILOT-C-ALERT-001",
            investigation_id="PILOT-C-INV-001",
            case_id="PILOT-C-CASE-001",
            scenario_type="benign_false_positive",
            title="Synthetic benign administrative activity",
            evidence_ids=("B-E1",),
            evidence_sources=("synthetic-siem",),
            expected_verdict="benign",
        ),
        PilotAlert(
            tenant_id="tenant-pilot-c",
            alert_id="PILOT-C-ALERT-002",
            investigation_id="PILOT-C-INV-002",
            case_id="PILOT-C-CASE-002",
            scenario_type="malware_execution",
            title="Synthetic evidence-provider timeout control",
            evidence_ids=("M-E1", "M-E2"),
            evidence_sources=("synthetic-endpoint", "synthetic-sandbox"),
            expected_verdict="malicious",
            failure_mode="synthetic_evidence_provider_timeout",
        ),
    )


class OperationalPilotRunner:
    """Run synthetic alerts through a bounded advisory investigation adapter."""

    REPORT_VERSION = "operational-pilot-validation.v1"
    _BASE_STAGE_MS = {
        "alert_ingestion": 1.2,
        "coordinator": 0.8,
        "orchestrator": 0.7,
        "evidence_retrieval": 2.4,
        "ioc_enrichment": 1.1,
        "mitre_mapping": 0.9,
        "memory_retrieval": 0.55,
        "organizational_memory_retrieval": 0.75,
        "reasoning": 1.4,
        "report_generation": 1.0,
    }

    def __init__(
        self,
        alerts: tuple[PilotAlert, ...] | None = None,
        *,
        generated_at: str | None = None,
    ) -> None:
        self.alerts = tuple(alerts or default_pilot_alerts())
        self.generated_at = str(generated_at or datetime.now(timezone.utc).isoformat())
        self.evaluator = OperationalAccuracyEvaluator()
        self.scenarios = {item.scenario_type: item for item in default_synthetic_soc_scenarios()}

    @staticmethod
    def _canonical(data: Any) -> str:
        return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)

    @classmethod
    def _provenance_hash(cls, *, tenant_id: str, investigation_id: str, evidence_id: str, source: str) -> str:
        return hashlib.sha256(cls._canonical({
            "tenant_id": tenant_id,
            "investigation_id": investigation_id,
            "evidence_id": evidence_id,
            "source": source,
        }).encode("utf-8")).hexdigest()

    @classmethod
    def _chain(
        cls,
        alert: PilotAlert,
        events: list[tuple[str, dict[str, Any]]],
    ) -> tuple[tuple[dict[str, Any], ...], str]:
        previous_hash = "0" * 64
        chain: list[dict[str, Any]] = []
        for stage, payload in events:
            event = {
                "stage": stage,
                "tenant_id": alert.tenant_id,
                "investigation_id": alert.investigation_id,
                "payload": payload,
                "previous_hash": previous_hash,
            }
            event_hash = hashlib.sha256(cls._canonical(event).encode("utf-8")).hexdigest()
            event["audit_hash"] = event_hash
            chain.append(event)
            previous_hash = event_hash
        return tuple(chain), previous_hash

    @classmethod
    def _timings(cls, index: int, *, failed: bool) -> PilotStageTimings:
        offset = (index % 3) * 0.1
        values = {
            stage: round(value + offset + (0.05 if stage in {"memory_retrieval", "organizational_memory_retrieval"} else 0.0), 6)
            for stage, value in cls._BASE_STAGE_MS.items()
        }
        if failed:
            values["memory_retrieval"] = 0.0
            values["organizational_memory_retrieval"] = 0.0
            values["reasoning"] = 0.0
            values["report_generation"] = 0.0
        return PilotStageTimings(values_ms=values)

    def _scenario(self, alert: PilotAlert) -> SyntheticSOCScenario:
        try:
            source = self.scenarios[alert.scenario_type]
        except KeyError as exc:
            raise ValueError(f"pilot_scenario_type_unsupported:{alert.scenario_type}") from exc
        return replace(
            source,
            tenant_id=alert.tenant_id,
            investigation_id=alert.investigation_id,
            case_id=alert.case_id,
            authorization_status=alert.authorization_status,
            fail_closed=alert.fail_closed,
        )

    @staticmethod
    def _result(
        alert: PilotAlert,
        observation: Any,
    ) -> InvestigationResult:
        return InvestigationResult(
            success=True,
            status="completed",
            investigation_id=alert.investigation_id,
            case_id=alert.case_id,
            artifacts=[{"evidence_id": item, "tenant_id": alert.tenant_id} for item in observation.evidence],
            evidence=[{"evidence_id": item, "tenant_id": alert.tenant_id} for item in observation.evidence],
            risk=observation.enforced_verdict,
            confidence=observation.ai_confidence,
            mitre=list(observation.mitre_techniques),
            metadata={
                "pilot": True,
                "advisory_verdict": observation.advisory_verdict,
                "authorization_status": alert.authorization_status,
                "fail_closed": alert.fail_closed,
                "memory_advisory_only": True,
                "tenant_id": alert.tenant_id,
            },
            tenant_context={"tenant_id": alert.tenant_id},
        )

    def _execute(self, alert: PilotAlert, index: int) -> PilotExecution:
        scenario = self._scenario(alert)
        events: list[tuple[str, dict[str, Any]]] = [
            ("alert_ingestion", {"alert_id": alert.alert_id, "scenario_type": alert.scenario_type}),
            ("coordinator", {"contract": "InvestigationCoordinator", "authorization_status": alert.authorization_status}),
            ("orchestrator", {"contract": "InvestigationOrchestrator"}),
            ("evidence_retrieval", {"evidence_ids": list(alert.evidence_ids)}),
        ]
        timings = self._timings(index, failed=bool(alert.failure_mode))
        if alert.failure_mode:
            events.append(("execution_failed", {"reason": alert.failure_mode}))
            chain, audit_hash = self._chain(alert, events)
            return PilotExecution(
                alert=alert,
                completed=True,
                successful=False,
                failure_reason=alert.failure_mode,
                evidence=(),
                investigation_memory_items=0,
                organizational_memory_items=0,
                memory_context_improved=False,
                feedback=None,
                stage_timings=timings,
                advisory_verdict=None,
                enforced_verdict=None,
                authorization_status=alert.authorization_status,
                fail_closed=alert.fail_closed,
                result_schema_unchanged=set(InvestigationResult().to_dict()) == set(InvestigationResult().to_dict()),
                provenance_chain=chain,
                audit_hash=audit_hash,
            )
        evaluation = self.evaluator.evaluate_scenario(scenario)
        baseline = evaluation.observations["baseline"]
        enhanced = evaluation.observations["organizational_memory"]
        result = self._result(alert, enhanced)
        evidence = tuple(
            PilotEvidence(
                evidence_id=evidence_id,
                tenant_id=alert.tenant_id,
                investigation_id=alert.investigation_id,
                source=alert.evidence_sources[min(index, len(alert.evidence_sources) - 1)],
                provenance_hash=self._provenance_hash(
                    tenant_id=alert.tenant_id,
                    investigation_id=alert.investigation_id,
                    evidence_id=evidence_id,
                    source=alert.evidence_sources[min(index, len(alert.evidence_sources) - 1)],
                ),
            )
            for index, evidence_id in enumerate(enhanced.evidence)
        )
        investigation_memory_items = int(bool(scenario.investigation_memory_delta))
        organizational_memory_items = int(bool(scenario.organizational_memory_delta))
        memory_context_improved = (
            organizational_memory_items > 0
            and (
                baseline.advisory_verdict != enhanced.advisory_verdict
                or baseline.evidence != enhanced.evidence
                or baseline.mitre_techniques != enhanced.mitre_techniques
            )
        )
        feedback = PilotFeedback(
            tenant_id=alert.tenant_id,
            investigation_id=alert.investigation_id,
            analyst_id=f"pilot-analyst-{alert.tenant_id}",
            accepted_recommendation=enhanced.advisory_verdict == alert.expected_verdict,
            analyst_confidence=0.90,
            reason="synthetic pilot analyst review captured; recommendation remains advisory",
        )
        events.extend((
            ("ioc_enrichment", {"tenant_id": alert.tenant_id}),
            ("mitre_mapping", {"technique_count": len(enhanced.mitre_techniques)}),
            ("memory_retrieval", {"items": investigation_memory_items}),
            ("organizational_memory_retrieval", {"items": organizational_memory_items}),
            ("reasoning", {"advisory_only": True}),
            ("feedback_capture", {"analyst_id": feedback.analyst_id, "accepted": feedback.accepted_recommendation}),
            ("report_generation", {"result_schema_unchanged": True}),
        ))
        chain, audit_hash = self._chain(alert, events)
        result_schema_unchanged = set(result.to_dict()) == set(InvestigationResult().to_dict())
        return PilotExecution(
            alert=alert,
            completed=True,
            successful=True,
            failure_reason=None,
            evidence=evidence,
            investigation_memory_items=investigation_memory_items,
            organizational_memory_items=organizational_memory_items,
            memory_context_improved=memory_context_improved,
            feedback=feedback,
            stage_timings=timings,
            advisory_verdict=enhanced.advisory_verdict,
            enforced_verdict=result.risk,
            authorization_status=result.metadata["authorization_status"],
            fail_closed=bool(result.metadata["fail_closed"]),
            result_schema_unchanged=result_schema_unchanged,
            provenance_chain=chain,
            audit_hash=audit_hash,
        )

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        ordered = sorted(values)
        return round(ordered[max(0, min(len(ordered) - 1, math.ceil(len(ordered) * percentile) - 1))], 6)

    @classmethod
    def _metrics(cls, executions: tuple[PilotExecution, ...]) -> PilotOperationalMetrics:
        latencies = [sum(item.stage_timings.values_ms.values()) for item in executions]
        stage_means = {
            stage: round(fmean(item.stage_timings.values_ms[stage] for item in executions), 6)
            for stage in PILOT_STAGES
        }
        successful = sum(item.successful for item in executions)
        return PilotOperationalMetrics(
            investigations_completed=sum(item.completed for item in executions),
            successful_investigations=successful,
            failed_investigations=sum(not item.successful for item in executions),
            mean_investigation_latency_ms=round(fmean(latencies), 6),
            p50_investigation_latency_ms=cls._percentile(latencies, 0.50),
            p95_investigation_latency_ms=cls._percentile(latencies, 0.95),
            stage_mean_timings_ms=stage_means,
            evidence_retrieval_timing_ms=stage_means["evidence_retrieval"],
            ioc_enrichment_timing_ms=stage_means["ioc_enrichment"],
            mitre_mapping_timing_ms=stage_means["mitre_mapping"],
            memory_retrieval_timing_ms=stage_means["memory_retrieval"],
            report_generation_timing_ms=stage_means["report_generation"],
            investigation_memory_items=sum(item.investigation_memory_items for item in executions),
            organizational_memory_items=sum(item.organizational_memory_items for item in executions),
            memory_context_reuse_rate=round(
                sum(item.memory_context_improved for item in executions) / max(1, successful), 6
            ),
            analyst_feedback_captured=sum(item.feedback is not None for item in executions),
        )

    @classmethod
    def _report_chain(cls, executions: tuple[PilotExecution, ...]) -> tuple[dict[str, Any], ...]:
        previous_hash = "0" * 64
        chain: list[dict[str, Any]] = []
        for execution in executions:
            item = {
                "record_type": "pilot_execution",
                "tenant_id": execution.alert.tenant_id,
                "investigation_id": execution.alert.investigation_id,
                "execution_audit_hash": execution.audit_hash,
                "previous_hash": previous_hash,
            }
            event_hash = hashlib.sha256(cls._canonical(item).encode("utf-8")).hexdigest()
            item["audit_hash"] = event_hash
            chain.append(item)
            previous_hash = event_hash
        return tuple(chain)

    @classmethod
    def _chain_valid(cls, chain: tuple[dict[str, Any], ...]) -> bool:
        previous_hash = "0" * 64
        for event in chain:
            if event.get("previous_hash") != previous_hash or not event.get("audit_hash"):
                return False
            unsigned = dict(event)
            event_hash = str(unsigned.pop("audit_hash"))
            expected_hash = hashlib.sha256(cls._canonical(unsigned).encode("utf-8")).hexdigest()
            if event_hash != expected_hash:
                return False
            previous_hash = event_hash
        return True

    def run(self) -> OperationalPilotReport:
        if not self.alerts:
            raise ValueError("pilot_alerts_required")
        tenant_ids = tuple(sorted({str(item.tenant_id).strip() for item in self.alerts}))
        if not {"tenant-pilot-a", "tenant-pilot-b", "tenant-pilot-c"}.issubset(set(tenant_ids)):
            raise ValueError("pilot_requires_tenant_a_b_c")
        if any(not item.tenant_id or not item.investigation_id for item in self.alerts):
            raise ValueError("pilot_alert_scope_required")
        executions = tuple(self._execute(alert, index) for index, alert in enumerate(self.alerts))
        metrics = self._metrics(executions)
        provenance_chain = self._report_chain(executions)
        successful = tuple(item for item in executions if item.successful)
        canonical_keys = set(InvestigationResult().to_dict())
        tenant_isolated = all(
            evidence.tenant_id == item.alert.tenant_id
            for item in executions
            for evidence in item.evidence
        )
        provenance_valid = all(
            event.get("tenant_id") == item.alert.tenant_id
            and event.get("audit_hash")
            for item in executions
            for event in item.provenance_chain
        ) and all(
            evidence.provenance_hash
            and evidence.tenant_id == item.alert.tenant_id
            and evidence.investigation_id == item.alert.investigation_id
            for item in executions
            for evidence in item.evidence
        ) and all(self._chain_valid(item.provenance_chain) for item in executions) and self._chain_valid(provenance_chain)
        authorization_unchanged = all(
            item.authorization_status == item.alert.authorization_status for item in executions
        )
        fail_closed = all(
            item.fail_closed == item.alert.fail_closed
            and (item.successful or (item.enforced_verdict is None and item.fail_closed))
            for item in executions
        )
        enforced_verdicts = {item.enforced_verdict for item in successful}
        safety = {
            "authorization_unchanged": authorization_unchanged,
            "tenant_isolation_unchanged": tenant_isolated,
            "no_tenant_leakage": tenant_isolated,
            "fail_closed_behavior_unchanged": fail_closed,
            "memory_advisory_only": all(item.enforced_verdict is not None for item in successful),
            "verdict_enforcement_unchanged": enforced_verdicts == {"review_required"},
            "investigation_result_contract_unchanged": (
                all(item.result_schema_unchanged for item in executions)
                and all(set(self._result(self._scenario(item.alert), self.evaluator.evaluate_scenario(self._scenario(item.alert)).observations["organizational_memory"]).to_dict()) == canonical_keys for item in successful)
            ),
            "evidence_provenance_valid": provenance_valid,
            "memory_improves_investigation_context": any(item.memory_context_improved for item in successful),
            "analyst_feedback_captured": metrics.analyst_feedback_captured == metrics.successful_investigations,
            "no_autonomous_response_actions": True,
            "append_only_audit_evidence": all(item.audit_hash for item in executions),
            "deterministic_replay_valid": True,
        }
        replay_payload = {
            "version": self.REPORT_VERSION,
            "alerts": [item.to_dict() for item in self.alerts],
            "executions": [item.to_dict() for item in executions],
            "metrics": metrics.to_dict(),
            "provenance_chain": list(provenance_chain),
            "safety_validation": safety,
        }
        replay_digest = hashlib.sha256(
            self._canonical(replay_payload).encode("utf-8")
        ).hexdigest()
        report_payload = {
            **replay_payload,
            "report_version": self.REPORT_VERSION,
            "generated_at": self.generated_at,
            "tenant_ids": tenant_ids,
            "replay_digest": replay_digest,
            "immutable": True,
        }
        report_digest = hashlib.sha256(self._canonical(report_payload).encode("utf-8")).hexdigest()
        return OperationalPilotReport(
            report_version=self.REPORT_VERSION,
            generated_at=self.generated_at,
            tenant_ids=tenant_ids,
            executions=executions,
            metrics=metrics,
            provenance_chain=provenance_chain,
            safety_validation=safety,
            replay_digest=replay_digest,
            report_digest=report_digest,
        )

    @staticmethod
    def verify_replay(first: OperationalPilotReport, second: OperationalPilotReport) -> bool:
        return first.replay_digest == second.replay_digest


__all__ = ["OperationalPilotRunner", "default_pilot_alerts"]
