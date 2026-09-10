from datetime import datetime, timedelta, timezone
import secrets

import pytest
from flask import Flask
from flask import session

from database.connection import DatabaseConnection
from services.audit.service import AuditService
from services.auth.auth_service import AuthService
from services.core.service_registry import ServiceRegistry
from services.identity.canonical_authority import CanonicalAuthorityService
from services.pilot_management.authorization import (
    PilotAuthorizationError,
    PilotAuthorizationService,
)
from services.pilot_management.routes import pilot_authorization_api
from services.auth import auth_api
from services.core.security_context import authorize_investigation


class Clock:
    def __init__(self, value):
        self.value = value

    def __call__(self):
        return self.value


@pytest.fixture
def pilot_services(tmp_path):
    db = DatabaseConnection(tmp_path / "pilot-authorization.db")
    auth = AuthService(db)
    authority = CanonicalAuthorityService(db, auth=auth)
    audit = AuditService(db)
    tenant = authority.tenants.create("Pilot tenant", "pilot-tenant")
    authority.identities.create("manager@example.test", "manager", "manager-actor")
    authority.identities.create("analyst@example.test", "analyst", "analyst-actor")
    authority.memberships.add(tenant.tenant_id, "manager-actor", "admin")
    authority.memberships.add(tenant.tenant_id, "analyst-actor", "analyst")
    manager_password = secrets.token_urlsafe(24)
    analyst_password = secrets.token_urlsafe(24)
    auth.register("manager", "manager@example.test", manager_password, "admin", tenant_id=tenant.tenant_id, actor_id="manager-actor")
    auth.register("analyst", "analyst@example.test", analyst_password, "analyst", tenant_id=tenant.tenant_id, actor_id="analyst-actor")
    clock = Clock(datetime.now(timezone.utc))
    service = PilotAuthorizationService(
        db,
        auth_service=auth,
        canonical_authority=authority,
        audit_service=audit,
        clock=clock,
    )
    return db, auth, authority, audit, service, clock, tenant.tenant_id, manager_password, analyst_password


def test_create_binds_active_analyst_tenant_role_and_audit(pilot_services):
    _db, _auth, _authority, audit, service, clock, tenant_id, _manager_password, _analyst_password = pilot_services
    authorization = service.create(
        analyst_id="analyst-actor",
        tenant_id=tenant_id,
        authorized_by="manager-actor",
        expires_at=(clock.value + timedelta(hours=2)).isoformat(),
        approved_scenarios=["multi_ioc_investigation", "phishing_compromise"],
        audit_correlation_id="corr-create",
    )

    assert authorization.role == "analyst"
    assert authorization.authorization_status == "active"
    assert authorization.approved_scenarios == ("multi_ioc_investigation", "phishing_compromise")
    events = audit.list_for_tenant(tenant_id)
    assert any(item["event_type"] == "PILOT_AUTHORIZATION_CREATED" for item in events)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"analyst_id": "unknown", "tenant_id": "pilot-tenant"},
        {"analyst_id": "manager-actor", "tenant_id": "pilot-tenant"},
        {"analyst_id": "analyst-actor", "tenant_id": "other-tenant"},
    ],
)
def test_authorization_creation_rejects_unknown_wrong_role_or_wrong_tenant(pilot_services, kwargs):
    _db, _auth, _authority, _audit, service, clock, tenant_id, _manager_password, _analyst_password = pilot_services
    with pytest.raises(PilotAuthorizationError):
        service.create(
            analyst_id=kwargs["analyst_id"],
            tenant_id=kwargs["tenant_id"],
            authorized_by="manager-actor",
            expires_at=(clock.value + timedelta(hours=2)).isoformat(),
            approved_scenarios=["phishing_compromise"],
            audit_correlation_id="corr-invalid",
        )


def test_authorization_service_requires_manager_authorizer(pilot_services):
    _db, _auth, _authority, _audit, service, clock, tenant_id, _manager_password, _analyst_password = pilot_services
    with pytest.raises(PilotAuthorizationError, match="authorized_by_manager_role_required"):
        service.create(
            analyst_id="analyst-actor",
            tenant_id=tenant_id,
            authorized_by="analyst-actor",
            expires_at=(clock.value + timedelta(hours=2)).isoformat(),
            approved_scenarios=["phishing_compromise"],
            audit_correlation_id="corr-invalid-authorizer",
        )


def test_expired_and_unapproved_authorization_fail_closed(pilot_services):
    _db, _auth, _authority, _audit, service, clock, tenant_id, _manager_password, _analyst_password = pilot_services
    authorization = service.create(
        analyst_id="analyst-actor",
        tenant_id=tenant_id,
        authorized_by="manager-actor",
        expires_at=(clock.value + timedelta(minutes=5)).isoformat(),
        approved_scenarios=["phishing_compromise"],
        audit_correlation_id="corr-expiry",
    )
    assert service.active_for("analyst-actor", tenant_id) is not None
    assert service.is_scenario_allowed(authorization.authorization_id, "phishing_compromise", tenant_id=tenant_id)
    assert not service.is_scenario_allowed(authorization.authorization_id, "malware_execution", tenant_id=tenant_id)
    clock.value += timedelta(minutes=6)
    assert service.active_for("analyst-actor", tenant_id) is None
    assert not service.is_scenario_allowed(authorization.authorization_id, "phishing_compromise", tenant_id=tenant_id)


def test_revoke_denies_authorization_invalidates_sessions_and_audits(pilot_services):
    _db, auth, _authority, audit, service, clock, tenant_id, _manager_password, _analyst_password = pilot_services
    analyst = auth.get_by_username("analyst")
    authorization = service.create(
        analyst_id="analyst-actor",
        tenant_id=tenant_id,
        authorized_by="manager-actor",
        expires_at=(clock.value + timedelta(hours=2)).isoformat(),
        approved_scenarios=["phishing_compromise"],
        audit_correlation_id="corr-create-revoke",
    )
    old_version = analyst.session_version
    revoked = service.revoke(
        authorization.authorization_id,
        tenant_id=tenant_id,
        revoked_by="manager-actor",
        reason="pilot complete",
        audit_correlation_id="corr-revoke",
    )

    assert revoked.authorization_status == "revoked"
    assert service.active_for("analyst-actor", tenant_id) is None
    assert auth.session_user(analyst.id, old_version) is None
    events = audit.list_for_tenant(tenant_id)
    assert any(item["event_type"] == "PILOT_AUTHORIZATION_REVOKED" for item in events)


def test_http_boundary_requires_manager_and_revocation_really_expires_session(pilot_services):
    _db, _auth, authority, _audit, service, clock, tenant_id, manager_password, analyst_password = pilot_services
    registry = ServiceRegistry()
    registry.register("auth_service", _auth)
    registry.register("canonical_authority", authority)
    registry.register("pilot_authorization_service", service)

    application = Flask(__name__)
    application.secret_key = secrets.token_urlsafe(32)
    application.config["PILOT_ACCESS_REQUIRED"] = True
    application.container = registry
    application.register_blueprint(auth_api)
    application.register_blueprint(pilot_authorization_api)

    manager = application.test_client()
    analyst = application.test_client()

    def login(client, username, password):
        csrf = client.get("/api/auth/csrf").get_json()["csrf_token"]
        response = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 200

    login(manager, "manager", manager_password)
    login(analyst, "analyst", analyst_password)

    assert analyst.get("/api/pilot-authorizations/current").status_code == 403
    manager_csrf = manager.get("/api/auth/csrf").get_json()["csrf_token"]
    response = manager.post(
        "/api/pilot-authorizations",
        json={
            "analyst_id": "analyst-actor",
            "expires_at": (clock.value + timedelta(hours=2)).isoformat(),
            "approved_scenarios": ["phishing_compromise"],
        },
        headers={"X-CSRF-Token": manager_csrf},
    )
    assert response.status_code == 201
    authorization_id = response.get_json()["authorization_id"]

    assert analyst.get("/api/pilot-authorizations/current").status_code == 200
    assert analyst.get("/api/pilot-authorizations").status_code == 403
    with analyst.session_transaction() as analyst_session:
        session_copy = dict(analyst_session)
    with application.test_request_context("/api/investigations", method="POST"):
        session.update(session_copy)
        allowed, error = authorize_investigation(
            {"metadata": {"synthetic": True, "scenario": "phishing_compromise"}},
            write=True,
        )
        assert (allowed, error) == (True, "")
    with application.test_request_context("/api/investigations", method="POST"):
        session.update(session_copy)
        allowed, error = authorize_investigation(
            {"metadata": {"synthetic": False, "scenario": "phishing_compromise"}},
            write=True,
        )
        assert (allowed, error) == (False, "pilot_synthetic_data_required")
    manager_csrf = manager.get("/api/auth/csrf").get_json()["csrf_token"]
    revoked = manager.post(
        f"/api/pilot-authorizations/{authorization_id}/revoke",
        json={"reason": "pilot complete"},
        headers={"X-CSRF-Token": manager_csrf},
    )
    assert revoked.status_code == 200
    assert analyst.get("/api/auth/me").status_code == 401
