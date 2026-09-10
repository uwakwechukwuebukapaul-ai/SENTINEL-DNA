from database.connection import DatabaseConnection
from services.intelligence.investigation.investigation_result import InvestigationResult
from services.intelligence.reasoning.evidence_sufficiency import SufficiencyStatus
from services.intelligence.repository.execution_repository import ExecutionRepository
from services.intelligence.runtime.investigation_job import InvestigationJob
from services.intelligence.runtime.investigation_lifecycle import InvestigationLifecycleState
from services.intelligence.runtime.investigation_worker import InvestigationWorker


def repository(tmp_path):
    return ExecutionRepository(DatabaseConnection(tmp_path / "bounded-loop.sqlite"))


def make_job(**changes):
    values = {
        "job_id": "JOB-1", "tenant_id": "tenant-a", "case_id": "CASE-1", "investigation_id": "INV-1",
        "execution_id": "EXE-1", "trigger_id": "TRIGGER-1", "idempotency_key": "tenant-a:event-1",
        "actor_id": "actor-a", "service_identity": None, "correlation_id": "CORR-1",
    }
    values.update(changes)
    return InvestigationJob(**values)


def enqueue(repo, job):
    repo.create_job(job)
    repo.transition_job(job.job_id, job.tenant_id, InvestigationLifecycleState.QUEUED, service_identity="intake")


def insufficient_result():
    return {
        "success": True, "status": "completed", "evidence": [{"evidence_id": "E-1", "tenant_id": "tenant-a"}],
        "evidence_sufficiency": "INSUFFICIENT", "evidence_gaps": ["host timeline"],
        "recommended_follow_up": {
            "capability": "evidence_lookup", "required_evidence": ["host timeline"],
            "authorization_reference": "policy:read-only-evidence",
        },
    }


def test_insufficient_generates_exactly_one_follow_up_then_completes(tmp_path):
    repo = repository(tmp_path)
    enqueue(repo, make_job())
    calls = []

    def initial(job):
        calls.append((job.iteration, "initial"))
        return insufficient_result()

    def follow_up(job, task):
        calls.append((job.iteration, task.task_id))
        return InvestigationResult(success=True, status="completed", evidence=[{"evidence_id": "E-2", "tenant_id": "tenant-a"}], metadata={"evidence_sufficiency": "SUFFICIENT"})

    worker = InvestigationWorker(repo, service_identity="worker-a", investigate=initial, follow_up=follow_up, authorize_job=lambda _job, identity: identity == "worker-a", heartbeat_interval_seconds=0)
    queued = worker.run_once(tenant_id="tenant-a")
    assert queued.state is InvestigationLifecycleState.QUEUED
    assert queued.iteration == 1
    follow_up_task = repo.get_follow_up_task("JOB-1", "tenant-a")
    assert follow_up_task.iteration == 1
    assert follow_up_task.execution_id == repo.get_job("JOB-1", "tenant-a").execution_id == "EXE-1"
    completed = worker.run_once(tenant_id="tenant-a")
    assert completed.state is InvestigationLifecycleState.COMPLETED
    assert calls[0][0] == 0 and calls[1][0] == 1
    assert repo.get_sufficiency_evaluation("JOB-1", "tenant-a", 0).status is SufficiencyStatus.INSUFFICIENT
    assert repo.get_sufficiency_evaluation("JOB-1", "tenant-a", 1).status is SufficiencyStatus.SUFFICIENT
    assert len(repo.get_snapshot(repo.get_job("JOB-1", "tenant-a").snapshot_id, "tenant-a").evidence) == 1
    events = [item["event_type"] for item in repo.audit_service.list_for_tenant("tenant-a", limit=100)]
    assert {"FOLLOW_UP_TASK_CREATED", "FOLLOW_UP_REQUEUED", "EVIDENCE_SUFFICIENCY_EVALUATED", "AUTONOMOUS_STOP"}.issubset(events)


def test_sufficient_stops_without_follow_up(tmp_path):
    repo = repository(tmp_path)
    enqueue(repo, make_job())
    worker = InvestigationWorker(
        repo, service_identity="worker-a",
        investigate=lambda _job: InvestigationResult(success=True, status="completed", evidence=[{"evidence_id": "E-1"}]),
        authorize_job=lambda _job, identity: identity == "worker-a",
        heartbeat_interval_seconds=0,
    )
    completed = worker.run_once()
    assert completed.state is InvestigationLifecycleState.COMPLETED
    assert repo.get_follow_up_task("JOB-1", "tenant-a") is None


def test_unknown_escalates_and_blocked_stops_fail_closed(tmp_path):
    repo = repository(tmp_path)
    enqueue(repo, make_job())
    unknown = InvestigationWorker(repo, service_identity="worker-a", investigate=lambda _job: {"success": True, "status": "completed", "evidence_sufficiency": "UNKNOWN"}, authorize_job=lambda _job, identity: identity == "worker-a", heartbeat_interval_seconds=0)
    assert unknown.run_once().state is InvestigationLifecycleState.ESCALATED

    blocked_path = tmp_path / "blocked"
    blocked_path.mkdir()
    repo2 = repository(blocked_path)
    enqueue(repo2, make_job())
    blocked = InvestigationWorker(repo2, service_identity="worker-a", investigate=lambda _job: {"success": True, "status": "completed", "evidence_sufficiency": "INSUFFICIENT", "evidence_gaps": ["gap"]}, authorize_job=lambda _job, identity: identity == "worker-a", heartbeat_interval_seconds=0)
    assert blocked.run_once().state is InvestigationLifecycleState.BLOCKED


def test_no_second_autonomous_iteration_and_cancellation_before_follow_up(tmp_path):
    repo = repository(tmp_path)
    enqueue(repo, make_job())
    worker = InvestigationWorker(repo, service_identity="worker-a", investigate=lambda _job: insufficient_result(), follow_up=lambda _job, _task: insufficient_result(), authorize_job=lambda _job, identity: identity == "worker-a", heartbeat_interval_seconds=0)
    assert worker.run_once().iteration == 1
    assert worker.run_once().state is InvestigationLifecycleState.ESCALATED
    assert worker.run_once() is None

    cancelled_path = tmp_path / "cancelled"
    cancelled_path.mkdir()
    repo2 = repository(cancelled_path)
    enqueue(repo2, make_job())
    def cancel(job):
        repo2.request_cancellation(job.job_id, job.tenant_id, actor_id="operator")
        return insufficient_result()
    cancelled = InvestigationWorker(repo2, service_identity="worker-a", investigate=cancel, authorize_job=lambda _job, identity: identity == "worker-a", heartbeat_interval_seconds=0).run_once()
    assert cancelled.state is InvestigationLifecycleState.CANCELLED
    assert repo2.get_follow_up_task("JOB-1", "tenant-a") is None
