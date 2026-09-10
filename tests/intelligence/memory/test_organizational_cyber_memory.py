import importlib.util
import sqlite3

import pytest

from services.intelligence.memory import (
    AttackCampaignMemory,
    AnalystKnowledgeEntry,
    DetectionLearningRecord,
    InvestigationPattern,
    OrganizationalMemoryRepository,
    OrganizationalMemoryValidator,
    ResponsePlaybookMemory,
    default_organizational_validation_scenarios,
)
from services.intelligence.memory.similarity import DeterministicSimilarityProvider


def test_consolidation_produces_all_domain_records_with_provenance_and_hashes():
    validator = OrganizationalMemoryValidator(generated_at="2026-08-25T00:00:00+00:00")
    scenario = default_organizational_validation_scenarios()[0]
    source, organization, consolidation = validator._seed(scenario)
    try:
        assert consolidation.validation_gate == "validated_source_and_findings"
        assert {type(item) for item in consolidation.records} == {
            InvestigationPattern,
            AttackCampaignMemory,
            AnalystKnowledgeEntry,
            DetectionLearningRecord,
            ResponsePlaybookMemory,
        }
        for item in consolidation.records:
            assert item.tenant_id == scenario.tenant_id
            assert item.source_investigation_id == scenario.source_investigation_id
            assert item.evidence_provenance["source_investigation_id"] == scenario.source_investigation_id
            assert item.why_stored
            assert item.created_at == "2026-01-01T00:00:00+00:00"
            assert len(item.audit_hash) == 64
            assert item.advisory_only is True
        assert len(organization.repository.audit_events(scenario.tenant_id)) >= 5
    finally:
        source.repository.close()
        organization.repository.close()


def test_organizational_memory_is_tenant_isolated_and_append_only():
    validator = OrganizationalMemoryValidator(generated_at="2026-08-25T00:00:00+00:00")
    scenario = default_organizational_validation_scenarios()[0]
    source, organization, _ = validator._seed(scenario)
    try:
        assert organization.repository.list("other-tenant") == []
        record_data = organization.repository.list(scenario.tenant_id)[0].to_dict()
        record_id = next(record_data[key] for key in ("pattern_id", "campaign_id", "knowledge_id", "detection_id", "playbook_memory_id") if record_data.get(key))
        with pytest.raises(sqlite3.IntegrityError, match="organizational_memory_is_append_only"):
            organization.repository._connection.execute(
                "UPDATE organizational_memory SET confidence=0 WHERE record_id=?", (record_id,)
            )
    finally:
        source.repository.close()
        organization.repository.close()


def test_similarity_provider_is_deterministic_and_provider_neutral():
    provider = DeterministicSimilarityProvider()
    assert provider.provider_name == "deterministic-jaccard-v1"
    assert provider.similarity(["phishing", "T1566"], ["phishing", "T1566"]) == 1.0
    assert provider.similarity(["phishing"], ["ransomware"]) == 0.0
    assert provider.rank(["phishing"], [("b", ["ransomware"]), ("a", ["phishing"])])[0]["record_id"] == "a"


def test_organizational_validation_proves_advisory_context_without_control_changes():
    first = OrganizationalMemoryValidator(generated_at="2026-08-25T00:00:00+00:00").run()
    second = OrganizationalMemoryValidator(generated_at="2026-08-25T00:00:00+00:00").run()
    comparison = first.comparisons[0]

    assert first.validation_result == "passed"
    assert comparison.memory_disabled_context_count == 0
    assert comparison.memory_enabled_context_count >= 1
    assert comparison.historical_relevance > 0
    assert comparison.latency_change_ms >= -comparison.disabled_latency_ms
    assert all(first.control_invariants.values())
    assert first.deterministic_replay["replay_digest"] == second.deterministic_replay["replay_digest"]
    assert first.deterministic_replay["timings_excluded"] is True


def test_organizational_memory_migration_creates_append_only_tables():
    path = "database/migrations/008_organizational_cyber_memory.py"
    spec = importlib.util.spec_from_file_location("organizational_memory_migration", path)
    migration = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(migration)
    connection = sqlite3.connect(":memory:")
    migration.upgrade(connection)
    names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"organizational_memory", "organizational_memory_audit"}.issubset(names)
