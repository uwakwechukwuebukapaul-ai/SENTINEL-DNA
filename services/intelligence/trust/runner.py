"""Enterprise trust closure assessment."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import tempfile
from typing import Any

from config.runtime import RuntimeConfig
from services.intelligence.certification import CertificationReportGenerator, EnterpriseCertificationRunner

from .models import TrustClosureFinding, TrustClosureReport


class EnterpriseTrustClosureRunner:
    """Convert certification evidence into a production trust assessment."""

    REPORT_VERSION = "sentinel-dna-enterprise-trust-closure.v1"

    def __init__(
        self,
        *,
        generated_at: str | None = None,
        commit_sha: str | None = None,
        repository_root: str | Path | None = None,
        previous_certification_path: str | Path = "artifacts/enterprise-certification-refresh-2026-08-25.json",
    ) -> None:
        self.generated_at = str(generated_at or datetime.now(timezone.utc).isoformat())
        self.repository_root = Path(repository_root or Path(__file__).resolve().parents[3]).resolve()
        self.commit_sha = str(commit_sha or self._git_sha())
        self.previous_certification_path = self.repository_root / previous_certification_path

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

    def _git_dirty(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=all"],
                cwd=self.repository_root,
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return bool(result.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            return True

    def _previous_certification(self) -> dict[str, Any]:
        if not self.previous_certification_path.is_file():
            return {
                "available": False,
                "path": str(self.previous_certification_path),
                "report_digest": "",
                "replay_digest": "",
                "validation_digest": "",
            }
        try:
            payload = json.loads(self.previous_certification_path.read_text(encoding="utf-8"))
            return {
                "available": True,
                "path": str(self.previous_certification_path.relative_to(self.repository_root)),
                "report_digest": str(payload.get("report_digest", "")),
                "replay_digest": str(payload.get("replay_digest", "")),
                "validation_digest": str(payload.get("validation_digest", "")),
                "failed_controls": list(payload.get("failed_controls", [])),
            }
        except (OSError, ValueError, json.JSONDecodeError):
            return {
                "available": False,
                "path": str(self.previous_certification_path),
                "report_digest": "",
                "replay_digest": "",
                "validation_digest": "",
            }

    def _otp_hardening(self) -> dict[str, bool]:
        from services.auth.auth_service import AuthService

        issue_secret = inspect.signature(AuthService.issue_otp).parameters["secret"]
        verify_secret = inspect.signature(AuthService.verify_otp).parameters["secret"]
        routes_path = self.repository_root / "services/auth/routes.py"
        route_text = routes_path.read_text(encoding="utf-8")
        calls = re.findall(r"\.(?:issue_otp|verify_otp)\(", route_text)
        configured_calls = re.findall(
            r"\.(?:issue_otp|verify_otp)\([^\n]*secret=current_app\.secret_key",
            route_text,
        )
        return {
            "otp_issue_secret_required": issue_secret.default is inspect.Parameter.empty,
            "otp_verify_secret_required": verify_secret.default is inspect.Parameter.empty,
            "production_otp_routes_use_configured_secret": bool(calls) and len(calls) == len(configured_calls),
        }

    @staticmethod
    def _production_config_fail_closed() -> bool:
        config = RuntimeConfig(
            environment="production",
            database_path="",
            secret_key="short",
            secure_cookies=False,
            debug=False,
        )
        try:
            config.validate()
        except RuntimeError:
            return True
        return False

    @staticmethod
    def _immutable_writer_check(report: Any) -> bool:
        try:
            with tempfile.TemporaryDirectory(prefix="sentinel-trust-") as directory:
                path = Path(directory) / "certification.json"
                CertificationReportGenerator.write(report, path)
                try:
                    CertificationReportGenerator.write(report, path)
                except FileExistsError:
                    return True
        except (OSError, ValueError):
            return False
        return False

    @staticmethod
    def _finding(
        finding_id: str,
        category: str,
        severity: str,
        status: str,
        title: str,
        description: str,
        references: tuple[str, ...],
        remediation: str | None = None,
    ) -> TrustClosureFinding:
        return TrustClosureFinding(finding_id, category, severity, status, title, description, references, remediation)

    def run(self) -> TrustClosureReport:
        certification = EnterpriseCertificationRunner(
            generated_at=self.generated_at,
            commit_sha=self.commit_sha,
        ).run()
        certification_controls = {
            item.control_id: item.passed
            for item in certification.controls
        }
        previous = self._previous_certification()
        otp = self._otp_hardening()
        security = {
            **otp,
            "production_config_fail_closed": self._production_config_fail_closed(),
            "tenant_isolation": certification_controls.get("SEC-TENANT-ISOLATION", False),
            "authorization_boundaries": certification_controls.get("SEC-AUTHORIZATION", False),
            "fail_closed_behavior": certification_controls.get("SEC-FAIL-CLOSED", False),
            "audit_integrity": certification_controls.get("SEC-AUDIT-INTEGRITY", False),
            "append_only_evidence": certification_controls.get("SEC-APPEND-ONLY", False),
            "provenance_tracking": certification_controls.get("AI-EVIDENCE-PROVENANCE", False),
            "memory_advisory_boundary": certification_controls.get("AI-MEMORY-ADVISORY", False),
        }
        artifact_paths = (
            self.repository_root / "artifacts/enterprise-proof-refresh-2026-08-25.json",
            self.repository_root / "artifacts/operational-pilot-refresh-2026-08-25.json",
            self.repository_root / "artifacts/enterprise-certification-refresh-2026-08-25.json",
        )
        release_hygiene = {
            "clean_git_state_required": not self._git_dirty(),
            "artifact_provenance": all(path.is_file() and path.stat().st_size > 0 for path in artifact_paths),
            "immutable_evidence_storage": self._immutable_writer_check(certification),
            "replay_digest_preservation": bool(
                previous.get("available") and previous.get("replay_digest") == certification.replay_digest
            ),
            "release_manifest_correctness": not self._git_dirty(),
        }
        migrations = (
            (self.repository_root / "database/migrations/007_investigation_memory.py").is_file()
            and (self.repository_root / "database/migrations/008_organizational_cyber_memory.py").is_file()
        )
        deployment = {
            "production_configuration_requirements_validated": security["production_config_fail_closed"],
            "database_migrations_present": migrations,
            "postgresql_migration_rehearsal_completed": False,
            "backup_restore_verified": False,
            "monitoring_requirements_verified": False,
            "operational_ownership_verified": False,
            "deployment_executed": False,
            "external_integrations_enabled": False,
        }
        evidence_refs = (
            str(self.previous_certification_path.relative_to(self.repository_root))
            if self.previous_certification_path.is_relative_to(self.repository_root)
            else str(self.previous_certification_path),
            "enterprise-certification.replay_digest",
            "enterprise-certification.validation_digest",
            "auth_service.otp_secret_required",
            "config.runtime.production_validation",
        )
        findings: list[TrustClosureFinding] = []
        if all(security.values()):
            findings.append(self._finding(
                "TRUST-SECURITY-CONTROLS",
                "security",
                "info",
                "passed",
                "Credential and security boundaries hardened",
                "OTP secret fallbacks are removed, production routes use configured application secrets, and certification security controls pass.",
                evidence_refs,
            ))
        else:
            findings.append(self._finding(
                "TRUST-SECURITY-CONTROLS",
                "security",
                "high",
                "failed",
                "Security hardening controls incomplete",
                "One or more credential, authorization, tenant, provenance, or fail-closed controls did not pass.",
                evidence_refs,
                "Resolve all failed security controls before release.",
            ))
        if not release_hygiene["clean_git_state_required"]:
            findings.append(self._finding(
                "TRUST-BLOCKER-CLEAN-WORKTREE",
                "release_hygiene",
                "high",
                "blocked",
                "Release manifest requires a clean worktree",
                "The release manifest gate refuses to build from a dirty repository.",
                ("git.status.porcelain",),
                "Commit or isolate all intended changes and rerun release-manifest validation.",
            ))
        if not release_hygiene["replay_digest_preservation"]:
            findings.append(self._finding(
                "TRUST-BLOCKER-REPLAY-DRIFT",
                "release_hygiene",
                "high",
                "blocked",
                "Certification replay drift detected",
                "The refreshed certification replay digest differs from the previous artifact.",
                ("enterprise-certification.replay_digest",),
                "Investigate deterministic fixture or contract drift.",
            ))
        if not deployment["postgresql_migration_rehearsal_completed"]:
            findings.append(self._finding(
                "TRUST-BLOCKER-POSTGRES-REHEARSAL",
                "deployment_readiness",
                "high",
                "blocked",
                "PostgreSQL migration rehearsal is not evidenced",
                "SQLite/synthetic validation does not prove PostgreSQL migration behavior.",
                ("database/migrations/007_investigation_memory.py", "database/migrations/008_organizational_cyber_memory.py"),
                "Run a controlled PostgreSQL migration and rollback rehearsal outside this evidence-only task.",
            ))
        if not deployment["backup_restore_verified"]:
            findings.append(self._finding(
                "TRUST-BLOCKER-BACKUP-RESTORE",
                "deployment_readiness",
                "high",
                "blocked",
                "Backup and restore evidence is missing",
                "No production-like backup/restore rehearsal was executed.",
                ("deployment.backup_restore",),
                "Complete and sign a backup/restore drill before deployment approval.",
            ))
        if not deployment["monitoring_requirements_verified"] or not deployment["operational_ownership_verified"]:
            findings.append(self._finding(
                "TRUST-WARN-OPERATIONS",
                "deployment_readiness",
                "medium",
                "warning",
                "Monitoring and operational ownership are not evidenced",
                "The repository does not provide signed production monitoring and ownership acceptance evidence.",
                ("deployment.monitoring", "deployment.ownership"),
                "Obtain operations sign-off, alert routing, on-call ownership, and runbook acceptance.",
            ))
        findings.append(self._finding(
            "TRUST-WARN-CREDENTIAL-ATTESTATION",
            "credential_security",
            "medium",
            "warning",
            "Provider-side credential revocation is not locally attestable",
            "Local configuration references were reviewed without exposing values; secret-store/provider revocation evidence is external to this workspace.",
            ("configuration.secret_references",),
            "Attach secret-manager rotation and revocation attestation before production sign-off.",
        ))
        remaining_risks = tuple(item.title for item in findings if item.status in {"blocked", "warning"})
        blockers = tuple(item.finding_id for item in findings if item.status == "blocked")
        release_gates = (
            "clean worktree and successful release-manifest verification",
            "secret-store rotation/revocation attestation",
            "PostgreSQL migration and rollback rehearsal",
            "backup/restore drill with signed evidence",
            "monitoring, alert routing, and operational ownership sign-off",
        )
        stable_payload = {
            "version": self.REPORT_VERSION,
            "commit_sha": self.commit_sha,
            "previous_certification_replay": previous.get("replay_digest", ""),
            "current_certification_replay": certification.replay_digest,
            "security_hardening": security,
            "release_evidence_hygiene": release_hygiene,
            "deployment_readiness": deployment,
            "findings": [item.to_dict() for item in findings],
            "production_blockers": blockers,
        }
        replay_digest = hashlib.sha256(json.dumps(stable_payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
        report_payload = {
            **stable_payload,
            "report_version": self.REPORT_VERSION,
            "timestamp": self.generated_at,
            "previous_certification": previous,
            "remaining_risks": remaining_risks,
            "recommended_release_gates": release_gates,
            "evidence_references": evidence_refs,
            "replay_digest": replay_digest,
            "production_ready": not blockers and all(deployment.values()),
            "immutable": True,
            "environment": {"python": platform.python_version(), "platform": platform.platform()},
        }
        report_digest = hashlib.sha256(json.dumps(report_payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
        return TrustClosureReport(
            report_version=self.REPORT_VERSION,
            timestamp=self.generated_at,
            commit_sha=self.commit_sha,
            previous_certification=previous,
            security_hardening=security,
            release_evidence_hygiene=release_hygiene,
            deployment_readiness=deployment,
            findings=tuple(findings),
            remaining_risks=remaining_risks,
            production_blockers=blockers,
            recommended_release_gates=release_gates,
            evidence_references=evidence_refs,
            replay_digest=replay_digest,
            report_digest=report_digest,
            production_ready=not blockers and all(deployment.values()),
        )

    @staticmethod
    def verify_replay(first: TrustClosureReport, second: TrustClosureReport) -> bool:
        return first.replay_digest == second.replay_digest


__all__ = ["EnterpriseTrustClosureRunner"]
