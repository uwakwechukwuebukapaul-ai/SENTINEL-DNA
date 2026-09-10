from datetime import datetime, timezone

from app.intelligence.gateway import IOCType, IntelligenceObservation, ProviderIdentity, ProviderResult, ThreatIntelligenceGateway
from database.connection import DatabaseConnection
from services.intelligence.repository.execution_repository import ExecutionRepository
from services.intelligence.repository.provider_observation_repository import ProviderObservationRepository
from services.intelligence.runtime.investigation_job import InvestigationJob
from services.intelligence.runtime.investigation_runtime_policy import InvestigationRuntimePolicy
from services.intelligence.runtime.investigation_worker import InvestigationWorker
from services.intelligence.runtime.provider_follow_up_capability import ProviderObservationFollowUpExecutor
from services.intelligence.runtime.investigation_lifecycle import InvestigationLifecycleState
from services.tenant.authorization import TenantAuthorizationService


class Context:
    tenant_id = "tenant-a"
    actor_id = "actor-a"
    role = "analyst"
    correlation_id = "CORR-1"


class Provider:
    identity = ProviderIdentity("provider-a", "test-1")

    def __init__(self):
        self.calls = 0

    def capabilities(self):
        return frozenset({IOCType.DOMAIN})

    def lookup(self, request):
        self.calls += 1
        return ProviderResult(
            self.identity,
            IntelligenceObservation(
                request.ioc, self.identity, datetime(2026, 8, 24, tzinfo=timezone.utc),
                provider_record="record-1", reputation="malicious", confidence=0.9,
            ),
        )


def make_job():
    return InvestigationJob(
        job_id="JOB-1", tenant_id="tenant-a", case_id="CASE-1", investigation_id="INV-1",
        execution_id="EXE-1", trigger_id="TRIGGER-1", idempotency_key="tenant-a:event-1",
        actor_id="actor-a", service_identity=None, correlation_id="CORR-1",
    )


def test_worker_executes_one_authorized_provider_follow_up_and_re_evaluates(tmp_path):
    db = DatabaseConnection(tmp_path / "provider-worker.sqlite")
    execution = ExecutionRepository(db)
    observation_repository = ProviderObservationRepository(
        db, authorization=TenantAuthorizationService(),
    )
    provider = Provider()
    gateway = ThreatIntelligenceGateway(
        [provider], lambda tenant, actor: (tenant, actor) == ("tenant-a", "actor-a"),
        provider_policy=lambda *_: True,
    )
    executor = ProviderObservationFollowUpExecutor(
        gateway, observation_repository, execution,
        authorization_context_factory=lambda _job: Context(),
        provider_authorizer=lambda *_: True,
        runtime_policy=InvestigationRuntimePolicy(),
        approved_provider="provider-a", release_gate=lambda *_: True,
        service_authorizer=lambda *_: True,
        service_identity="provider-follow-up",
    )
    job = make_job()
    execution.create_job(job)
    execution.transition_job(job.job_id, job.tenant_id, InvestigationLifecycleState.QUEUED, service_identity="intake")

    def initial(_job):
        return {
            "success": True,
            "status": "completed",
            "evidence": [{"evidence_id": "E-INITIAL", "tenant_id": "tenant-a"}],
            "iocs": [{"type": "domain", "value": "example.test"}],
            "evidence_sufficiency": "INSUFFICIENT",
            "evidence_gaps": ["provider reputation"],
            "recommended_follow_up": {
                "capability": "threat_intelligence_lookup",
                "required_evidence": ["provider reputation"],
                "authorization_reference": "policy:read-only-threat-intelligence",
                "provider_request": {"ioc_type": "domain", "ioc_value": "example.test"},
            },
        }

    worker = InvestigationWorker(
        execution, service_identity="worker-a", investigate=initial,
        provider_follow_up_executor=executor,
        authorize_job=lambda _job, identity: identity == "worker-a",
        heartbeat_interval_seconds=0,
    )
    queued = worker.run_once(tenant_id="tenant-a")
    assert queued.state is InvestigationLifecycleState.QUEUED
    completed = worker.run_once(tenant_id="tenant-a")

    assert completed.state is InvestigationLifecycleState.COMPLETED
    assert provider.calls == 1
    assert execution.provider_health_for_execution("EXE-1", "tenant-a")
    snapshot = execution.get_snapshot(completed.snapshot_id, "tenant-a")
    assert snapshot.provider_observation_references
    assert execution.get_follow_up_task("JOB-1", "tenant-a").iteration == 1
    events = {
        item["event_type"]
        for item in execution.audit_service.list_for_tenant("tenant-a", limit=100)
    }
    assert {"PROVIDER_REQUEST_RESERVED", "PROVIDER_INVOCATION_STARTED", "PROVIDER_EVIDENCE_PROJECTED"}.issubset(events)
