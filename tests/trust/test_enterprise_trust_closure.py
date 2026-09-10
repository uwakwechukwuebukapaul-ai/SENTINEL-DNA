import shutil
import subprocess
from pathlib import Path

import pytest

from services.intelligence.certification import CertificationReportGenerator, EnterpriseCertificationRunner
from services.intelligence.trust import EnterpriseTrustClosureRunner, TrustClosureReportGenerator


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _isolated_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    subprocess.run(
        ["git", "clone", "--no-local", str(REPOSITORY_ROOT), str(repository)],
        check=True,
        capture_output=True,
        text=True,
    )

    shutil.copyfile(
        repository / "artifacts" / "enterprise-proof-refresh-2026-08-25.json",
        repository / "artifacts" / "enterprise-proof-billing-refresh-2026-08-25.json",
    )
    CertificationReportGenerator.write(
        EnterpriseCertificationRunner(
            generated_at="2026-08-25T00:00:00+00:00",
            commit_sha="synthetic-commit-sha",
        ).run(),
        repository / "artifacts" / "enterprise-certification-billing-refresh-2026-08-25.json",
    )

    tracked_probe = repository / "README.md"
    tracked_probe.write_bytes(tracked_probe.read_bytes() + b"\ntrust closure dirty-state fixture\n")
    return repository


def _report():
    return EnterpriseTrustClosureRunner(
        generated_at="2026-08-25T00:00:00+00:00",
        commit_sha="synthetic-commit-sha",
    ).run()


def test_credential_security_closure_removes_unsafe_otp_defaults():
    report = _report()

    assert report.security_hardening["otp_issue_secret_required"] is True
    assert report.security_hardening["otp_verify_secret_required"] is True
    assert report.security_hardening["production_otp_routes_use_configured_secret"] is True
    assert report.security_hardening["production_config_fail_closed"] is True
    assert "development-only-secret" not in report.to_json()


def test_trust_report_preserves_certification_security_controls():
    report = _report()

    assert report.security_hardening["tenant_isolation"] is True
    assert report.security_hardening["authorization_boundaries"] is True
    assert report.security_hardening["fail_closed_behavior"] is True
    assert report.security_hardening["audit_integrity"] is True
    assert report.security_hardening["append_only_evidence"] is True
    assert report.security_hardening["provenance_tracking"] is True
    assert report.security_hardening["memory_advisory_boundary"] is True


def test_release_hygiene_preserves_artifacts_and_blocks_dirty_manifest(tmp_path):
    repository = _isolated_repository(tmp_path)
    runner = EnterpriseTrustClosureRunner(
        generated_at="2026-08-25T00:00:00+00:00",
        commit_sha="synthetic-commit-sha",
        repository_root=repository,
    )
    report = runner.run()

    assert report.release_evidence_hygiene["artifact_provenance"] is True
    assert report.release_evidence_hygiene["immutable_evidence_storage"] is True
    assert report.release_evidence_hygiene["replay_digest_preservation"] is True
    assert report.release_evidence_hygiene["clean_git_state_required"] is False
    assert report.release_evidence_hygiene["release_manifest_correctness"] is False
    assert "TRUST-BLOCKER-CLEAN-WORKTREE" in report.production_blockers


def test_deployment_readiness_reports_unperformed_production_operations():
    report = _report()

    assert report.deployment_readiness["database_migrations_present"] is True
    assert report.deployment_readiness["postgresql_migration_rehearsal_completed"] is False
    assert report.deployment_readiness["backup_restore_verified"] is False
    assert report.deployment_readiness["monitoring_requirements_verified"] is False
    assert report.deployment_readiness["operational_ownership_verified"] is False
    assert report.production_ready is False
    assert "TRUST-BLOCKER-POSTGRES-REHEARSAL" in report.production_blockers
    assert "TRUST-BLOCKER-BACKUP-RESTORE" in report.production_blockers


def test_trust_replay_is_deterministic_and_report_is_append_only(tmp_path):
    first = _report()
    second = _report()
    runner = EnterpriseTrustClosureRunner(commit_sha="synthetic-commit-sha")
    assert runner.verify_replay(first, second)
    assert first.replay_digest == second.replay_digest
    assert first.report_digest
    assert first.immutable is True

    target = tmp_path / "trust-closure.json"
    assert TrustClosureReportGenerator.write(first, target) == target
    with pytest.raises(FileExistsError, match="immutable_trust_closure_exists"):
        TrustClosureReportGenerator.write(first, target)
