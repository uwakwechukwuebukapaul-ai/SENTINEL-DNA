import json
import subprocess
from pathlib import Path

from deployment.validation.ownership import OperationalOwnershipEvidenceValidator, REQUIRED_EVIDENCE
from deployment.validation.postgres_rehearsal import PostgresRehearsalValidator, REQUIRED_CHECKS
from deployment.validation.release_hygiene import ReleaseHygieneValidator
from deployment.validation.runtime_readiness import RuntimeReadinessValidator
from services.intelligence.certification import EvidenceClosureReportGenerator, EnterpriseEvidenceClosureRunner
from services.intelligence.certification.evidence_closure import SOURCE_NAMES


def _initialize_git_repository(repository_root: Path) -> None:
    subprocess.run(["git", "init"], cwd=repository_root, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "config", "user.name", "deployment-test-fixture"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "deployment-test-fixture@example.invalid"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "Initialize deployment test repository"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )


def _postgres_evidence():
    return {
        "database_engine": "postgresql",
        "rehearsal_scope": "disposable",
        "credentials_used": False,
        "external_connections": False,
        "customer_data_used": False,
        "migration_versions": [1, 2, 3],
        "checks": {name: True for name in REQUIRED_CHECKS},
        "record_counts": {"investigations": 2, "audit_events": 2},
        "tenant_ids": ["tenant-a", "tenant-b"],
        "provenance_digest": "provenance-digest",
        "audit_digest": "audit-digest",
        "investigation_digest": "investigation-digest",
    }


def test_postgres_rehearsal_is_blocked_without_disposable_evidence(tmp_path):
    report = PostgresRehearsalValidator(repository_root=tmp_path, generated_at="2026-08-25T00:00:00+00:00").run()

    assert report["validation_result"] == "blocked"
    assert "POSTGRES-REHEARSAL:evidence_not_supplied" in report["blockers"]
    assert report["evidence"]["production_database_touched"] is False
    assert report["evidence"]["secrets_serialized"] is False


def test_postgres_rehearsal_accepts_bounded_disposable_evidence_and_replays_deterministically(tmp_path):
    evidence = _postgres_evidence()
    first = PostgresRehearsalValidator(
        repository_root=tmp_path,
        evidence=evidence,
        generated_at="2026-01-01T00:00:00+00:00",
    ).run()
    second = PostgresRehearsalValidator(
        repository_root=tmp_path,
        evidence=evidence,
        generated_at="2027-01-01T00:00:00+00:00",
    ).run()

    assert first["validation_result"] == "passed"
    assert first["replay_digest"] == second["replay_digest"]
    assert first["report_digest"] != second["report_digest"]


def test_postgres_rehearsal_missing_migration_check_remains_pending(tmp_path):
    evidence = _postgres_evidence()
    evidence["checks"].pop("rollback_capability")
    report = PostgresRehearsalValidator(repository_root=tmp_path, evidence=evidence).run()

    assert report["validation_result"] == "blocked"
    assert "rollback_capability" in report["pending_checks"]


def test_operational_ownership_requires_real_assignments(tmp_path):
    documentation = tmp_path / "OPERATIONAL_OWNERSHIP_EVIDENCE.md"
    documentation.write_text("TBD — assign real operators", encoding="utf-8")
    report = OperationalOwnershipEvidenceValidator(
        repository_root=tmp_path,
        documentation_path=documentation,
    ).run()

    assert report["validation_result"] == "blocked"
    assert set(report["pending_checks"]) == set(REQUIRED_EVIDENCE)
    assert report["evidence"]["owner_values_serialized"] is False


def test_operational_ownership_passes_only_with_complete_evidence(tmp_path):
    documentation = tmp_path / "OPERATIONAL_OWNERSHIP_EVIDENCE.md"
    documentation.write_text("assigned evidence", encoding="utf-8")
    evidence_path = tmp_path / "ownership.json"
    evidence_path.write_text(json.dumps({name: "assigned-evidence-reference" for name in REQUIRED_EVIDENCE}), encoding="utf-8")
    report = OperationalOwnershipEvidenceValidator(
        repository_root=tmp_path,
        evidence_path=evidence_path,
        documentation_path=documentation,
    ).run()

    assert report["validation_result"] == "passed"
    assert report["pending_checks"] == []


def test_runtime_readiness_fails_closed_without_configuration(tmp_path):
    _initialize_git_repository(tmp_path)
    report = RuntimeReadinessValidator(repository_root=tmp_path, environ={}).run().to_dict()

    assert report["validation_result"] == "blocked"
    assert report["checks"]["missing_secrets_fail_closed"] is True
    assert report["checks"]["required_production_configuration_keys"] is False
    assert report["evidence"]["secret_values_serialized"] is False
    assert "super-secret-value" not in json.dumps(report)


def test_release_hygiene_fails_closed_for_dirty_or_unproven_release(tmp_path):
    validator = ReleaseHygieneValidator(
        repository_root=".",
        generated_at="2026-08-25T00:00:00+00:00",
    )
    first = validator.run()
    second = ReleaseHygieneValidator(
        repository_root=".",
        generated_at="2027-01-01T00:00:00+00:00",
    ).run()

    assert first["validation_result"] == "blocked"
    assert "RELEASE-HYGIENE:artifact_provenance_missing_or_invalid" in first["blockers"]
    assert first["replay_digest"] == second["replay_digest"]
    assert first["report_digest"] != second["report_digest"]


def test_release_hygiene_rejects_tampered_immutable_closure_artifact(tmp_path):
    commit_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    source_factories = {
        name: (lambda name=name: {
            "report_version": f"{name}.v1",
            "report_digest": f"report-{name}",
            "replay_digest": f"replay-{name}",
            "validation_result": "passed",
            "safety_validation": {"fixture_safe": True},
            "checks": {"fixture_check": True},
        })
        for name in SOURCE_NAMES
    }
    report = EnterpriseEvidenceClosureRunner(
        source_factories=source_factories,
        commit_sha=commit_sha,
    ).run()
    artifact = tmp_path / "closure.json"
    EvidenceClosureReportGenerator.write(report, artifact)

    assert ReleaseHygieneValidator._artifact_is_valid(artifact, commit_sha) is True
    tampered = json.loads(artifact.read_text(encoding="utf-8"))
    tampered["passed_controls"].append("tampered-control")
    tampered_path = tmp_path / "tampered.json"
    tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
    assert ReleaseHygieneValidator._artifact_is_valid(tampered_path, commit_sha) is False
