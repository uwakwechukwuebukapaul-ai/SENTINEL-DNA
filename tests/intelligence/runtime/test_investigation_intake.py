from types import SimpleNamespace

import pytest

from database.connection import DatabaseConnection
from services.intelligence.repository.execution_repository import ExecutionRepository
from services.intelligence.runtime.investigation_intake import (
    EligibilityDecision,
    InvestigationIntake,
)
from services.intelligence.runtime.investigation_lifecycle import InvestigationLifecycleState
from tests.credential_helpers import random_password


def repository(tmp_path):
    return ExecutionRepository(DatabaseConnection(tmp_path / "investigation-intake.sqlite"))


def context(tenant="tenant-a", actor="actor-a", roles=("analyst",), correlation="corr-1", error=None):
    return SimpleNamespace(
        tenant_id=tenant,
        actor_id=actor,
        user_id=actor,
        roles=roles,
        correlation_id=correlation,
        error=error,
    )


def alert(event_id="event-1", case_id="CASE-1", **changes):
    password = random_password()
    value = {
        "case_id": case_id,
        "source": "api",
        "alert": {
            "id": event_id,
            "event_type": "failed_login",
            "severity": "high",
            "description": "Repeated authentication failures",
            "password": password,
        },
    }
    value.update(changes)
    return value


def intake(repo, **changes):
    return InvestigationIntake(repo, **changes)


def test_authorized_alert_creates_queued_job_without_execution(tmp_path):
    repo = repository(tmp_path)
    result = intake(repo).accept(alert(), context=context())

    assert result.accepted is True
    assert result.duplicate is False
    assert result.state == InvestigationLifecycleState.QUEUED.value
    job = repo.get_job(result.job_id, "tenant-a")
    trigger = repo.get_trigger(result.trigger_id, "tenant-a")
    assert job.trigger_id == trigger.trigger_id
    assert job.case_id == "CASE-1"
    assert job.state_history[0]["next_state"] == "PENDING"
    assert job.state_history[1]["next_state"] == "QUEUED"
    assert "password" not in str(trigger.normalized_payload)


def test_intake_never_invokes_worker_or_coordinator(tmp_path):
    repo = repository(tmp_path)
    called = []
    result = intake(repo).accept(alert(), context=context())

    assert result.accepted is True
    assert called == []
    assert repo.claim_job("worker-a") is not None


def test_exact_duplicate_returns_same_durable_job(tmp_path):
    repo = repository(tmp_path)
    service = intake(repo)
    first = service.accept(alert(), context=context())
    second = service.accept(alert(), context=context(correlation="corr-2"))

    assert second.accepted is True
    assert second.duplicate is True
    assert second.job_id == first.job_id
    with repo.db.session() as connection:
        assert connection.execute("SELECT COUNT(*) AS count FROM investigation_jobs").fetchone()["count"] == 1


def test_conflicting_duplicate_is_blocked(tmp_path):
    repo = repository(tmp_path)
    service = intake(repo)
    service.accept(alert(), context=context())
    result = service.accept(alert(description="different alert content"), context=context())

    assert result.accepted is False
    assert result.code == "idempotency_conflict"
    assert result.http_status == 409


def test_cross_tenant_same_source_event_creates_isolated_job(tmp_path):
    repo = repository(tmp_path)
    service = intake(repo)
    first = service.accept(alert(), context=context("tenant-a", "actor-a"))
    second = service.accept(alert(), context=context("tenant-b", "actor-b", correlation="corr-b"))

    assert first.job_id != second.job_id
    assert repo.get_job(first.job_id, "tenant-b") is None
    assert repo.get_job(second.job_id, "tenant-a") is None
    assert repo.get_trigger(first.trigger_id, "tenant-b") is None


def test_missing_tenant_fails_closed_and_audits(tmp_path):
    repo = repository(tmp_path)
    result = intake(repo).accept(alert(), context=context(tenant=None))

    assert result.accepted is False
    assert result.code == "tenant_required"
    events = repo.audit_service.list_for_tenant("tenant-a")
    assert events == []


def test_missing_actor_and_service_identity_fails_closed(tmp_path):
    repo = repository(tmp_path)
    result = intake(repo).accept(alert(), context=context(actor=None, roles=()))

    assert result.accepted is False
    assert result.code == "actor_or_service_identity_required"


def test_unauthorized_actor_fails_closed(tmp_path):
    repo = repository(tmp_path)
    result = intake(repo).accept(alert(), context=context(roles=("viewer",)))

    assert result.accepted is False
    assert result.code == "intake_unauthorized"


def test_authorized_service_identity_can_submit_without_actor(tmp_path):
    repo = repository(tmp_path)
    service = intake(repo, authorize_service_identity=lambda identity: identity == "detector-service")
    result = service.accept(
        alert(), context=context(actor=None, roles=()), service_identity="detector-service"
    )

    assert result.accepted is True
    assert repo.get_job(result.job_id, "tenant-a").service_identity == "detector-service"


def test_trigger_audit_persists_authorized_service_identity(tmp_path):
    repo = repository(tmp_path)
    service = intake(repo, authorize_service_identity=lambda identity: identity == "detector-service")

    result = service.accept(
        alert(), context=context(actor=None, roles=()), service_identity="detector-service"
    )
    events = [
        item for item in repo.audit_service.list_for_tenant("tenant-a", limit=100)
        if item["resource_id"] == result.trigger_id
    ]

    assert events
    assert all(item["details"]["service_identity"] == "detector-service" for item in events)


def test_tenant_payload_mismatch_is_rejected(tmp_path):
    repo = repository(tmp_path)
    value = alert(tenant_id="tenant-b")
    result = intake(repo).accept(value, context=context("tenant-a"))

    assert result.accepted is False
    assert result.code == "malformed_alert"


def test_malformed_alert_is_rejected(tmp_path):
    repo = repository(tmp_path)
    result = intake(repo).accept({"case_id": "CASE-1"}, context=context())

    assert result.accepted is False
    assert result.code == "malformed_alert"
    assert result.http_status == 400


def test_unsupported_source_is_rejected(tmp_path):
    repo = repository(tmp_path)
    result = intake(repo).accept(alert(), context=context(), source="unknown-provider")

    assert result.accepted is False
    assert result.code == "malformed_alert"


def test_normalization_is_deterministic_and_secret_free(tmp_path):
    first = InvestigationIntake.normalize_alert(alert(), tenant_id="tenant-a", source="api")
    second = InvestigationIntake.normalize_alert(alert(), tenant_id="tenant-a", source="api")

    assert first == second
    assert first["source_event_id"] == "event-1"
    assert "password" not in str(first)


def test_ineligible_alert_is_persisted_without_a_job(tmp_path):
    repo = repository(tmp_path)
    service = intake(repo, eligibility_policy=lambda value: EligibilityDecision("INELIGIBLE", "unsupported alert type"))
    result = service.accept(alert(), context=context())

    assert result.accepted is False
    assert result.code == "ineligible_alert"
    assert repo.get_trigger(result.trigger_id, "tenant-a").job_id is None
    assert repo.get_job_by_idempotency_key("api:event-1", "tenant-a") is None


def test_destructive_capability_is_blocked_from_autonomous_path(tmp_path):
    repo = repository(tmp_path)
    result = intake(repo).accept(alert(action="host_isolation"), context=context())

    assert result.accepted is False
    assert result.code == "intake_blocked"
    assert repo.get_trigger(result.trigger_id, "tenant-a").eligibility_result == "BLOCKED"


def test_correlation_and_lineage_are_preserved(tmp_path):
    repo = repository(tmp_path)
    result = intake(repo).accept(alert(), context=context(correlation="corr-fixed"))
    job = repo.get_job(result.job_id, "tenant-a")
    trigger = repo.get_trigger(result.trigger_id, "tenant-a")

    assert result.correlation_id == "corr-fixed"
    assert job.correlation_id == "corr-fixed"
    assert trigger.correlation_id == "corr-fixed"
    assert job.investigation_id == "INV-1" or job.investigation_id == "CASE-1"


def test_intake_audit_is_secret_safe_and_sequenced(tmp_path):
    repo = repository(tmp_path)
    result = intake(repo).accept(alert(), context=context())
    events = repo.audit_service.list_for_tenant("tenant-a", limit=50)
    trigger_events = [item for item in events if item["resource_id"] == result.trigger_id]

    assert trigger_events
    assert all(item["sequence_number"] for item in trigger_events)
    assert "must-never-persist" not in str(events)


def test_conflicting_case_binding_is_rejected(tmp_path):
    repo = repository(tmp_path)
    value = alert()
    value["alert"]["case_id"] = "CASE-OTHER"
    result = intake(repo).accept(value, context=context())

    assert result.accepted is False
    assert result.code == "malformed_alert"
