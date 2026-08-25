import importlib.util
from pathlib import Path
import sqlite3

import pytest

from services.intelligence.memory import (
    InvestigationMemoryRepository,
    MemoryService,
    OperationalCyberMemoryValidator,
    default_operational_validation_scenarios,
)


def store(service, *, tenant="tenant-a", investigation="inv-1", verdict="malicious", confidence=.8):
    return service.store_investigation_memory(
        {
            "tenant_id": tenant,
            "investigation_id": investigation,
            "case_id": investigation,
            "alert": {"type": "phishing", "category": "credential_access"},
            "artifacts": [{"evidence_id": f"E-{investigation}", "type": "email", "source": "gateway"}],
            "intelligence_provenance": {"provider": "email-gateway"},
        },
        {"summary": "credential access", "confidence": confidence, "mitre_techniques": ["T1566"]},
        {"investigation_id": investigation, "case_id": investigation, "status": "completed", "success": True, "confidence": confidence, "verdict": verdict, "mitre": ["T1566"]},
    )


def test_memory_is_tenant_isolated_and_preserves_provenance():
    service = MemoryService(InvestigationMemoryRepository())
    record = store(service, tenant="tenant-a")
    store(service, tenant="tenant-b", investigation="inv-b")

    assert [item.memory_id for item in service.retrieve_historical_investigations("tenant-a")] == [record.memory_id]
    assert service.retrieve_historical_investigations("tenant-b")[0].tenant_id == "tenant-b"
    assert service.retrieve_historical_investigations("tenant-a")[0].provenance["evidence_ids"] == ["E-inv-1"]
    assert service.repository.audit_events("tenant-a")
    assert service.repository.audit_events("tenant-b")
    assert service.repository.audit_events("tenant-a")[0]["tenant_id"] == "tenant-a"


def test_replay_is_deterministic_and_duplicate_safe():
    service = MemoryService(InvestigationMemoryRepository())
    first = store(service, tenant="tenant-a")
    second = store(service, tenant="tenant-a")

    assert first.memory_id == second.memory_id
    assert len(service.retrieve_historical_investigations("tenant-a")) == 1


def test_similarity_and_confidence_signals_are_advisory_and_deterministic():
    service = MemoryService(InvestigationMemoryRepository())
    store(service, tenant="tenant-a", investigation="inv-1", verdict="malicious", confidence=.8)
    matches = service.retrieve_similar_investigations(
        "security_investigation",
        "phishing",
        tenant_id="tenant-a",
        attack_pattern=["phishing", "credential_access"],
    )
    comparison = service.compare_previous_verdict("tenant-a", "malicious", matches)
    signals = service.confidence_improvement_signals(.95, matches, comparison)

    assert matches[0]["similarity_score"] > 0
    assert comparison["status"] == "reinforced"
    assert signals["confidence_delta"] > 0
    assert signals["advisory_only"] is True


def test_analyst_feedback_is_tenant_scoped_and_audited():
    service = MemoryService(InvestigationMemoryRepository())
    feedback = service.record_analyst_feedback(
        tenant_id="tenant-a",
        investigation_id="inv-1",
        analyst_id="analyst-1",
        verdict="confirmed",
        reason="Evidence supports the verdict",
        evidence_references=["E-1"],
        provenance={"source": "analyst_console"},
    )

    assert service.repository.list_feedback("tenant-a", "inv-1")[0].feedback_id == feedback.feedback_id
    assert service.repository.list_feedback("tenant-b") == []
    assert service.repository.audit_events("tenant-a")[0]["event_type"] == "analyst_feedback_recorded"


def test_missing_tenant_is_fail_closed_for_learning_reads():
    service = MemoryService(InvestigationMemoryRepository())
    with pytest.raises(ValueError, match="memory_tenant_id_required"):
        service.retrieve_historical_investigations("")


def test_investigation_memory_migration_creates_learning_tables():
    migration_path = "database/migrations/007_investigation_memory.py"
    spec = importlib.util.spec_from_file_location("memory_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(migration)
    connection = sqlite3.connect(":memory:")
    migration.upgrade(connection)
    names = {
        row[0]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {
        "investigation_memory",
        "investigation_memory_feedback",
        "investigation_memory_audit",
    }.issubset(names)


def test_investigation_memory_migration_upgrades_legacy_table():
    migration_path = "database/migrations/007_investigation_memory.py"
    spec = importlib.util.spec_from_file_location("memory_migration_legacy", migration_path)
    migration = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(migration)
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """CREATE TABLE investigation_memory (
        memory_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, investigation_type TEXT NOT NULL,
        scenario TEXT NOT NULL, risk_level TEXT NOT NULL, confidence REAL NOT NULL,
        evidence_summary TEXT NOT NULL, reasoning_summary TEXT NOT NULL,
        mitre_techniques TEXT NOT NULL, outcome TEXT NOT NULL, created_at TEXT NOT NULL,
        synthetic_only INTEGER NOT NULL)"""
    )
    migration.upgrade(connection)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(investigation_memory)")}
    assert {"tenant_id", "investigation_id", "provenance", "evidence_fingerprint"}.issubset(columns)


def test_operational_validation_proves_memory_quality_without_control_changes():
    report = OperationalCyberMemoryValidator(generated_at="2026-08-25T00:00:00+00:00").run()

    assert report.validation_result == "passed"
    assert report.scenario_count == 2
    assert report.aggregate_metrics["mean_confidence_change"] > 0
    assert report.aggregate_metrics["mean_evidence_correlation_improvement"] > 0
    assert report.aggregate_metrics["total_analyst_feedback_reuse"] == 2
    assert report.aggregate_metrics["mean_historical_case_relevance"] > 0
    assert "mean_execution_time_change_ms" in report.aggregate_metrics
    assert all(report.control_invariants.values())


def test_operational_validation_memory_is_advisory_and_result_schema_is_preserved():
    report = OperationalCyberMemoryValidator(generated_at="2026-08-25T00:00:00+00:00").run()

    for comparison in report.comparisons:
        assert comparison.disabled.result_confidence == comparison.enabled.result_confidence
        assert comparison.disabled.verdict == comparison.enabled.verdict
        assert comparison.disabled.authorization_status == comparison.enabled.authorization_status
        assert comparison.disabled.fail_closed is comparison.enabled.fail_closed is True
        assert comparison.result_schema_unchanged is True
        assert comparison.disabled.provenance["advisory_only"] is True
        assert comparison.enabled.provenance["advisory_only"] is True


def test_operational_validation_preserves_provenance_and_replay_digest():
    scenarios = default_operational_validation_scenarios()
    first = OperationalCyberMemoryValidator(
        scenarios=scenarios, generated_at="2026-08-25T00:00:00+00:00"
    ).run()
    second = OperationalCyberMemoryValidator(
        scenarios=scenarios, generated_at="2026-08-25T00:00:00+00:00"
    ).run()

    assert first.deterministic_replay["input_output_digest"] == second.deterministic_replay["input_output_digest"]
    assert first.deterministic_replay["timing_excluded"] is True
    assert first.evidence_provenance["scenario_ids"] == [item.scenario_id for item in scenarios]
    assert all(
        item.enabled.provenance["tenant_id"] == scenarios[index].tenant_id
        for index, item in enumerate(first.comparisons)
    )
    report_path = Path(".memory-validation-test-report.json")
    try:
        first.write(report_path)
        assert report_path.exists()
        assert '"validation_result": "passed"' in report_path.read_text(encoding="utf-8")
    finally:
        report_path.unlink(missing_ok=True)
