from datetime import datetime, timedelta, timezone

import pytest

from app.intelligence.gateway import IntelligenceObservation, ProviderResult
from services.intelligence.runtime.investigation_runtime_policy import InvestigationRuntimePolicy
from services.intelligence.runtime.provider_follow_up_capability import ProviderFollowUpError, ProviderObservationFollowUpExecutor

from tests.intelligence.provider.test_provider_follow_up_capability import (
    Context,
    Provider,
    follow_up_task,
    job,
    setup_executor,
)


def request_id(execution):
    return next(
        item["details"]["request_id"]
        for item in execution.audit_service.list_for_tenant("tenant-a", limit=100)
        if item["event_type"] == "PROVIDER_REQUEST_RESERVED"
    )


def test_release_gate_denies_without_explicit_approval(tmp_path):
    _execution, _observations, provider, executor = setup_executor(tmp_path)
    executor.release_gate = lambda *_: False

    with pytest.raises(ProviderFollowUpError) as error:
        executor.execute_follow_up(job(), follow_up_task())

    assert error.value.code == "provider_release_gate_denied"
    assert provider.calls == 0


def test_service_authorization_denies_fail_closed(tmp_path):
    _execution, _observations, provider, executor = setup_executor(tmp_path)
    executor.service_authorizer = lambda *_: False

    with pytest.raises(ProviderFollowUpError) as error:
        executor.execute_follow_up(job(), follow_up_task())

    assert error.value.code == "service_unauthorized"
    assert provider.calls == 0


def test_missing_service_identity_is_rejected_at_executor_boundary(tmp_path):
    execution, observations, _provider, _executor = setup_executor(tmp_path)
    from app.intelligence.gateway import ThreatIntelligenceGateway

    with pytest.raises(ValueError, match="service identity"):
        ProviderObservationFollowUpExecutor(
            ThreatIntelligenceGateway([], lambda *_: True), observations, execution,
            authorization_context_factory=lambda _job: Context("tenant-a", "actor-a"),
            provider_authorizer=lambda *_: True,
            runtime_policy=InvestigationRuntimePolicy(),
            approved_provider="provider-a", release_gate=lambda *_: True,
            service_authorizer=lambda *_: True, service_identity=None,
        )


def test_quota_exhaustion_does_not_invoke_provider_or_create_ledger_cost(tmp_path):
    execution, _observations, provider, executor = setup_executor(
        tmp_path, policy=InvestigationRuntimePolicy(tenant_provider_quota=0.0),
    )

    with pytest.raises(ProviderFollowUpError) as error:
        executor.execute_follow_up(job(), follow_up_task())

    assert error.value.code == "quota_exhausted"
    assert provider.calls == 0
    assert execution.provider_budget_for_tenant("tenant-a")["consumed_cost"] == 0.0
    assert execution.get_provider_request(request_id(execution), "tenant-a")["status"] == "FAILED"


def test_successful_reservation_remains_accounted_after_provider_failure(tmp_path):
    from app.intelligence.gateway import ProviderError, ProviderErrorCode

    execution, _observations, provider, executor = setup_executor(
        tmp_path, provider=Provider(error=ProviderError(ProviderErrorCode.TIMEOUT, "timed out", True)),
    )

    result = executor.execute_follow_up(job(), follow_up_task())
    ledger = execution.provider_budget_for_tenant("tenant-a")

    assert result["metadata"]["error_code"] == "provider_timeout"
    assert provider.calls == 1
    assert ledger["reserved_cost"] == 1.0
    assert ledger["consumed_cost"] == 1.0


def test_tenant_quota_is_shared_across_distinct_provider_requests(tmp_path):
    execution, _observations, provider, executor = setup_executor(tmp_path)
    second_job = job(
        job_id="JOB-2", execution_id="EXE-2", investigation_id="INV-2",
        trigger_id="TRIGGER-2", idempotency_key="tenant-a:event-2",
        correlation_id="CORR-1",
    )
    execution.create_job(second_job)

    executor.execute_follow_up(job(), follow_up_task())

    with pytest.raises(ProviderFollowUpError) as error:
        executor.execute_follow_up(second_job, follow_up_task(task_id="FU-2", job_id="JOB-2", investigation_id="INV-2"))

    assert error.value.code == "quota_exhausted"
    assert provider.calls == 1
    assert execution.provider_budget_for_tenant("tenant-a")["consumed_cost"] == 1.0


def test_duplicate_reservation_and_provider_request_are_idempotent(tmp_path):
    execution, _observations, provider, executor = setup_executor(tmp_path)
    task = follow_up_task()

    first = executor.execute_follow_up(job(), task)
    second = executor.execute_follow_up(job(), task)
    usage = execution.provider_budget_for_tenant("tenant-a")

    assert first["provider_observation_references"] == second["provider_observation_references"]
    assert second["metadata"]["replay_reused"] is True
    assert provider.calls == 1
    assert usage["consumed_cost"] == 1.0


def test_observation_link_preserves_request_and_scope_lineage(tmp_path):
    execution, _observations, _provider, executor = setup_executor(tmp_path)
    result = executor.execute_follow_up(job(), follow_up_task())
    linked = execution.verify_provider_observation_links(
        request_id=request_id(execution), tenant_id="tenant-a", job_id="JOB-1",
        investigation_id="INV-1", execution_id="EXE-1", task_id="FU-1",
        observation_ids=result["provider_observation_references"],
    )

    assert linked[0]["capability"] == "threat_intelligence_lookup"
    assert linked[0]["authorization_reference"] == "AUTH-1"
    assert linked[0]["iteration"] == 1


def test_provider_quota_request_and_observation_audits_preserve_service_identity(tmp_path):
    execution, _observations, _provider, executor = setup_executor(
        tmp_path, service_identity="certified-provider-service",
    )

    executor.execute_follow_up(job(), follow_up_task())
    events = execution.audit_service.list_for_tenant("tenant-a", limit=100)
    required = {
        "PROVIDER_REQUEST_RESERVED",
        "PROVIDER_QUOTA_RESERVED",
        "PROVIDER_OBSERVATION_LINKED",
    }
    observed = {item["event_type"]: item for item in events if item["event_type"] in required}

    assert set(observed) == required
    assert all(item["details"]["service_identity"] == "certified-provider-service" for item in observed.values())


def test_replay_does_not_consume_quota_again(tmp_path):
    execution, _observations, _provider, executor = setup_executor(tmp_path)
    executor.execute_follow_up(job(), follow_up_task())
    before = execution.provider_budget_for_tenant("tenant-a")
    executor.execute_follow_up(job(), follow_up_task())
    after = execution.provider_budget_for_tenant("tenant-a")

    assert before == after


def test_replay_scope_mismatch_fails_before_provider_refresh(tmp_path):
    _execution, _observations, provider, executor = setup_executor(tmp_path)

    with pytest.raises(ProviderFollowUpError) as error:
        executor.execute_follow_up(job(case_id="CASE-OTHER"), follow_up_task())

    assert error.value.code == "tenant_mismatch"
    assert provider.calls == 0


def test_stale_observation_is_persisted_as_stale_evidence(tmp_path):
    class StaleProvider(Provider):
        def lookup(self, request):
            self.calls += 1
            return ProviderResult(
                self.identity,
                IntelligenceObservation(
                    request.ioc, self.identity, datetime.now(timezone.utc),
                    provider_record="stale-record", expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
                    reputation="malicious", confidence=0.5,
                ),
            )

    _execution, _observations, _provider, executor = setup_executor(tmp_path, provider=StaleProvider())
    result = executor.execute_follow_up(job(), follow_up_task())

    assert result["evidence"][0]["status"] == "stale"


def test_provider_health_contains_request_lineage_and_failure_outcome(tmp_path):
    from app.intelligence.gateway import ProviderError, ProviderErrorCode

    execution, _observations, _provider, executor = setup_executor(
        tmp_path, provider=Provider(error=ProviderError(ProviderErrorCode.TIMEOUT, "timed out", True)),
    )
    executor.execute_follow_up(job(), follow_up_task())
    health = execution.provider_health_for_execution("EXE-1", "tenant-a")

    assert health[0]["request_id"] == request_id(execution)
    assert health[0]["job_id"] == "JOB-1"
    assert health[0]["task_id"] == "FU-1"
    assert health[0]["outcome"] == "provider_timeout"


def test_audit_events_are_tenant_scoped_and_sequence_ordered(tmp_path):
    execution, _observations, _provider, executor = setup_executor(tmp_path)
    executor.execute_follow_up(job(), follow_up_task())
    events = execution.audit_service.list_for_tenant("tenant-a", limit=100)
    scoped = [item for item in events if item.get("job_id") == "JOB-1" or item.get("resource_id") == "JOB-1"]
    sequences = [item["sequence_number"] for item in scoped if item.get("sequence_number") is not None]

    assert "PROVIDER_QUOTA_RESERVED" in {item["event_type"] for item in events}
    assert "PROVIDER_OBSERVATION_LINKED" in {item["event_type"] for item in events}
    assert sequences == sorted(sequences, reverse=True)
    assert set(sequences) == set(range(1, max(sequences) + 1))


def test_persisted_metadata_does_not_include_secret_markers(tmp_path):
    execution, _observations, _provider, executor = setup_executor(tmp_path)
    result = executor.execute_follow_up(job(), follow_up_task())
    events = execution.audit_service.list_for_tenant("tenant-a", limit=100)

    serialized = repr(result) + repr(events)
    assert "api_key" not in serialized.lower()
    assert "private_key" not in serialized.lower()
    assert "access_token" not in serialized.lower()
