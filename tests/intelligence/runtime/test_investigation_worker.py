import pytest

from database.connection import DatabaseConnection
from services.intelligence.investigation.investigation_result import InvestigationResult
from services.intelligence.repository.execution_repository import ExecutionRepository, JobLeaseError
from services.intelligence.runtime.investigation_job import InvestigationJob
from services.intelligence.runtime.investigation_lifecycle import InvestigationLifecycleState
from services.intelligence.runtime.investigation_worker import (
    InvestigationWorker,
    RetryableInvestigationError,
)


def repository(tmp_path):
    return ExecutionRepository(DatabaseConnection(tmp_path / "investigation-worker.sqlite"))


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


def enqueue(repo, value=None):
    repo.create_job(value or job())
    repo.transition_job(
        (value or job()).job_id,
        (value or job()).tenant_id,
        InvestigationLifecycleState.QUEUED,
        service_identity="intake",
    )


def fixed_clock(value="2026-08-24T00:00:00+00:00"):
    current = {"value": value}

    def now():
        return current["value"]

    return current, now


def events(repo):
    return [item["event_type"] for item in repo.audit_service.list_for_tenant("tenant-a", limit=100)]


def authorize_worker(_job, identity):
    return identity in {"worker-a", "worker-b"}


def test_worker_executes_canonical_adapter_and_completes_job(tmp_path):
    repo = repository(tmp_path)
    enqueue(repo)
    calls = []

    def canonical(job_value):
        calls.append(job_value.job_id)
        return InvestigationResult(success=True, status="completed", case_id=job_value.case_id)

    worker = InvestigationWorker(
        repo,
        service_identity="worker-a",
        investigate=canonical,
        authorize_job=authorize_worker,
        heartbeat_interval_seconds=0,
    )
    completed = worker.run_once(tenant_id="tenant-a")

    assert calls == ["JOB-1"]
    assert completed.state == InvestigationLifecycleState.COMPLETED
    assert repo.get_job("JOB-1", "tenant-a").state == InvestigationLifecycleState.COMPLETED
    assert {"WORKER_CLAIMED", "WORKER_HEARTBEAT", "INVESTIGATION_STARTED", "INVESTIGATION_COMPLETED"}.issubset(events(repo))


def test_worker_without_authorization_hook_denies_before_execution(tmp_path):
    repo = repository(tmp_path)
    enqueue(repo)
    called = []
    worker = InvestigationWorker(
        repo,
        service_identity="worker-a",
        investigate=lambda _job: called.append(True),
        heartbeat_interval_seconds=0,
    )

    blocked = worker.run_once()

    assert blocked.state is InvestigationLifecycleState.BLOCKED
    assert called == []


def test_worker_without_service_identity_fails_closed(tmp_path):
    repo = repository(tmp_path)

    with pytest.raises(ValueError, match="service_identity"):
        InvestigationWorker(
            repo,
            service_identity=None,
            investigate=lambda _job: InvestigationResult(success=True, status="completed"),
            authorize_job=authorize_worker,
        )


def test_worker_with_unauthorized_identity_denies_before_execution(tmp_path):
    repo = repository(tmp_path)
    enqueue(repo)
    called = []
    worker = InvestigationWorker(
        repo,
        service_identity="worker-b",
        investigate=lambda _job: called.append(True),
        authorize_job=lambda _job, identity: identity == "worker-a",
        heartbeat_interval_seconds=0,
    )

    blocked = worker.run_once()

    assert blocked.state is InvestigationLifecycleState.BLOCKED
    assert called == []


def test_worker_uses_coordinator_without_replacing_public_contract(tmp_path):
    repo = repository(tmp_path)
    enqueue(repo)
    calls = []

    class Coordinator:
        def investigate(self, **kwargs):
            calls.append(kwargs)
            return InvestigationResult(success=True, status="completed")

    worker = InvestigationWorker(
        repo,
        service_identity="worker-a",
        coordinator=Coordinator(),
        authorize_job=authorize_worker,
        heartbeat_interval_seconds=0,
    )
    worker.run_once()

    assert calls[0]["case_id"] == "CASE-1"
    assert calls[0]["tenant_id"] == "tenant-a"
    assert calls[0]["execution_id"] == "EXE-1"


def test_worker_persists_non_retryable_failure(tmp_path):
    repo = repository(tmp_path)
    enqueue(repo)

    def failing(_job):
        raise RuntimeError("safe failure")

    worker = InvestigationWorker(
        repo,
        service_identity="worker-a",
        investigate=failing,
        authorize_job=authorize_worker,
        heartbeat_interval_seconds=0,
    )
    failed = worker.run_once()

    assert failed.state == InvestigationLifecycleState.FAILED
    assert failed.failure_code == "investigation_failed"
    assert "RuntimeError" in failed.failure_reason
    assert "INVESTIGATION_FAILED" in events(repo)


def test_worker_retries_only_explicit_retryable_failure_with_backoff(tmp_path):
    repo = repository(tmp_path)
    current, now = fixed_clock()
    enqueue(repo, job(created_at=current["value"], available_at=current["value"], max_attempts=2))
    attempts = {"count": 0}

    def sometimes_fails(_job):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RetryableInvestigationError("transient")
        return InvestigationResult(success=True, status="completed")

    worker = InvestigationWorker(
        repo,
        service_identity="worker-a",
        investigate=sometimes_fails,
        authorize_job=authorize_worker,
        heartbeat_interval_seconds=0,
        retry_delay_seconds=10,
        clock=now,
    )
    retried = worker.run_once()
    assert retried.state == InvestigationLifecycleState.QUEUED
    assert retried.attempts == 1
    assert retried.available_at == "2026-08-24T00:00:10+00:00"
    assert worker.run_once() is None

    current["value"] = "2026-08-24T00:00:11+00:00"
    completed = worker.run_once()
    assert completed.state == InvestigationLifecycleState.COMPLETED
    assert attempts["count"] == 2


def test_worker_cancellation_during_execution_is_cooperative(tmp_path):
    repo = repository(tmp_path)
    enqueue(repo)

    def cancel_from_execution(job_value):
        repo.request_cancellation(job_value.job_id, job_value.tenant_id, actor_id="operator")
        return InvestigationResult(success=True, status="completed")

    worker = InvestigationWorker(
        repo,
        service_identity="worker-a",
        investigate=cancel_from_execution,
        authorize_job=authorize_worker,
        heartbeat_interval_seconds=0,
    )
    cancelled = worker.run_once()

    assert cancelled.state == InvestigationLifecycleState.CANCELLED
    assert "INVESTIGATION_CANCELLED" in events(repo)


def test_worker_blocks_unauthorized_service_without_execution(tmp_path):
    repo = repository(tmp_path)
    enqueue(repo)
    called = []
    worker = InvestigationWorker(
        repo,
        service_identity="worker-a",
        investigate=lambda _job: called.append(True),
        authorize_job=lambda _job, _identity: False,
        heartbeat_interval_seconds=0,
    )

    blocked = worker.run_once()

    assert blocked.state == InvestigationLifecycleState.BLOCKED
    assert called == []


def test_stale_worker_cannot_finalize_recovered_job(tmp_path):
    repo = repository(tmp_path)
    current, now = fixed_clock()
    enqueue(repo, job(created_at=current["value"], available_at=current["value"], max_attempts=2))
    worker_a = InvestigationWorker(
        repo,
        service_identity="worker-a",
        investigate=lambda _job: InvestigationResult(success=True, status="completed"),
        authorize_job=authorize_worker,
        lease_seconds=1,
        heartbeat_interval_seconds=0,
        clock=now,
    )
    claimed = repo.claim_job("worker-a", lease_seconds=1, now=now())
    assert claimed.state == InvestigationLifecycleState.RUNNING
    current["value"] = "2026-08-24T00:00:02+00:00"
    recovered = repo.recover_expired_jobs(now=now())
    assert recovered[0].state == InvestigationLifecycleState.QUEUED

    stale_result = worker_a._complete(claimed)
    assert stale_result.state == InvestigationLifecycleState.QUEUED
    assert repo.get_job("JOB-1", "tenant-a").state == InvestigationLifecycleState.QUEUED


def test_worker_recovery_allows_second_worker_to_complete(tmp_path):
    repo = repository(tmp_path)
    current, now = fixed_clock()
    enqueue(repo, job(created_at=current["value"], available_at=current["value"], max_attempts=2))
    worker_a = repo.claim_job("worker-a", lease_seconds=1, now=now())
    current["value"] = "2026-08-24T00:00:02+00:00"
    assert repo.recover_expired_jobs(now=now())[0].state == InvestigationLifecycleState.QUEUED

    worker_b = InvestigationWorker(
        repo,
        service_identity="worker-b",
        investigate=lambda _job: InvestigationResult(success=True, status="completed"),
        authorize_job=authorize_worker,
        heartbeat_interval_seconds=0,
        clock=now,
    )
    completed = worker_b.run_once()
    assert completed.state == InvestigationLifecycleState.COMPLETED
    assert completed.attempts == 2
    assert worker_a.service_identity == "worker-a"


def test_shutdown_stops_future_claims_and_is_a_safe_boundary(tmp_path):
    repo = repository(tmp_path)
    enqueue(repo)
    worker = InvestigationWorker(
        repo,
        service_identity="worker-a",
        investigate=lambda _job: InvestigationResult(success=True, status="completed"),
        authorize_job=authorize_worker,
        heartbeat_interval_seconds=0,
    )
    worker.request_shutdown()

    assert worker.run_once() is None
    assert repo.get_job("JOB-1", "tenant-a").state == InvestigationLifecycleState.QUEUED


def test_shutdown_during_execution_finishes_current_job_at_safe_boundary(tmp_path):
    repo = repository(tmp_path)
    enqueue(repo)
    worker = None

    def finish_current_job(job_value):
        worker.request_shutdown()
        return InvestigationResult(success=True, status="completed")

    worker = InvestigationWorker(
        repo,
        service_identity="worker-a",
        investigate=finish_current_job,
        authorize_job=authorize_worker,
        heartbeat_interval_seconds=0,
    )
    completed = worker.run_once()

    assert completed.state == InvestigationLifecycleState.COMPLETED
    assert worker.shutdown_requested is True
    assert "WORKER_SHUTDOWN" in events(repo)
    assert worker.run_once() is None


def test_lease_owned_finalization_rejects_expired_owner(tmp_path):
    repo = repository(tmp_path)
    current, now = fixed_clock()
    enqueue(repo, job(created_at=current["value"], available_at=current["value"]))
    claimed = repo.claim_job("worker-a", lease_seconds=1, now=now())
    current["value"] = "2026-08-24T00:00:02+00:00"

    with pytest.raises(JobLeaseError) as exc_info:
        repo.transition_job(
            claimed.job_id,
            claimed.tenant_id,
            InvestigationLifecycleState.COMPLETED,
            service_identity="worker-a",
            require_lease=True,
            now=now(),
        )
    assert "lease" in str(exc_info.value).lower()
