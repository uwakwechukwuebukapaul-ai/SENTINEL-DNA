from database.connection import DatabaseConnection
from services.intelligence.investigation.artifacts import InvestigationArtifactBuilder, project_artifacts
from services.intelligence.repository.artifact_repository import InvestigationArtifactRepository


def result():
    return {
        "investigation_id": "INV-1",
        "case_id": "CASE-1",
        "tenant_context": {"tenant_id": "TENANT-1"},
        "confidence": 0.91,
        "findings": [{"title": "Suspicious execution", "severity": "high", "evidence_refs": ["E-1"], "source": "evidence_reasoner"}],
        "recommendations": ["Review affected host"],
        "iocs": [{"ioc_id": "IOC-1", "ioc_type": "ip", "value": "1.2.3.4", "provenance": {"source": "provider-a"}}],
        "mitre": ["T1059"],
        "timeline": [{"event_id": "EV-1", "timestamp": "2026-01-01T00:00:00Z", "event_type": "observed", "description": "Observed event"}],
        "risk": {"score": 80, "severity": "high"},
        "metadata": {"authorization_capability": "secret", "database_path": "soc.db"},
    }


def test_builder_normalizes_supported_artifacts_and_ids_are_deterministic():
    builder = InvestigationArtifactBuilder()
    first = builder.build(result())
    second = builder.build(result())
    assert {item.artifact_type for item in first} == {
        "finding", "recommendation", "ioc", "mitre_technique", "timeline_event", "risk_assessment", "confidence_assessment",
    }
    assert [item.artifact_id for item in first] == [item.artifact_id for item in second]
    ioc = next(item for item in first if item.artifact_type == "ioc")
    assert ioc.payload == {"ioc_id": "IOC-1", "ioc_type": "ip", "value": "1.2.3.4"}


def test_artifacts_persist_and_retrieve_by_type(tmp_path):
    repository = InvestigationArtifactRepository(DatabaseConnection(tmp_path / "artifacts.sqlite"))
    artifacts = InvestigationArtifactBuilder().build(result())
    repository.save_many(artifacts)
    restarted = InvestigationArtifactRepository(DatabaseConnection(tmp_path / "artifacts.sqlite"))
    iocs = restarted.get_for_investigation("INV-1", tenant_id="TENANT-1", artifact_type="ioc")
    assert len(iocs) == 1
    assert iocs[0]["payload"]["ioc_id"] == "IOC-1"
    assert "authorization_capability" not in iocs[0]["payload"]


def test_consumer_projection_groups_canonical_artifacts_without_raw_metadata():
    projected = project_artifacts([item.to_dict() for item in InvestigationArtifactBuilder().build(result())])
    assert projected["findings"][0]["title"] == "Suspicious execution"
    assert projected["iocs"] == [{
        "ioc_id": "IOC-1", "ioc_type": "ip", "value": "1.2.3.4",
        "artifact_id": projected["iocs"][0]["artifact_id"],
        "evidence_refs": [], "provenance": {"source": "provider-a"}, "confidence": None,
    }]
    assert "authorization_capability" not in projected["findings"][0]
