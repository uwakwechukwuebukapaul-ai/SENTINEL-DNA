from database.connection import DatabaseConnection
from services.intelligence.repository.investigation_persistence_service import InvestigationPersistenceService
from services.intelligence.repository.investigation_repository import InvestigationRepository


def test_investigation_survives_repository_restart(tmp_path):
    db = DatabaseConnection(tmp_path / "investigations.sqlite")
    service = InvestigationPersistenceService(InvestigationRepository(db))
    service.start("INV-1", "CASE-1", tenant_id="TENANT-1", actor_id="ACTOR-1", correlation_id="CORR-1")
    service.persist_result({
        "investigation_id": "INV-1",
        "case_id": "CASE-1",
        "success": True,
        "status": "completed",
        "confidence": 0.91,
        "findings": [{"finding_id": "F-1", "evidence_refs": ["E-1"]}],
        "metadata": {"authorization_capability": "must-not-persist"},
    }, tenant_id="TENANT-1", actor_id="ACTOR-1", correlation_id="CORR-1")

    restarted = InvestigationPersistenceService(InvestigationRepository(db))
    record = restarted.retrieve("INV-1", tenant_id="TENANT-1")
    assert record["status"] == "completed"
    assert record["result"]["findings"][0]["evidence_refs"] == ["E-1"]
    assert "authorization_capability" not in record["result_metadata"]


def test_wrong_tenant_cannot_retrieve_investigation(tmp_path):
    db = DatabaseConnection(tmp_path / "investigations.sqlite")
    service = InvestigationPersistenceService(InvestigationRepository(db))
    service.start("INV-2", "CASE-2", tenant_id="TENANT-A")
    assert service.retrieve("INV-2", tenant_id="TENANT-B") is None
