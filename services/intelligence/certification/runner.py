"""Unified enterprise readiness certification runner."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import platform
from pathlib import Path
import subprocess
from typing import Any, Callable

from services.intelligence.evaluation.benchmark_runner import OperationalAccuracyBenchmarkRunner
from services.intelligence.memory.organizational_validation import OrganizationalMemoryValidator
from services.intelligence.memory.validation import OperationalCyberMemoryValidator
from services.intelligence.enterprise_proof import EnterpriseProofValidator
from services.intelligence.pilot import OperationalPilotRunner
from services.intelligence.telemetry import run_performance_benchmark
from services.billing.validation import BillingEntitlementValidationRunner

from .models import (
    CertificationControl,
    CertificationEvidence,
    CertificationFinding,
    CertificationMetric,
    CertificationReport,
)


class EnterpriseCertificationRunner:
    """Aggregate existing validation artifacts without adding decision authority."""

    REPORT_VERSION = "sentinel-dna-enterprise-certification.v1"
    FIXED_SOURCE_TIME = "2026-01-01T00:00:00+00:00"
    SOURCE_NAMES = (
        "investigation_memory",
        "organizational_cyber_memory",
        "operational_accuracy",
        "enterprise_proof",
        "controlled_operational_pilot",
        "performance_telemetry",
        "billing_entitlement_validation",
    )

    def __init__(
        self,
        *,
        generated_at: str | None = None,
        commit_sha: str | None = None,
        performance_iterations: int = 5,
    ) -> None:
        self.generated_at = str(generated_at or datetime.now(timezone.utc).isoformat())
        self.commit_sha = str(commit_sha or self._git_sha())
        self.performance_iterations = max(1, int(performance_iterations))

    @staticmethod
    def _canonical(data: Any) -> str:
        return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)

    @staticmethod
    def _git_sha() -> str:
        repository_root = Path(__file__).resolve().parents[3]
        try:
            completed = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repository_root,
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return completed.stdout.strip() or "unknown"
        except (OSError, subprocess.SubprocessError):
            return "unknown"

    @staticmethod
    def _source_replay(report: Any) -> str:
        if report is None:
            return ""
        if hasattr(report, "replay_digest"):
            return str(report.replay_digest)
        deterministic = getattr(report, "deterministic_replay", {}) or {}
        return str(
            deterministic.get("replay_digest")
            or deterministic.get("input_output_digest")
            or deterministic.get("input_digest")
            or ""
        )

    @staticmethod
    def _source_version(report: Any) -> str:
        if report is None:
            return "unknown"
        return str(getattr(report, "report_version", getattr(report, "benchmark_version", "unknown")))

    @staticmethod
    def _source_report_digest(report: Any) -> str:
        return str(getattr(report, "report_digest", "")) if report is not None else ""

    @staticmethod
    def _source_status(report: Any) -> str:
        if report is None:
            return "failed"
        for attribute in ("validation_result",):
            value = getattr(report, attribute, None)
            if value is not None:
                return "passed" if value == "passed" else "failed"
        for attribute in ("safety_validation", "control_invariants", "control_checks"):
            value = getattr(report, attribute, None)
            if value is not None:
                return "passed" if all(bool(item) for item in value.values()) else "failed"
        return "failed"

    def _collect_source(
        self,
        source: str,
        factory: Callable[[], Any],
        reports: dict[str, Any],
    ) -> CertificationEvidence:
        error: str | None = None
        try:
            report = factory()
        except Exception as exc:  # certification must fail closed if evidence cannot be collected
            report = None
            error = f"{type(exc).__name__}:{exc}"
        reports[source] = report
        replay_digest = self._source_replay(report)
        status = self._source_status(report)
        if error:
            status = "failed"
        summary: dict[str, Any] = {
            "status": status,
            "error": error,
        }
        for attribute in ("validation_result", "control_invariants", "safety_validation", "control_checks"):
            value = getattr(report, attribute, None) if report is not None else None
            if value is not None:
                summary[attribute] = value
        if source == "operational_accuracy" and report is not None:
            summary["memory_benefit_score"] = float(report.memory_benefit_score)
            summary["aggregate_metrics"] = {
                "baseline": report.aggregate_metrics.get("baseline", {}),
                "organizational_memory": report.aggregate_metrics.get("organizational_memory", {}),
            }
        if source == "controlled_operational_pilot" and report is not None:
            summary["metrics"] = report.metrics.to_dict()
        if source == "performance_telemetry" and report is not None:
            summary["component_statistics"] = report.component_statistics
        if source == "billing_entitlement_validation" and report is not None:
            summary["scenarios"] = report.scenarios
            summary["metrics"] = report.metrics
            summary["security_invariants"] = report.security_invariants
            summary["evidence_policy"] = report.evidence_policy
        references = (
            f"{source}:report_digest:{self._source_report_digest(report) or 'unavailable'}",
            f"{source}:replay_digest:{replay_digest or 'unavailable'}",
        )
        stable_evidence = {
            "source": source,
            "source_report_version": self._source_version(report),
            "status": status,
            "source_replay_digest": replay_digest,
            # Source report digests are retained as audit references above,
            # but observed timing can make them vary. Stable evidence identity
            # is anchored only to the source replay digest.
            "references": [f"{source}:replay_digest:{replay_digest or 'unavailable'}"],
        }
        evidence_digest = hashlib.sha256(self._canonical(stable_evidence).encode("utf-8")).hexdigest()
        return CertificationEvidence(
            evidence_id=f"CERT-EVIDENCE-{source.upper()}",
            source=source,
            source_report_version=self._source_version(report),
            status=status,
            source_report_digest=self._source_report_digest(report),
            source_replay_digest=replay_digest,
            evidence_digest=evidence_digest,
            references=references,
            summary=summary,
        )

    @staticmethod
    def _mapping(report: Any, *attributes: str) -> dict[str, bool]:
        if report is None:
            return {}
        for attribute in attributes:
            value = getattr(report, attribute, None)
            if isinstance(value, dict):
                return value
        return {}

    @classmethod
    def _control_value(cls, report: Any, *keys: str) -> bool:
        mapping = cls._mapping(report, "safety_validation", "control_invariants", "control_checks")
        return bool(mapping) and all(bool(mapping.get(key, False)) for key in keys)

    @staticmethod
    def _scenario_checks(scenario: dict[str, Any] | None, *keys: str) -> bool:
        if not scenario:
            return False
        checks = scenario.get("checks", {})
        return bool(scenario.get("status") == "passed") and all(bool(checks.get(key, False)) for key in keys)

    @staticmethod
    def _control(
        control_id: str,
        domain: str,
        name: str,
        passed: bool,
        evidence_ids: tuple[str, ...],
        rationale: str,
    ) -> CertificationControl:
        return CertificationControl(
            control_id=control_id,
            domain=domain,
            name=name,
            required=True,
            passed=bool(passed),
            evidence_ids=evidence_ids,
            rationale=rationale,
        )

    @staticmethod
    def _metric(
        metric_id: str,
        domain: str,
        name: str,
        value: float,
        unit: str,
        evidence_ids: tuple[str, ...],
        interpretation: str,
    ) -> CertificationMetric:
        return CertificationMetric(
            metric_id=metric_id,
            domain=domain,
            name=name,
            value=round(float(value), 6),
            unit=unit,
            evidence_ids=evidence_ids,
            interpretation=interpretation,
        )

    def run(self) -> CertificationReport:
        reports: dict[str, Any] = {}
        factories: tuple[tuple[str, Callable[[], Any]], ...] = (
            ("investigation_memory", lambda: OperationalCyberMemoryValidator(generated_at=self.generated_at).run()),
            ("organizational_cyber_memory", lambda: OrganizationalMemoryValidator(generated_at=self.generated_at).run()),
            ("operational_accuracy", lambda: OperationalAccuracyBenchmarkRunner(generated_at=self.generated_at).run()),
            ("enterprise_proof", lambda: EnterpriseProofValidator(generated_at=self.generated_at).run()),
            ("controlled_operational_pilot", lambda: OperationalPilotRunner(generated_at=self.generated_at).run()),
            ("performance_telemetry", lambda: run_performance_benchmark(iterations=self.performance_iterations, generated_at=self.generated_at)),
            ("billing_entitlement_validation", lambda: BillingEntitlementValidationRunner(generated_at=self.generated_at).run()),
        )
        evidence = tuple(self._collect_source(source, factory, reports) for source, factory in factories)
        evidence_ids = {item.source: item.evidence_id for item in evidence}
        memory = reports.get("investigation_memory")
        organizational = reports.get("organizational_cyber_memory")
        accuracy = reports.get("operational_accuracy")
        enterprise = reports.get("enterprise_proof")
        pilot = reports.get("controlled_operational_pilot")
        performance = reports.get("performance_telemetry")
        memory_controls = self._mapping(memory, "control_invariants")
        org_controls = self._mapping(organizational, "control_invariants")
        accuracy_controls = self._mapping(accuracy, "safety_validation")
        enterprise_controls = self._mapping(enterprise, "safety_validation")
        pilot_controls = self._mapping(pilot, "safety_validation")
        performance_controls = self._mapping(performance, "control_checks")
        billing = reports.get("billing_entitlement_validation")
        billing_scenarios = {
            item["scenario_id"]: item
            for item in (getattr(billing, "scenarios", ()) if billing is not None else ())
        }
        billing_security = getattr(billing, "security_invariants", {}) if billing is not None else {}
        billing_evidence_id = evidence_ids["billing_entitlement_validation"]
        security_ids = tuple(evidence_ids[item] for item in ("investigation_memory", "organizational_cyber_memory", "enterprise_proof", "controlled_operational_pilot", "billing_entitlement_validation"))
        controls = (
            self._control(
                "SEC-TENANT-ISOLATION", "security", "Tenant isolation", all((
                    bool(memory_controls.get("tenant_isolation_preserved")),
                    bool(org_controls.get("tenant_isolation_preserved")),
                    bool(accuracy_controls.get("tenant_isolation_unchanged")),
                    bool(enterprise_controls.get("tenant_isolation_unchanged")),
                    bool(pilot_controls.get("tenant_isolation_unchanged")),
                    bool(billing_security.get("tenant_isolation_preserved")),
                )), security_ids, "All validation layers preserve tenant-scoped evidence and memory custody."),
            self._control(
                "SEC-AUTHORIZATION", "security", "Authorization boundaries", all((
                    bool(memory_controls.get("authorization_unchanged")),
                    bool(org_controls.get("authorization_unchanged")),
                    bool(accuracy_controls.get("authorization_unchanged")),
                    bool(enterprise_controls.get("authorization_unchanged")),
                    bool(pilot_controls.get("authorization_unchanged")),
                )), security_ids, "Memory and pilot evidence do not alter authorization status."),
            self._control(
                "SEC-FAIL-CLOSED", "security", "Fail-closed behavior", all((
                    bool(memory_controls.get("fail_closed_unchanged")),
                    bool(accuracy_controls.get("fail_closed_behavior_unchanged")),
                    bool(enterprise_controls.get("fail_closed_behavior_unchanged")),
                    bool(pilot_controls.get("fail_closed_behavior_unchanged")),
                    bool(billing_security.get("fail_closed_behavior")),
                )), security_ids, "Blocked and failed paths remain fail-closed."),
            self._control(
                "SEC-AUDIT-INTEGRITY", "security", "Audit integrity", all((
                    bool(getattr(memory, "audit_trail", ())),
                    bool(getattr(enterprise, "report_digest", "")),
                    bool(getattr(pilot, "provenance_chain", ())),
                    bool(performance_controls.get("audit_path_unchanged")),
                    bool(billing_security.get("audit_integrity")),
                )), tuple(evidence_ids.values()), "Source audit trails, hash chains, and telemetry audit paths are present."),
            self._control(
                "SEC-APPEND-ONLY", "security", "Append-only evidence", all((
                    bool(enterprise_controls.get("append_only_evidence")),
                    bool(pilot_controls.get("append_only_audit_evidence")),
                    bool(getattr(memory, "audit_trail", ())),
                    bool(billing_security.get("append_only_evidence")),
                )), tuple(evidence_ids[item] for item in ("investigation_memory", "enterprise_proof", "controlled_operational_pilot")), "Validation artifact writers and audit evidence remain append-only."),
            self._control(
                "AI-VERDICT-CONSISTENCY", "ai_investigation", "Verdict consistency", all((
                    bool(memory_controls.get("verdict_unchanged")),
                    bool(accuracy_controls.get("verdict_enforcement_unchanged")),
                    bool(enterprise_controls.get("verdict_enforcement_unchanged")),
                    bool(pilot_controls.get("verdict_enforcement_unchanged")),
                )), tuple(evidence_ids[item] for item in ("investigation_memory", "operational_accuracy", "enterprise_proof", "controlled_operational_pilot")), "Advisory memory does not change enforced verdicts."),
            self._control(
                "AI-EVIDENCE-PROVENANCE", "ai_investigation", "Evidence provenance", all((
                    bool(memory_controls.get("evidence_provenance_preserved")),
                    bool(org_controls.get("evidence_provenance_preserved")),
                    bool(enterprise_controls.get("evidence_provenance_valid")),
                    bool(pilot_controls.get("evidence_provenance_valid")),
                    bool(billing_security.get("provenance_tracking")),
                )), security_ids, "Evidence remains linked to its tenant and source investigation."),
            self._control(
                "AI-CONFIDENCE-CALIBRATION", "ai_investigation", "Confidence calibration", bool(
                    accuracy and accuracy.aggregate_metrics.get("organizational_memory", {}).get("confidence_calibration", 0.0)
                    >= accuracy.aggregate_metrics.get("baseline", {}).get("confidence_calibration", 1.0)
                ), (evidence_ids["operational_accuracy"],), "Organizational memory does not reduce calibrated confidence quality."),
            self._control(
                "AI-MEMORY-ADVISORY", "ai_investigation", "Memory advisory boundary", all((
                    bool(memory_controls.get("memory_advisory_only")),
                    bool(org_controls.get("memory_advisory_only")),
                    bool(accuracy_controls.get("memory_advisory_only")),
                    bool(enterprise_controls.get("memory_advisory_only")),
                    bool(pilot_controls.get("memory_advisory_only")),
                )), tuple(evidence_ids[item] for item in ("investigation_memory", "organizational_cyber_memory", "operational_accuracy", "enterprise_proof", "controlled_operational_pilot")), "Memory is advisory-only in every evidence source."),
            self._control(
                "PERF-LATENCY", "performance", "Latency measurements", bool(
                    pilot and pilot.metrics.mean_investigation_latency_ms > 0 and performance
                    and performance.component_statistics
                ), (evidence_ids["controlled_operational_pilot"], evidence_ids["performance_telemetry"]), "Pilot and telemetry layers provide latency measurements."),
            self._control(
                "PERF-SCALE", "performance", "Scale benchmarks", bool(
                    enterprise and [item.investigation_count for item in enterprise.scale_benchmark.points] == [10, 100, 1000]
                ), (evidence_ids["enterprise_proof"],), "Enterprise proof includes the required 10/100/1000 scale points."),
            self._control(
                "PERF-MEMORY-OVERHEAD", "performance", "Memory overhead", bool(
                    enterprise and all(item.memory_overhead_kb >= 0 for item in enterprise.scale_benchmark.points)
                ), (evidence_ids["enterprise_proof"],), "Scale evidence records memory overhead without hiding cost."),
            self._control(
                "OPS-REPLAY-STABILITY", "operational", "Replay stability", all(bool(item.source_replay_digest) and item.status == "passed" for item in evidence), tuple(item.evidence_id for item in evidence), "Every source supplies a passing stable replay digest."),
            self._control(
                "OPS-DETERMINISTIC-EXECUTION", "operational", "Deterministic execution", all((
                    bool(getattr(accuracy, "replay_digest", "")),
                    bool(getattr(enterprise, "replay_digest", "")),
                    bool(getattr(pilot, "replay_digest", "")),
                    bool(self._source_replay(performance)),
                )), tuple(evidence_ids.values()), "Stable fixture inputs and replay digests are preserved; observed timing is excluded."),
            self._control(
                "OPS-REPORT-INTEGRITY", "operational", "Report integrity", all(bool(item.source_report_digest) for item in evidence if item.source != "performance_telemetry") and all(bool(item.evidence_digest) for item in evidence), tuple(item.evidence_id for item in evidence), "Source report references and certification evidence digests are present."),
            self._control(
                "BILLING-UNPAID-SAFETY", "billing", "Unpaid tenant safety", self._scenario_checks(billing_scenarios.get("unpaid-tenant-lifecycle"), "tenant_exists_without_active_billing", "identity_remains_valid", "restricted_capabilities_fail_closed", "enterprise_features_not_exposed", "audit_validation"), (billing_evidence_id,), "Unpaid tenants remain identifiable while restricted capabilities fail closed and billing observations are audited."),
            self._control(
                "BILLING-ENTITLEMENT-TRANSITION", "billing", "Entitlement transition correctness", self._scenario_checks(billing_scenarios.get("subscription-activation"), "billing_transition_applied", "new_capabilities_match_entitlement", "only_entitlement_state_changed", "identity_unchanged", "tenant_id_unchanged"), (billing_evidence_id,), "Activation changes entitlement state without changing identity, ownership, or investigation state."),
            self._control(
                "BILLING-UPGRADE-PRESERVATION", "billing", "Upgrade preservation", self._scenario_checks(billing_scenarios.get("subscription-activation"), "investigation_digest_preserved", "evidence_digest_preserved", "provenance_digest_preserved", "provenance_tenant_unchanged"), (billing_evidence_id,), "Subscription activation preserves existing investigation evidence and provenance."),
            self._control(
                "BILLING-DOWNGRADE-SAFETY", "billing", "Downgrade safety", self._scenario_checks(billing_scenarios.get("paid-tenant-downgrade"), "tenant_remains_valid", "historical_investigation_accessible", "restricted_features_removed", "no_privilege_escalation", "evidence_ownership_unchanged", "audit_validation"), (billing_evidence_id,), "Downgrade removes restricted capabilities without changing tenant validity or historical evidence ownership."),
            self._control(
                "BILLING-INVESTIGATION-PRESERVATION", "billing", "Investigation preservation", self._scenario_checks(billing_scenarios.get("pre-billing-investigation-preservation"), "investigation_retrievable", "investigation_digest_preserved", "evidence_digest_preserved", "provenance_digest_preserved", "provenance_tenant_unchanged"), (billing_evidence_id,), "Investigations created before billing activation remain retrievable with unchanged evidence provenance."),
            self._control(
                "BILLING-FAILURE-FAIL-CLOSED", "billing", "Billing failure fail-closed", self._scenario_checks(billing_scenarios.get("billing-failure-handling"), "provider_failure_rejected", "no_partial_entitlement_activation", "no_elevated_privileges", "subscription_state_consistent", "failed_billing_event_not_recorded", "fail_closed_behavior_preserved"), (billing_evidence_id,), "Provider or billing failure does not create partial entitlements or elevated privileges."),
            self._control(
                "BILLING-AUDIT-CONTINUITY", "billing", "Billing audit continuity", bool(billing_security.get("audit_integrity")) and bool(billing_security.get("append_only_evidence")) and all(self._scenario_checks(item, "audit_validation") for item in billing_scenarios.values()), (billing_evidence_id,), "Billing lifecycle observations preserve tenant-bound append-only audit continuity."),
        )
        metrics: list[CertificationMetric] = []
        if accuracy:
            metrics.extend((
                self._metric("METRIC-ACCURACY-VERDICT", "ai_investigation", "Organizational verdict agreement", accuracy.aggregate_metrics["organizational_memory"]["verdict_agreement"], "ratio", (evidence_ids["operational_accuracy"],), "Higher is better."),
                self._metric("METRIC-ACCURACY-CONFIDENCE", "ai_investigation", "Confidence calibration", accuracy.aggregate_metrics["organizational_memory"]["confidence_calibration"], "score", (evidence_ids["operational_accuracy"],), "Higher is better."),
                self._metric("METRIC-MEMORY-BENEFIT", "ai_investigation", "Memory benefit score", accuracy.memory_benefit_score, "score", (evidence_ids["operational_accuracy"],), "Positive score indicates advisory memory benefit."),
            ))
        if pilot:
            metrics.extend((
                self._metric("METRIC-PILOT-MEAN-LATENCY", "performance", "Pilot mean investigation latency", pilot.metrics.mean_investigation_latency_ms, "ms", (evidence_ids["controlled_operational_pilot"],), "Synthetic deterministic timing."),
                self._metric("METRIC-PILOT-P50-LATENCY", "performance", "Pilot p50 investigation latency", pilot.metrics.p50_investigation_latency_ms, "ms", (evidence_ids["controlled_operational_pilot"],), "Synthetic deterministic timing."),
                self._metric("METRIC-PILOT-P95-LATENCY", "performance", "Pilot p95 investigation latency", pilot.metrics.p95_investigation_latency_ms, "ms", (evidence_ids["controlled_operational_pilot"],), "Synthetic deterministic timing."),
            ))
        if enterprise:
            largest = enterprise.scale_benchmark.points[-1]
            metrics.extend((
                self._metric("METRIC-SCALE-P95-1000", "performance", "1000-investigation enhanced p95 latency", largest.enhanced_p95_latency_ms, "ms", (evidence_ids["enterprise_proof"],), "Synthetic scale estimate."),
                self._metric("METRIC-SCALE-MEMORY-1000", "performance", "1000-investigation memory overhead", largest.memory_overhead_rate, "ratio", (evidence_ids["enterprise_proof"],), "Synthetic scale estimate."),
            ))
        if performance:
            coordinator = performance.component_statistics.get("coordinator", {})
            metrics.append(self._metric("METRIC-TELEMETRY-COORDINATOR-P50", "performance", "Telemetry coordinator p50", coordinator.get("p50_ms", 0.0), "ms", (evidence_ids["performance_telemetry"],), "Host-observed telemetry; not part of replay identity."))
        if billing:
            metrics.extend((
                self._metric("METRIC-BILLING-SCENARIOS", "billing", "Billing lifecycle scenarios passed", billing.metrics.get("passed_scenario_count", 0), "count", (billing_evidence_id,), "Synthetic offline billing lifecycle evidence."),
                self._metric("METRIC-BILLING-AUDIT-COVERAGE", "billing", "Billing scenarios with audit validation", billing.metrics.get("audit_validated_scenario_count", 0), "count", (billing_evidence_id,), "Each scenario must retain append-only tenant-bound audit evidence."),
            ))
        passed_controls = tuple(item.control_id for item in controls if item.passed)
        failed_controls = tuple(item.control_id for item in controls if not item.passed)
        warnings = (
            "synthetic_validation_only_no_production_deployment_or_external_integrations",
            "performance_telemetry_timings_are_host_observed_and_excluded_from_replay_identity",
        )
        findings: list[CertificationFinding] = []
        for control in controls:
            if not control.passed:
                findings.append(CertificationFinding(
                    finding_id=f"FINDING-{control.control_id}",
                    severity="high" if control.required else "medium",
                    status="failed",
                    title=f"Certification control failed: {control.name}",
                    description=control.rationale,
                    evidence_ids=control.evidence_ids,
                    remediation="Investigate the source validation evidence before enterprise certification.",
                ))
        if not findings:
            findings.append(CertificationFinding(
                finding_id="FINDING-ALL-REQUIRED-CONTROLS",
                severity="info",
                status="passed",
                title="All required enterprise controls passed",
                description="Unified validation evidence supports the current synthetic enterprise readiness scope.",
                evidence_ids=tuple(item.evidence_id for item in evidence),
            ))
        for index, warning in enumerate(warnings, start=1):
            findings.append(CertificationFinding(
                finding_id=f"FINDING-WARNING-{index:02d}",
                severity="low",
                status="warning",
                title="Certification scope warning",
                description=warning,
                evidence_ids=tuple(item.evidence_id for item in evidence),
            ))
        stable_payload = {
            "version": self.REPORT_VERSION,
            "evidence": [
                {
                    "evidence_id": item.evidence_id,
                    "source": item.source,
                    "status": item.status,
                    "source_replay_digest": item.source_replay_digest,
                    "evidence_digest": item.evidence_digest,
                }
                for item in evidence
            ],
            "controls": [item.to_dict() for item in controls],
            "evidence_references": [item.evidence_id for item in evidence],
        }
        validation_digest = hashlib.sha256(self._canonical(stable_payload).encode("utf-8")).hexdigest()
        replay_digest = hashlib.sha256(self._canonical({**stable_payload, "validation_digest": validation_digest}).encode("utf-8")).hexdigest()
        environment = {
            "execution_mode": "synthetic_offline_evidence_packaging",
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "source_count": len(evidence),
            "external_integrations": False,
            "production_deployment": False,
        }
        report_payload = {
            "report_version": self.REPORT_VERSION,
            "timestamp": self.generated_at,
            "environment_metadata": environment,
            "commit_sha": self.commit_sha,
            "validation_digest": validation_digest,
            "evidence": [item.to_dict() for item in evidence],
            "controls": [item.to_dict() for item in controls],
            "metrics": [item.to_dict() for item in metrics],
            "findings": [item.to_dict() for item in findings],
            "passed_controls": list(passed_controls),
            "failed_controls": list(failed_controls),
            "warnings": list(warnings),
            "evidence_references": [item.evidence_id for item in evidence],
            "replay_digest": replay_digest,
            "immutable": True,
        }
        report_digest = hashlib.sha256(self._canonical(report_payload).encode("utf-8")).hexdigest()
        return CertificationReport(
            report_version=self.REPORT_VERSION,
            timestamp=self.generated_at,
            environment_metadata=environment,
            commit_sha=self.commit_sha,
            validation_digest=validation_digest,
            evidence=evidence,
            controls=controls,
            metrics=tuple(metrics),
            findings=tuple(findings),
            passed_controls=passed_controls,
            failed_controls=failed_controls,
            warnings=warnings,
            evidence_references=tuple(item.evidence_id for item in evidence),
            replay_digest=replay_digest,
            report_digest=report_digest,
        )

    @staticmethod
    def verify_replay(first: CertificationReport, second: CertificationReport) -> bool:
        return first.replay_digest == second.replay_digest


__all__ = ["EnterpriseCertificationRunner"]
