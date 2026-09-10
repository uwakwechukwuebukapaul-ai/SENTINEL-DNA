"""Evidence-only aggregation of Sentinel DNA enterprise validation reports."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
from typing import Any, Callable, Mapping

from deployment.validation.contract import DeploymentContractValidator
from deployment.validation.database_rehearsal import DatabaseMigrationRehearsalValidator
from deployment.validation.ownership import OperationalOwnershipEvidenceValidator
from deployment.validation.postgres_rehearsal import PostgresRehearsalValidator
from deployment.validation.recovery import BackupRecoveryEvidenceValidator
from deployment.validation.release_hygiene import ReleaseHygieneValidator
from deployment.validation.runtime_readiness import RuntimeReadinessValidator
from services.billing.validation import BillingEntitlementValidationRunner
from services.intelligence.enterprise_proof import EnterpriseProofValidator
from services.intelligence.evaluation.benchmark_runner import OperationalAccuracyBenchmarkRunner
from services.intelligence.memory.organizational_validation import OrganizationalMemoryValidator
from services.intelligence.memory.validation import OperationalCyberMemoryValidator
from services.intelligence.pilot import OperationalPilotRunner
from services.intelligence.trust import EnterpriseTrustClosureRunner

from .models import EvidenceClosureReport


REPORT_VERSION = "sentinel-dna-enterprise-evidence-closure.v1"
REPLAY_VERSION = "sentinel-dna-enterprise-evidence-closure-replay.v1"
SOURCE_NAMES = (
    "enterprise_readiness_certification",
    "enterprise_proof_validation",
    "trust_closure",
    "investigation_memory_validation",
    "organizational_cyber_memory_validation",
    "operational_accuracy_validation",
    "controlled_operational_pilot",
    "deployment_contract_validation",
    "recovery_readiness_validation",
    "billing_entitlement_validation",
    "runtime_readiness",
    "database_rehearsal",
    "postgres_rehearsal",
    "backup_restore",
    "operational_ownership",
    "release_hygiene",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Any) -> str:
    return hashlib.sha256((_canonical(value) + "\n").encode("utf-8")).hexdigest()


class EnterpriseEvidenceClosureRunner:
    """Collect required validation evidence without adding decision authority."""

    REPORT_VERSION = REPORT_VERSION
    SOURCE_NAMES = SOURCE_NAMES

    def __init__(
        self,
        *,
        repository_root: str | Path | None = None,
        generated_at: str | None = None,
        commit_sha: str | None = None,
        source_factories: Mapping[str, Callable[[], Any]] | None = None,
    ) -> None:
        self.repository_root = Path(repository_root or Path(__file__).resolve().parents[4]).resolve()
        self.generated_at = str(generated_at or datetime.now(timezone.utc).isoformat())
        self.commit_sha = str(commit_sha or self._git_sha())
        self.source_factories = dict(source_factories or {})

    def _git_sha(self) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repository_root,
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() or "unknown"
        except (OSError, subprocess.SubprocessError):
            return "unknown"

    def _factories(self) -> dict[str, Callable[[], Any]]:
        deployment = lambda: DeploymentContractValidator(
            repository_root=self.repository_root,
            generated_at=self.generated_at,
        ).run()
        return {
            "enterprise_readiness_certification": lambda: __import__(
                "services.intelligence.certification", fromlist=["EnterpriseCertificationRunner"]
            ).EnterpriseCertificationRunner(
                generated_at=self.generated_at,
                commit_sha=self.commit_sha,
            ).run(),
            "enterprise_proof_validation": lambda: EnterpriseProofValidator(generated_at=self.generated_at).run(),
            "trust_closure": lambda: EnterpriseTrustClosureRunner(
                repository_root=self.repository_root,
                generated_at=self.generated_at,
                commit_sha=self.commit_sha,
            ).run(),
            "investigation_memory_validation": lambda: OperationalCyberMemoryValidator(generated_at=self.generated_at).run(),
            "organizational_cyber_memory_validation": lambda: OrganizationalMemoryValidator(generated_at=self.generated_at).run(),
            "operational_accuracy_validation": lambda: OperationalAccuracyBenchmarkRunner(generated_at=self.generated_at).run(),
            "controlled_operational_pilot": lambda: OperationalPilotRunner(generated_at=self.generated_at).run(),
            "deployment_contract_validation": deployment,
            "recovery_readiness_validation": lambda: self._recovery_report(deployment()),
            "billing_entitlement_validation": lambda: BillingEntitlementValidationRunner(generated_at=self.generated_at).run(),
            "runtime_readiness": lambda: RuntimeReadinessValidator(
                repository_root=self.repository_root,
                generated_at=self.generated_at,
            ).run(),
            "database_rehearsal": lambda: DatabaseMigrationRehearsalValidator(
                repository_root=self.repository_root,
                generated_at=self.generated_at,
            ).run(),
            "postgres_rehearsal": lambda: PostgresRehearsalValidator(
                repository_root=self.repository_root,
                generated_at=self.generated_at,
            ).run(),
            "backup_restore": lambda: BackupRecoveryEvidenceValidator(
                generated_at=self.generated_at,
            ).run(),
            "operational_ownership": lambda: OperationalOwnershipEvidenceValidator(
                repository_root=self.repository_root,
                generated_at=self.generated_at,
            ).run(),
            "release_hygiene": lambda: ReleaseHygieneValidator(
                repository_root=self.repository_root,
                generated_at=self.generated_at,
            ).run(),
        }

    @staticmethod
    def _recovery_report(deployment_report: Any) -> dict[str, Any]:
        contracts = getattr(deployment_report, "contracts", ())
        if isinstance(deployment_report, dict):
            contracts = deployment_report.get("contracts", ())
        selected = [
            item for item in contracts
            if item.get("contract") in {"database_migration_rehearsal", "backup_restore_readiness"}
        ]
        checks = {
            item["contract"]: item.get("status") == "passed"
            for item in selected
        }
        body = {
            "report_version": "sentinel-dna-recovery-readiness-validation.v1",
            "contracts": selected,
            "checks": checks,
            "validation_result": "passed" if selected and all(checks.values()) else "failed",
            "evidence_policy": {
                "derived_from": "deployment_contract_validation",
                "production_operations_performed": False,
                "external_integrations_used": False,
            },
        }
        return {
            **body,
            "replay_digest": _digest({"replay_version": "sentinel-dna-recovery-readiness-replay.v1", **body}),
            "report_digest": _digest(body),
        }

    @staticmethod
    def _to_dict(report: Any) -> dict[str, Any]:
        if report is None:
            return {}
        if isinstance(report, dict):
            return dict(report)
        method = getattr(report, "to_dict", None)
        if callable(method):
            return dict(method())
        return {}

    @staticmethod
    def _replay(report: Any, payload: dict[str, Any]) -> str:
        value = getattr(report, "replay_digest", None)
        if value:
            return str(value)
        deterministic = payload.get("deterministic_replay", {})
        if isinstance(deterministic, dict):
            value = (
                deterministic.get("replay_digest")
                or deterministic.get("input_output_digest")
                or deterministic.get("input_digest")
            )
            if value:
                return str(value)
        return str(payload.get("replay_digest", ""))

    @staticmethod
    def _report_digest(report: Any, payload: dict[str, Any]) -> str:
        value = getattr(report, "report_digest", None)
        return str(value or payload.get("report_digest", ""))

    @staticmethod
    def _status(report: Any, payload: dict[str, Any]) -> str:
        if report is None and not payload:
            return "missing"
        if payload.get("validation_result") in {"passed", "failed", "blocked", "pending"}:
            return str(payload["validation_result"])
        if payload.get("closure_result") in {"passed", "failed", "blocked"}:
            return str(payload["closure_result"])
        if payload.get("production_ready") is False:
            return "blocked"
        for key in ("safety_validation", "control_invariants", "control_checks", "security_hardening"):
            mapping = payload.get(key)
            if isinstance(mapping, dict):
                return "passed" if all(bool(value) for value in mapping.values()) else "failed"
        mapping = payload.get("checks")
        if isinstance(mapping, dict):
            return "passed" if all(bool(value) for value in mapping.values()) else "failed"
        return "passed" if payload else "missing"

    @staticmethod
    def _controls(source: str, report: Any, payload: dict[str, Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []

        pending_checks = set(payload.get("pending_checks", ()))

        def add(control_id: str, passed: bool, name: str, domain: str = "enterprise", *, pending: bool = False) -> None:
            state = "passed" if passed else ("pending" if pending else "failed")
            result.append({
                "control_id": control_id,
                "source": source,
                "domain": domain,
                "name": name,
                "required": True,
                "passed": bool(passed),
                "state": state,
                "evidence_reference": f"{source}.replay_digest",
            })

        if source == "enterprise_readiness_certification":
            for item in payload.get("controls", ()):
                add(str(item.get("control_id")), bool(item.get("passed")), str(item.get("name", item.get("control_id"))), str(item.get("domain", "enterprise")))
        elif source in {"deployment_contract_validation", "recovery_readiness_validation"}:
            for contract in payload.get("contracts", ()):
                for name, passed in contract.get("checks", {}).items():
                    add(f"{source.upper()}:{contract.get('contract')}:{name}", bool(passed), name, "deployment_readiness")
            mapping = payload.get("safety_invariants", payload.get("checks", {}))
            for name, passed in mapping.items():
                add(f"{source.upper()}:{name}", bool(passed), name, "security")
        elif source in {"runtime_readiness", "database_rehearsal", "postgres_rehearsal", "backup_restore", "operational_ownership", "release_hygiene"}:
            for name, passed in sorted(payload.get("checks", {}).items()):
                add(
                    f"{source.upper()}:{name}",
                    bool(passed),
                    name,
                    "operational_readiness",
                    pending=name in pending_checks,
                )
        elif source == "billing_entitlement_validation":
            for scenario in payload.get("scenarios", ()):
                add(f"BILLING:{scenario.get('scenario_id')}", scenario.get("status") == "passed", str(scenario.get("title", scenario.get("scenario_id"))), "billing")
            for name, passed in payload.get("security_invariants", {}).items():
                add(f"BILLING-SECURITY:{name}", bool(passed), name, "security")
        else:
            mappings = ("safety_validation", "control_invariants", "control_checks", "security_hardening")
            for key in mappings:
                mapping = payload.get(key)
                if isinstance(mapping, dict):
                    for name, passed in sorted(mapping.items()):
                        add(f"{source.upper()}:{name}", bool(passed), name, "security" if "security" in key or "hardening" in key else "validation")
                    break
        return result

    @classmethod
    def _blockers(cls, source: str, status: str, controls: list[dict[str, Any]], payload: dict[str, Any]) -> list[str]:
        blockers: list[str] = []
        if status == "missing":
            blockers.append(f"EVIDENCE-SOURCE-MISSING:{source}")
        elif status in {"failed", "blocked", "pending"}:
            blockers.append(f"EVIDENCE-SOURCE-{status.upper()}:{source}")
        blockers.extend(
            f"CONTROL-{item.get('state', 'failed').upper()}:{item['control_id']}"
            for item in controls
            if item.get("state") != "passed"
        )
        if source == "trust_closure":
            blockers.extend(str(item) for item in payload.get("production_blockers", ()))
        return blockers

    def run(self) -> EvidenceClosureReport:
        factories = self._factories()
        factories.update(self.source_factories)
        reports: dict[str, Any] = {}
        sources: list[dict[str, Any]] = []
        controls: list[dict[str, Any]] = []
        blockers: list[str] = []
        warnings = {
            "closure_is_evidence_only_and_does_not_authorize_deployment",
            "source_reports_may_include_host_observed_timing_excluded_from_replay_identity",
        }
        replay_refs: list[dict[str, str]] = []
        for source in self.SOURCE_NAMES:
            report: Any = None
            error: str | None = None
            try:
                factory = factories.get(source)
                if factory is None:
                    raise LookupError("required_source_factory_missing")
                report = factory()
            except Exception as exc:  # fail closed while preserving bounded diagnostics
                error = type(exc).__name__
            payload = self._to_dict(report)
            status = self._status(report, payload) if error is None else "missing"
            replay = self._replay(report, payload)
            report_digest = self._report_digest(report, payload)
            if error is None and not replay:
                status = "missing"
            if error is None and not report_digest:
                status = "missing"
            source_controls = self._controls(source, report, payload)
            source_blockers = self._blockers(source, status, source_controls, payload)
            if error:
                source_blockers.append(f"EVIDENCE-SOURCE-ERROR:{source}:{error}")
            if error is None and not replay:
                source_blockers.append(f"EVIDENCE-REPLAY-MISSING:{source}")
            if error is None and not report_digest:
                source_blockers.append(f"EVIDENCE-REPORT-DIGEST-MISSING:{source}")
            blockers.extend(source_blockers)
            if payload.get("warnings"):
                warnings.update(str(item) for item in payload["warnings"])
            controls.extend(source_controls)
            replay_refs.append({"source": source, "reference": f"{source}.replay_digest", "digest": replay})
            sources.append({
                "source": source,
                "required": True,
                "status": status,
                "report_version": str(payload.get("report_version", getattr(report, "report_version", "unknown"))),
                "report_digest": report_digest,
                "replay_digest": replay,
                "evidence_references": [f"{source}.report_digest", f"{source}.replay_digest"],
                "provenance": {
                    "source_kind": "synthetic_offline_validation",
                    "tenant_scope": "defined_by_source_validator",
                    "secrets_serialized": False,
                    "external_integrations_used": False,
                },
                "summary": {
                    "control_count": len(source_controls),
                    "failed_control_count": sum(item["state"] == "failed" for item in source_controls),
                    "pending_control_count": sum(item["state"] == "pending" for item in source_controls),
                    "error": error,
                },
            })
        controls.sort(key=lambda item: (item["source"], item["control_id"]))
        sources.sort(key=lambda item: item["source"])
        passed = tuple(item["control_id"] for item in controls if item.get("state") == "passed")
        pending = tuple(item["control_id"] for item in controls if item.get("state") == "pending")
        failed = tuple(item["control_id"] for item in controls if item.get("state") == "failed")
        blockers = tuple(sorted(set(blockers)))
        closure_result = "passed" if not blockers and len(sources) == len(self.SOURCE_NAMES) else "blocked"
        stable_payload = {
            "replay_version": REPLAY_VERSION,
            "source_names": list(self.SOURCE_NAMES),
            "sources": [
                {"source": item["source"], "status": item["status"], "replay_digest": item["replay_digest"]}
                for item in sources
            ],
            "controls": controls,
            "passed_controls": list(passed),
            "pending_controls": list(pending),
            "failed_controls": list(failed),
            "blockers": list(blockers),
        }
        replay_digest = _digest(stable_payload)
        timestamp_metadata = {
            "generated_at": self.generated_at,
            "timezone": "UTC",
            "replay_excludes": ["generated_at", "commit_sha", "report_digest", "host_paths", "timing"],
        }
        provenance_metadata = {
            "commit_sha": self.commit_sha,
            "execution_mode": "synthetic_offline_evidence_closure",
            "source_count": len(sources),
            "required_source_count": len(self.SOURCE_NAMES),
            "external_integrations": False,
            "deployment_performed": False,
            "protected_runtime_contracts_changed": False,
        }
        report_without_digest = {
            "report_version": REPORT_VERSION,
            "generated_at": self.generated_at,
            "commit_sha": self.commit_sha,
            "closure_result": closure_result,
            "evidence_sources": sources,
            "control_matrix": controls,
            "total_controls": len(controls),
            "passed_controls": list(passed),
            "pending_controls": list(pending),
            "failed_controls": list(failed),
            "warnings": sorted(warnings),
            "remaining_blockers": list(blockers),
            "replay_digest_references": replay_refs,
            "timestamp_metadata": timestamp_metadata,
            "provenance_metadata": provenance_metadata,
            "replay_digest": replay_digest,
            "immutable": True,
        }
        artifact_digest = _digest(report_without_digest)
        return EvidenceClosureReport(
            report_version=REPORT_VERSION,
            generated_at=self.generated_at,
            commit_sha=self.commit_sha,
            closure_result=closure_result,
            evidence_sources=tuple(sources),
            control_matrix=tuple(controls),
            total_controls=len(controls),
            passed_controls=passed,
            pending_controls=pending,
            failed_controls=failed,
            warnings=tuple(sorted(warnings)),
            remaining_blockers=blockers,
            replay_digest_references=tuple(replay_refs),
            timestamp_metadata=timestamp_metadata,
            provenance_metadata=provenance_metadata,
            replay_digest=replay_digest,
            artifact_digest=artifact_digest,
        )

    @staticmethod
    def verify_replay(first: EvidenceClosureReport, second: EvidenceClosureReport) -> bool:
        return first.replay_digest == second.replay_digest


__all__ = ["EnterpriseEvidenceClosureRunner", "SOURCE_NAMES"]
