from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from app.intelligence.gateway import (
    IOCType,
    IntelligenceObservation,
    ProviderError,
    ProviderErrorCode,
    ProviderIdentity,
    ProviderResult,
    ThreatIntelligenceGateway,
)
from database.connection import DatabaseConnection
from services.intelligence.repository.execution_repository import ExecutionRepository
from services.intelligence.repository.provider_observation_repository import ProviderObservationRepository
from services.intelligence.runtime.investigation_job import InvestigationJob
from services.intelligence.runtime.investigation_runtime_policy import InvestigationRuntimePolicy
from services.intelligence.runtime.provider_follow_up_capability import (
    CAPABILITY_THREAT_INTELLIGENCE_LOOKUP,
    ProviderFollowUpError,
    ProviderObservationFollowUpExecutor,
    ReadOnlyFollowUpCapabilityRegistry,
)
from services.intelligence.runtime.task import Task
from services.tenant.authorization import TenantAuthorizationService


@dataclass(frozen=True)
class Context:
    tenant_id: str
    actor_id: str
    role: str = "analyst"
    correlation_id: str = "CORR-1"


class Provider:
    def __init__(self, name="provider-a", error=None, after_call=None):
        self.identity = ProviderIdentity(name, "test-1")
        self.error = error
        self.after_call = after_call
        self.calls = 0

    def capabilities(self):
        return frozenset({IOCType.DOMAIN})

    def lookup(self, request):
        self.calls += 1
        if self.after_call is not None:
            self.after_call()
        if self.error is not None:
            return ProviderResult(self.identity, error=self.error)
        return ProviderResult(
            self.identity,
            IntelligenceObservation(
                request.ioc,
                self.identity,
                datetime(2026, 8, 24, tzinfo=timezone.utc),
                provider_record="record-1",
                reputation="malicious",
                confidence=0.8,
            ),
        )


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


def follow_up_task(value="example.test", **changes):
    values = {
        "task_id": "FU-1",
        "capability": CAPABILITY_THREAT_INTELLIGENCE_LOOKUP,
        "payload": {"provider_request": {"ioc_type": "domain", "ioc_value": value}},
        "parent_task_id": "INITIAL-JOB-1",
        "job_id": "JOB-1",
        "tenant_id": "tenant-a",
        "case_id": "CASE-1",
        "investigation_id": "INV-1",
        "iteration": 1,
        "authorization_reference": "AUTH-1",
        "objective": "Collect recorded evidence gap",
        "required_evidence": ["provider reputation"],
        "deadline_at": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    values.update(changes)
    return Task(**values)


def setup_executor(tmp_path, *, provider=None, policy=None, provider_authorizer=None, context=None, service_identity="provider-follow-up"):
    db = DatabaseConnection(tmp_path / "provider-follow-up.sqlite")
    execution = ExecutionRepository(db)
    observations = ProviderObservationRepository(db, authorization=TenantAuthorizationService())
    provider = provider or Provider()
    gateway = ThreatIntelligenceGateway(
        [provider], lambda tenant, actor: tenant == "tenant-a" and actor == "actor-a",
        provider_policy=lambda *_: True,
    )
    context = context or Context("tenant-a", "actor-a")
    executor = ProviderObservationFollowUpExecutor(
        gateway,
        observations,
        execution,
        authorization_context_factory=lambda _job: context,
        provider_authorizer=provider_authorizer or (lambda *_: True),
        runtime_policy=policy or InvestigationRuntimePolicy(),
        approved_provider=provider.identity.name,
        release_gate=lambda *_: True,
        service_authorizer=lambda *_: True,
        service_identity=service_identity,
    )
    execution.create_job(job())
    return execution, observations, provider, executor


def test_allowlisted_lookup_persists_observation_and_projects_evidence(tmp_path):
    execution, observations, provider, executor = setup_executor(tmp_path)

    result = executor.execute_follow_up(job(), follow_up_task())

    assert result["success"] is True
    assert result["evidence"]
    assert result["provider_observation_references"]
    assert provider.calls == 1
    stored = observations.get_for_tenant(
        result["provider_observation_references"][0], tenant_id="tenant-a", case_id="CASE-1",
        correlation_id="CORR-1", actor_id="actor-a", authorization_context=Context("tenant-a", "actor-a")
    )
    assert stored.provenance["provider"] == "provider-a"
    assert stored.tenant_id == "tenant-a"
    assert "PROVIDER_OBSERVATION_PERSISTED" in [
        item["event_type"] for item in execution.audit_service.list_for_tenant("tenant-a", limit=100)
    ]


def test_duplicate_request_reuses_observation_without_provider_refresh(tmp_path):
    _execution, _observations, provider, executor = setup_executor(tmp_path)
    task = follow_up_task()

    first = executor.execute_follow_up(job(), task)
    second = executor.execute_follow_up(job(), task)

    assert provider.calls == 1
    assert second["metadata"]["replay_reused"] is True
    assert second["provider_observation_references"] == first["provider_observation_references"]


def test_budget_exhaustion_denies_provider_before_invocation(tmp_path):
    execution, _observations, provider, executor = setup_executor(
        tmp_path, policy=InvestigationRuntimePolicy(provider_call_budget=0)
    )

    with pytest.raises(ProviderFollowUpError) as error:
        executor.execute_follow_up(job(), follow_up_task())

    assert error.value.code == "budget_exhausted"
    assert provider.calls == 0
    assert execution.get_provider_request("PVR-", "tenant-a") is None


def test_provider_authorization_denial_is_fail_closed(tmp_path):
    _execution, _observations, provider, executor = setup_executor(
        tmp_path, provider_authorizer=lambda *_: False
    )

    with pytest.raises(ProviderFollowUpError) as error:
        executor.execute_follow_up(job(), follow_up_task())

    assert error.value.code == "provider_unauthorized"
    assert provider.calls == 0


def test_missing_authorization_context_is_rejected(tmp_path):
    _execution, _observations, provider, executor = setup_executor(
        tmp_path, context=None,
    )
    executor.authorization_context_factory = lambda _job: None

    with pytest.raises(ProviderFollowUpError) as error:
        executor.execute_follow_up(job(), follow_up_task())

    assert error.value.code == "unauthorized"
    assert provider.calls == 0


def test_case_and_investigation_lineage_mismatch_is_rejected(tmp_path):
    _execution, _observations, provider, executor = setup_executor(tmp_path)

    with pytest.raises(ProviderFollowUpError) as case_error:
        executor.execute_follow_up(job(), follow_up_task(case_id="CASE-OTHER"))
    with pytest.raises(ProviderFollowUpError) as investigation_error:
        executor.execute_follow_up(job(), follow_up_task(investigation_id="INV-OTHER"))

    assert case_error.value.code == "tenant_mismatch"
    assert investigation_error.value.code == "tenant_mismatch"
    assert provider.calls == 0


def test_tenant_lineage_and_unknown_capability_are_rejected(tmp_path):
    _execution, _observations, provider, executor = setup_executor(tmp_path)

    with pytest.raises(ProviderFollowUpError, match="lineage"):
        executor.execute_follow_up(job(tenant_id="tenant-b"), follow_up_task())
    with pytest.raises(ProviderFollowUpError) as error:
        executor.execute_follow_up(job(), follow_up_task(capability="unknown_capability"))
    assert error.value.code == "capability_blocked"
    assert provider.calls == 0


def test_registry_rejects_unallowlisted_and_accepts_explicit_capability():
    registry = ReadOnlyFollowUpCapabilityRegistry()
    with pytest.raises(ValueError):
        registry.register("disable_account", object())
    class Handler:
        def execute_follow_up(self, *_):
            return None

    handler = Handler()
    registry.register(CAPABILITY_THREAT_INTELLIGENCE_LOOKUP, handler)
    assert registry.resolve(CAPABILITY_THREAT_INTELLIGENCE_LOOKUP) is handler


def test_provider_failure_is_explicit_without_fabricated_evidence(tmp_path):
    provider = Provider(error=ProviderError(ProviderErrorCode.TIMEOUT, "timed out", True))
    _execution, _observations, _provider, executor = setup_executor(tmp_path, provider=provider)

    result = executor.execute_follow_up(job(), follow_up_task())

    assert result["success"] is True
    assert result["evidence"] == []
    assert result["metadata"]["error_code"] == "provider_timeout"


def test_no_provider_is_escalated_without_invocation(tmp_path):
    db = DatabaseConnection(tmp_path / "no-provider.sqlite")
    execution = ExecutionRepository(db)
    observations = ProviderObservationRepository(db, authorization=TenantAuthorizationService())
    gateway = ThreatIntelligenceGateway([], lambda *_: True)
    executor = ProviderObservationFollowUpExecutor(
        gateway, observations, execution,
        authorization_context_factory=lambda _job: Context("tenant-a", "actor-a"),
        provider_authorizer=lambda *_: True, runtime_policy=InvestigationRuntimePolicy(),
        approved_provider="provider-a", release_gate=lambda *_: True,
        service_authorizer=lambda *_: True,
        service_identity="provider-follow-up",
    )
    execution.create_job(job())

    with pytest.raises(ProviderFollowUpError) as error:
        executor.execute_follow_up(job(), follow_up_task())

    assert error.value.code == "provider_release_gate_denied"
    assert error.value.terminal_state == "BLOCKED"


def test_cancellation_after_provider_response_is_persisted_and_stops_follow_up(tmp_path):
    execution, _observations, provider, executor = setup_executor(tmp_path)
    provider.after_call = lambda: execution.request_cancellation(
        "JOB-1", "tenant-a", actor_id="operator", correlation_id="CORR-1",
    )

    with pytest.raises(ProviderFollowUpError) as error:
        executor.execute_follow_up(job(), follow_up_task())

    assert error.value.code == "cancellation"
    assert provider.calls == 1
    request_id = next(
        item["details"]["request_id"]
        for item in execution.audit_service.list_for_tenant("tenant-a", limit=100)
        if item["event_type"] == "PROVIDER_REQUEST_RESERVED"
    )
    assert execution.get_provider_request(request_id, "tenant-a")["status"] == "FAILED"


def test_replay_integrity_failure_does_not_refresh_provider(tmp_path):
    execution, observations, provider, executor = setup_executor(tmp_path)
    first = executor.execute_follow_up(job(), follow_up_task())
    observation_id = first["provider_observation_references"][0]
    with observations.db.session() as connection:
        connection.execute(
            "UPDATE provider_observations SET integrity_digest=? WHERE observation_id=?",
            ("tampered", observation_id),
        )

    with pytest.raises(ProviderFollowUpError) as error:
        executor.execute_follow_up(job(), follow_up_task())

    assert error.value.code == "replay_integrity_failure"
    assert provider.calls == 1


def test_cancelled_job_does_not_invoke_provider(tmp_path):
    _execution, _observations, provider, executor = setup_executor(tmp_path)

    with pytest.raises(ProviderFollowUpError) as error:
        executor.execute_follow_up(job(cancel_requested=True), follow_up_task())

    assert error.value.code == "cancellation"
    assert provider.calls == 0


def test_task_deadline_is_enforced(tmp_path):
    _execution, _observations, provider, executor = setup_executor(tmp_path)
    task = follow_up_task(deadline_at=datetime.now(timezone.utc) - timedelta(seconds=1))

    with pytest.raises(ProviderFollowUpError) as error:
        executor.execute_follow_up(job(), task)

    assert error.value.code == "task_timeout"
    assert provider.calls == 0
