from concurrent.futures import ThreadPoolExecutor

import pytest

from database.connection import DatabaseConnection
from services.intelligence.repository.execution_repository import (
    ExecutionRepository,
    JobConflictError,
    JobLeaseError,
)
from services.intelligence.runtime.investigation_job import InvestigationJob
from services.intelligence.runtime.investigation_lifecycle import (
    InvestigationLifecycleState,
    InvalidInvestigationTransition,
    validate_transition,
)
from services.intelligence.runtime.task import Task
from tests.credential_helpers import random_password


def repository(tmp_path):
    return ExecutionRepository(DatabaseConnection(tmp_path / "investigation-jobs.sqlite"))


def job(**changes):
    values = {
        "job_id": "JOB-1",
        "tenant_id": "tenant-a",
        "case_id": "CASE-1",
        "investigation_id": "INV-1",
        "execution_id": "EXE-1",
        "trigger_id": "TRIGGER-1",
        "idempotency_key": "tenant-a:event-1",
        "actor_id": "actor-a",
        "service_identity": None,
        "correlation_id": "CORR-1",
    }
    values.update(changes)
    return InvestigationJob(**values)


def test_lifecycle_accepts_legal_transitions_and_rejects_unauthorized_requeue():
    validate_transition(None, "PENDING")
    validate_transition("PENDING", "QUEUED")
    validate_transition("QUEUED", "RUNNING")
    validate_transition("RUNNING", "WAITING_FOR_EVIDENCE")
    validate_transition("RUNNING", "FOLLOW_UP")
    validate_transition("WAITING_FOR_EVIDENCE", "FOLLOW_UP")
    validate_transition("FOLLOW_UP", "QUEUED")
    for terminal in ("COMPLETED", "FAILED", "TIMED_OUT", "CANCELLED", "ESCALATED", "BLOCKED"):
        with pytest.raises(InvalidInvestigationTransition):
            validate_transition(terminal, "RUNNING")
    with pytest.raises(InvalidInvestigationTransition):
        validate_transition("RUNNING", "QUEUED")
    validate_transition("RUNNING", "QUEUED", recovery_authorized=True)


def test_job_creation_is_idempotent_and_context_conflicts_fail(tmp_path):
    repo = repository(tmp_path)
    created = repo.create_job(job())
    duplicate = repo.create_job(job())
    assert duplicate.job_id == created.job_id
    assert repo.get_job_by_idempotency_key("tenant-a:event-1", "tenant-a").job_id == "JOB-1"
    with pytest.raises(JobConflictError):
        repo.create_job(job(case_id="CASE-OTHER"))
    assert repo.get_job("JOB-1", "tenant-b") is None


def test_job_transition_is_durable_and_audited(tmp_path):
    repo = repository(tmp_path)
    repo.create_job(job())
    transitioned = repo.transition_job(
        "JOB-1", "tenant-a", "QUEUED", service_identity="intake", reason="eligible"
    )
    assert transitioned.state == InvestigationLifecycleState.QUEUED
    reloaded = repository(tmp_path).get_job("JOB-1", "tenant-a")
    assert reloaded.state == InvestigationLifecycleState.QUEUED
    assert [item["next_state"] for item in reloaded.state_history] == ["PENDING", "QUEUED"]
    audit = repo.audit_service.list_for_tenant("tenant-a", limit=20)
    assert [item["sequence_number"] for item in reversed(audit)] == [1, 2]
    assert all(item["event_type"] == "INVESTIGATION_JOB_TRANSITION" for item in audit)


def test_terminal_jobs_cannot_transition_or_be_cancelled(tmp_path):
    repo = repository(tmp_path)
    repo.create_job(job())
    repo.transition_job("JOB-1", "tenant-a", "QUEUED", service_identity="intake")
    repo.transition_job("JOB-1", "tenant-a", "RUNNING", service_identity="worker")
    repo.transition_job("JOB-1", "tenant-a", "COMPLETED", service_identity="worker")
    with pytest.raises(InvalidInvestigationTransition):
        repo.transition_job("JOB-1", "tenant-a", "RUNNING", service_identity="worker")
    cancelled = repo.request_cancellation("JOB-1", "tenant-a", actor_id="actor-a")
    assert cancelled.state == InvestigationLifecycleState.COMPLETED
    assert cancelled.cancel_requested is False


def test_atomic_claim_and_lease_heartbeat(tmp_path):
    repo = repository(tmp_path)
    repo.create_job(job())
    repo.transition_job("JOB-1", "tenant-a", "QUEUED", service_identity="intake")
    first = repo.claim_job("worker-a", lease_seconds=60)
    assert first.state == InvestigationLifecycleState.RUNNING
    with pytest.raises(JobLeaseError):
        repo.heartbeat_job("JOB-1", "tenant-a", "worker-b")
    second = repository(tmp_path).claim_job("worker-b", lease_seconds=60)
    assert second is None
    renewed = repo.heartbeat_job("JOB-1", "tenant-a", "worker-a", lease_seconds=60)
    assert renewed.heartbeat_at is not None


def test_only_one_concurrent_claim_succeeds(tmp_path):
    setup = repository(tmp_path)
    setup.create_job(job())
    setup.transition_job("JOB-1", "tenant-a", "QUEUED", service_identity="intake")
    repositories = [repository(tmp_path), repository(tmp_path)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda item: item[1].claim_job(item[0], lease_seconds=60), zip(("worker-a", "worker-b"), repositories)))
    assert sum(result is not None for result in results) == 1


def test_expired_lease_is_recovered_or_failed_by_attempt_budget(tmp_path):
    repo = repository(tmp_path)
    repo.create_job(job(
        max_attempts=2,
        created_at="2026-08-23T23:59:00+00:00",
        available_at="2026-08-23T23:59:00+00:00",
    ))
    repo.transition_job("JOB-1", "tenant-a", "QUEUED", service_identity="intake")
    claimed = repo.claim_job("worker-a", lease_seconds=1, now="2026-08-24T00:00:00+00:00")
    assert claimed.state == InvestigationLifecycleState.RUNNING
    recovered = repo.recover_expired_jobs(now="2026-08-24T00:00:02+00:00")
    assert recovered[0].state == InvestigationLifecycleState.QUEUED
    claimed_again = repo.claim_job("worker-b", lease_seconds=1, now="2026-08-24T00:00:02+00:00")
    assert claimed_again.attempts == 2
    failed = repo.recover_expired_jobs(now="2026-08-24T00:00:04+00:00")
    assert failed[0].state == InvestigationLifecycleState.FAILED


def test_cancellation_is_tenant_scoped_and_persisted(tmp_path):
    repo = repository(tmp_path)
    repo.create_job(job())
    assert repo.request_cancellation("JOB-1", "tenant-b", actor_id="actor-b") is None
    cancelled = repo.request_cancellation("JOB-1", "tenant-a", actor_id="actor-a")
    assert cancelled.state == InvestigationLifecycleState.CANCELLED
    assert cancelled.cancel_requested is True
    assert repo.get_cancellation_state("JOB-1", "tenant-a") is True


def test_audit_redacts_secret_like_metadata_and_preserves_sequence(tmp_path):
    repo = repository(tmp_path)
    password = random_password()
    repo.create_job(job())
    repo.record_audit_event(
        tenant_id="tenant-a", job_id="JOB-1", event_type="TEST_SAFE_EVENT",
        actor_id="actor-a", case_id="CASE-1", investigation_id="INV-1",
        execution_id="EXE-1", metadata={"password": password, "safe": "ok"},
    )
    events = repo.audit_service.list_for_tenant("tenant-a", limit=20)
    event = next(item for item in events if item["event_type"] == "TEST_SAFE_EVENT")
    assert event["sequence_number"] == 2
    assert event["details"]["password"] == "[REDACTED]"
    assert password not in str(event)


def test_audit_identity_mismatch_fails_closed(tmp_path):
    repo = repository(tmp_path)
    repo.create_job(job())
    with pytest.raises(PermissionError):
        repo.record_audit_event(
            tenant_id="tenant-b", job_id="JOB-1", event_type="CROSS_TENANT",
            actor_id="actor-b", case_id="CASE-1", investigation_id="INV-1",
            execution_id="EXE-1",
        )
    with pytest.raises(PermissionError):
        repo.record_audit_event(
            tenant_id="tenant-a", job_id="JOB-1", event_type="WRONG_CASE",
            actor_id="actor-a", case_id="CASE-OTHER", investigation_id="INV-1",
            execution_id="EXE-1",
        )


def test_task_lineage_fields_are_backward_compatible():
    task = Task(capability="analysis", payload={"value": 1}, job_id="JOB-1", tenant_id="tenant-a", iteration=1)
    serialized = task.to_dict()
    assert serialized["job_id"] == "JOB-1"
    assert serialized["tenant_id"] == "tenant-a"
    assert serialized["iteration"] == 1
