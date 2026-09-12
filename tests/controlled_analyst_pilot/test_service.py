from datetime import datetime, timedelta, timezone
import secrets

import pytest

from database.connection import DatabaseConnection
from database.migration_runner import CONTROLLED_ANALYST_PILOT_MIGRATIONS, MigrationRunner
from services.audit.service import AuditService
from services.auth.auth_service import AuthService
from services.identity.canonical_authority import CanonicalAuthorityService
from services.pilot_management.authorization import PilotAuthorizationService
from services.pilot_management.provisioning import PilotAccountProvisioningService
from services.controlled_analyst_pilot.service import (
    ControlledAnalystPilotError,
    ControlledAnalystPilotService,
)


class Clock:
    def __init__(self):
        self.value = datetime.now(timezone.utc)

    def __call__(self):
        return self.value


@pytest.fixture
def pilot(tmp_path):
    db = DatabaseConnection(tmp_path / "controlled-pilot.sqlite")
    assert MigrationRunner(db, migrations=CONTROLLED_ANALYST_PILOT_MIGRATIONS).run() == tuple(range(1, 11))
    auth = AuthService(db)
    authority = CanonicalAuthorityService(db, auth=auth)
    audit = AuditService(db)
    manager_tenant = authority.tenants.create("Manager tenant", "manager-tenant")
    authority.identities.create("manager@example.test", "Manager", "manager-actor")
    authority.memberships.add(manager_tenant.tenant_id, "manager-actor", "admin")
    manager_password = secrets.token_urlsafe(24)
    auth.register("manager", "manager@example.test", manager_password, "admin", tenant_id=manager_tenant.tenant_id, actor_id="manager-actor")
    clock = Clock()
    authorization = PilotAuthorizationService(db, auth_service=auth, canonical_authority=authority, audit_service=audit, clock=clock)
    provisioning = PilotAccountProvisioningService(db, auth_service=auth, canonical_authority=authority, pilot_authorization_service=authorization, audit_service=audit, clock=clock)
    service = ControlledAnalystPilotService(db, canonical_authority=authority, audit_service=audit, provisioning_service=provisioning, clock=clock)
    account = provisioning.provision(
        manager_tenant_id=manager_tenant.tenant_id,
        provisioned_by="manager-actor",
        username="pilot-analyst",
        email="pilot.analyst@example.test",
        display_name="Pilot Analyst",
        tenant_name="Controlled Pilot",
        expires_at=(clock.value + timedelta(days=2)).isoformat(),
        approved_scenarios=["phishing_compromise"],
        audit_correlation_id="corr-provision",
    )
    tenant = service.onboard_provisioned_account(
        provisioning_id=account.provisioning_id,
        manager_tenant_id=manager_tenant.tenant_id,
        actor_id="manager-actor",
        correlation_id="corr-onboard",
        display_name="Controlled Pilot",
    )
    return db, auth, authority, audit, service, account, tenant, manager_password, clock


def test_onboarding_is_durable_scoped_and_assigns_analyst_role(pilot):
    db, _auth, authority, audit, service, account, tenant, *_ = pilot
    assert tenant.status == "onboarded"
    assert tenant.synthetic_only is True
    assert tenant.external_custody_required is True
    assert tenant.analyst_id == account.analyst_id
    assert authority.resolve(tenant.tenant_id, account.analyst_id)[2].role == "analyst"
    assert service.tenant_state(tenant.tenant_id).tenant_id == tenant.tenant_id
    actions = {event["action"] for event in service.list_audit(tenant.tenant_id)}
    assert "pilot_tenant_onboarded" in actions
    assert any(event["event_type"] == "CONTROLLED_PILOT_TENANT_ONBOARDED" for event in audit.list_for_tenant(tenant.tenant_id))
    with db.session() as connection:
        assert connection.execute("SELECT COUNT(*) FROM controlled_pilot_membership_events").fetchone()[0] == 1


def test_feedback_is_append_only_server_attributed_and_tenant_scoped(pilot):
    _db, _auth, _authority, _audit, service, account, tenant, *_ = pilot
    feedback = service.capture_feedback(
        tenant_id=tenant.tenant_id,
        analyst_id=account.analyst_id,
        case_id="CASE-1",
        investigation_id="INV-1",
        payload={
            "decision": "accepted",
            "helpful_rating": 5,
            "confidence_rating": 4,
            "estimated_time_saved": 20,
            "comments": "Evidence chain was clear.",
        },
        correlation_id="corr-feedback",
    )
    assert feedback["analyst_id"] == account.analyst_id
    assert service.list_feedback(tenant.tenant_id)[0]["feedback_id"] == feedback["feedback_id"]
    assert service.list_feedback(tenant.manager_tenant_id)[0]["feedback_id"] == feedback["feedback_id"]
    assert service.list_feedback("other-tenant") == []
    with pytest.raises(ControlledAnalystPilotError, match="invalid_feedback_fields"):
        service.capture_feedback(
            tenant_id=tenant.tenant_id, analyst_id=account.analyst_id,
            case_id="CASE-1", investigation_id="INV-1",
            payload={"decision": "accepted", "helpful_rating": 5, "confidence_rating": 5, "estimated_time_saved": 1, "comments": "ok", "tenant_id": "attacker"},
            correlation_id="corr-invalid",
        )


def test_review_requires_manager_transition_and_supports_compensating_reopen(pilot):
    _db, _auth, _authority, _audit, service, account, tenant, *_ = pilot
    review = service.submit_review(
        tenant_id=tenant.tenant_id, analyst_id=account.analyst_id,
        case_id="CASE-1", investigation_id="INV-1", decision="accepted",
        comments="I agree with the recommendation.", correlation_id="corr-submit",
    )
    assert review.status == "pending_review"
    accepted = service.transition_review(
        review.review_id, actor_id="manager-actor", decision="accepted",
        comments="Manager reviewed the evidence.", correlation_id="corr-accept",
    )
    assert accepted.status == "accepted"
    reopened = service.reopen_review(
        review.review_id, actor_id="manager-actor", reason="New evidence was attached.", correlation_id="corr-reopen",
    )
    assert reopened.status == "reopened"
    assert service.list_reviews(tenant.manager_tenant_id)[0].review_id == review.review_id
    assert service.list_audit(tenant.manager_tenant_id)
    with pytest.raises(ControlledAnalystPilotError, match="review_not_transitionable"):
        service.transition_review(
            review.review_id, actor_id="manager-actor", decision="accepted",
            comments="duplicate finalization", correlation_id="corr-duplicate",
        )
    with _db.session() as connection:
        assert connection.execute("SELECT COUNT(*) FROM controlled_pilot_review_events WHERE review_id=?", (review.review_id,)).fetchone()[0] == 3


def test_suspend_resume_and_expiry_fail_closed(pilot):
    _db, _auth, _authority, _audit, service, account, tenant, _manager_password, clock = pilot
    suspended = service.suspend(tenant.tenant_id, actor_id="manager-actor", correlation_id="corr-suspend")
    assert suspended.status == "suspended"
    with pytest.raises(ControlledAnalystPilotError, match="pilot_tenant_inactive"):
        service.submit_review(tenant_id=tenant.tenant_id, analyst_id=account.analyst_id, case_id="C", investigation_id="I", decision="accepted", comments="not allowed", correlation_id="corr-blocked")
    resumed = service.resume(tenant.tenant_id, actor_id="manager-actor", correlation_id="corr-resume")
    assert resumed.status == "resumed"
    clock.value += timedelta(days=3)
    with pytest.raises(ControlledAnalystPilotError, match="pilot_tenant_inactive"):
        service.capture_feedback(tenant_id=tenant.tenant_id, analyst_id=account.analyst_id, case_id="C", investigation_id="I", payload={"decision": "accepted", "helpful_rating": 5, "confidence_rating": 5, "estimated_time_saved": 1, "comments": "expired"}, correlation_id="corr-expired")
