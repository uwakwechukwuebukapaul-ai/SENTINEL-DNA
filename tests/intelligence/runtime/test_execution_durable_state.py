from database.connection import DatabaseConnection
from services.intelligence.repository.execution_repository import ExecutionEnvelope, ExecutionRepository


def repository(tmp_path):
    return ExecutionRepository(DatabaseConnection(tmp_path / "execution.sqlite"))


def test_execution_state_persists_and_is_tenant_scoped(tmp_path):
    repo = repository(tmp_path)
    envelope = ExecutionEnvelope(
        execution_id="EXE-1",
        tenant_id="tenant-a",
        actor_id="analyst-a",
        investigation_id="INV-1",
        alert_reference="ALERT-1",
        status="FAILED",
        task_states=[{"task_id": "TASK-1", "state": "FAILED"}],
        evidence_references=["EVD-1"],
        failures=[{"error_code": "handler_exception", "error": "Capability handler failed"}],
        unavailable_reasons=[{"service": "threat_intelligence", "reason": "Provider timed out"}],
    )
    repo.save(envelope)

    assert repo.get("EXE-1", "tenant-a")["status"] == "FAILED"
    assert repo.get("EXE-1", "tenant-a")["evidence_references"] == ["EVD-1"]
    assert repo.get("EXE-1", "tenant-b") is None


def test_provider_health_snapshot_persists_without_provider_payload(tmp_path):
    repo = repository(tmp_path)
    repo.save(ExecutionEnvelope("EXE-2", "tenant-a", "analyst-a", "INV-2", "ALERT-2"))
    repo.save_provider_health(
        execution_id="EXE-2",
        tenant_id="tenant-a",
        snapshots=[{
            "provider": "provider-neutral",
            "status": "UNAVAILABLE",
            "timestamp": "2026-08-22T00:00:00+00:00",
            "failure_count": 1,
            "unavailable_reason": "provider timed out",
            "policy_decision": "allowed",
        }],
    )
    assert repo.get("EXE-2", "tenant-a")["execution_id"] == "EXE-2"


def test_failure_and_unavailable_states_are_replayable(tmp_path):
    repo = repository(tmp_path)
    envelope = ExecutionEnvelope(
        "EXE-3", "tenant-a", "analyst-a", "INV-3", "ALERT-3",
        status="UNAVAILABLE",
        task_states=[{"task_id": "TASK-3", "state": "UNAVAILABLE"}],
        unavailable_reasons=[{"service": "provider-neutral", "reason": "not configured"}],
    )
    repo.save(envelope)
    replay = repo.get("EXE-3", "tenant-a")
    assert replay["status"] == "UNAVAILABLE"
    assert replay["unavailable_reasons"][0]["reason"] == "not configured"
