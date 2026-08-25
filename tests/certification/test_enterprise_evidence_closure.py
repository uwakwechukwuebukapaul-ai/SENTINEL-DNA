import pytest

from services.intelligence.certification import (
    EnterpriseEvidenceClosureRunner,
    EvidenceClosureReportGenerator,
)


EXPECTED_SOURCES = {
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
}


def _fake_sources(*, missing: str | None = None, failed: str | None = None):
    sources = {}
    for name in EXPECTED_SOURCES:
        if name == missing:
            sources[name] = lambda: None
            continue
        payload = {
            "report_version": f"{name}.v1",
            "report_digest": f"report-{name}",
            "replay_digest": f"replay-{name}",
            "validation_result": "failed" if name == failed else "passed",
            "safety_validation": {"fixture_safe": name != failed},
        }
        if name == "enterprise_readiness_certification":
            payload["controls"] = [{"control_id": "CERT-FIXTURE", "name": "Fixture control", "domain": "security", "passed": name != failed}]
        if name in {"deployment_contract_validation", "recovery_readiness_validation"}:
            payload["contracts"] = [{"contract": "fixture_contract", "status": "failed" if name == failed else "passed", "checks": {"fixture_check": name != failed}}]
        if name == "billing_entitlement_validation":
            payload["scenarios"] = [{"scenario_id": "fixture-billing", "title": "Fixture billing", "status": "failed" if name == failed else "passed"}]
            payload["security_invariants"] = {"fixture_billing_safe": name != failed}
        if name in {"runtime_readiness", "database_rehearsal", "postgres_rehearsal", "backup_restore", "operational_ownership", "release_hygiene"}:
            payload["checks"] = {"fixture_check": name != failed}
        if name == "trust_closure":
            payload["production_ready"] = name != failed
            payload["production_blockers"] = ["TRUST-FIXTURE-BLOCKER"] if name == failed else []
        sources[name] = lambda payload=payload: payload
    return sources


def test_closure_discovers_all_required_evidence_sources():
    report = EnterpriseEvidenceClosureRunner(
        generated_at="2026-08-25T00:00:00+00:00",
        commit_sha="synthetic-commit-sha",
    ).run()

    assert {item["source"] for item in report.evidence_sources} == EXPECTED_SOURCES
    assert len(report.replay_digest_references) == len(EXPECTED_SOURCES)
    assert all(item["replay_digest"] for item in report.evidence_sources)
    assert report.total_controls == len(report.control_matrix)

    operational_sources = {
        item["source"] for item in report.evidence_sources
        if item["source"] in {"runtime_readiness", "database_rehearsal", "postgres_rehearsal", "backup_restore", "operational_ownership", "release_hygiene"}
    }
    assert operational_sources == {"runtime_readiness", "database_rehearsal", "postgres_rehearsal", "backup_restore", "operational_ownership", "release_hygiene"}


def test_missing_required_evidence_fails_closed():
    report = EnterpriseEvidenceClosureRunner(
        source_factories=_fake_sources(missing="billing_entitlement_validation"),
        commit_sha="synthetic-commit-sha",
    ).run()

    source = next(item for item in report.evidence_sources if item["source"] == "billing_entitlement_validation")
    assert source["status"] == "missing"
    assert "EVIDENCE-SOURCE-MISSING:billing_entitlement_validation" in report.remaining_blockers
    assert report.closure_result == "blocked"


def test_missing_replay_digest_fails_closed():
    sources = _fake_sources()
    sources["billing_entitlement_validation"] = lambda: {
        "report_version": "billing.v1",
        "report_digest": "billing-report",
        "validation_result": "passed",
    }

    report = EnterpriseEvidenceClosureRunner(source_factories=sources, commit_sha="synthetic-commit-sha").run()

    assert "EVIDENCE-REPLAY-MISSING:billing_entitlement_validation" in report.remaining_blockers
    assert report.closure_result == "blocked"


def test_closure_replay_is_deterministic_and_artifact_digest_tracks_metadata():
    first = EnterpriseEvidenceClosureRunner(
        generated_at="2026-01-01T00:00:00+00:00",
        commit_sha="synthetic-commit-sha",
        source_factories=_fake_sources(),
    ).run()
    second = EnterpriseEvidenceClosureRunner(
        generated_at="2027-01-01T00:00:00+00:00",
        commit_sha="synthetic-commit-sha",
        source_factories=_fake_sources(),
    ).run()

    assert first.closure_result == "passed"
    assert first.replay_digest == second.replay_digest
    assert first.artifact_digest != second.artifact_digest


def test_blocker_reporting_identifies_failed_source_and_controls():
    report = EnterpriseEvidenceClosureRunner(
        source_factories=_fake_sources(failed="deployment_contract_validation"),
        commit_sha="synthetic-commit-sha",
    ).run()

    assert "EVIDENCE-SOURCE-FAILED:deployment_contract_validation" in report.remaining_blockers
    assert "CONTROL-FAILED:DEPLOYMENT_CONTRACT_VALIDATION:fixture_contract:fixture_check" in report.remaining_blockers
    assert "TRUST-FIXTURE-BLOCKER" not in report.remaining_blockers


def test_closure_artifact_is_append_only(tmp_path):
    report = EnterpriseEvidenceClosureRunner(
        source_factories=_fake_sources(),
        commit_sha="synthetic-commit-sha",
    ).run()
    target = tmp_path / "enterprise-evidence-closure.json"

    assert EvidenceClosureReportGenerator.write(report, target) == target
    with pytest.raises(FileExistsError, match="immutable_evidence_closure_exists"):
        EvidenceClosureReportGenerator.write(report, target)


def test_closure_preserves_protected_boundaries():
    report = EnterpriseEvidenceClosureRunner(
        source_factories=_fake_sources(),
        commit_sha="synthetic-commit-sha",
    ).run()

    assert report.provenance_metadata["protected_runtime_contracts_changed"] is False
    assert report.provenance_metadata["deployment_performed"] is False
    assert all(item["provenance"]["secrets_serialized"] is False for item in report.evidence_sources)
