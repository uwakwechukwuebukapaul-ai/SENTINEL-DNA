from datetime import datetime, timedelta, timezone
import json
import secrets

import pytest
from flask import Flask

from database.connection import DatabaseConnection
from services.audit.service import AuditService
from services.auth.auth_service import AuthService
from services.auth import auth_api
from services.core.service_registry import ServiceRegistry
from services.identity.canonical_authority import CanonicalAuthorityService
from services.pilot_management.authorization import PilotAuthorizationService
from services.pilot_management.provisioning import (
    PilotAccountProvisioningService,
    PilotProvisioningError,
)
from services.pilot_management.routes import pilot_provisioning_api


class Clock:
    def __init__(self, value):
        self.value = value

    def __call__(self):
        return self.value


@pytest.fixture
def provisioning_services(tmp_path):
    db = DatabaseConnection(tmp_path / "pilot-provisioning.db")
    auth = AuthService(db)
    authority = CanonicalAuthorityService(db, auth=auth)
    audit = AuditService(db)
    manager_tenant = authority.tenants.create("Manager tenant", "manager-tenant")
    authority.identities.create("manager@example.test", "Manager", "manager-actor")
    authority.identities.create("analyst@example.test", "Analyst", "analyst-actor")
    authority.memberships.add(manager_tenant.tenant_id, "manager-actor", "admin")
    authority.memberships.add(manager_tenant.tenant_id, "analyst-actor", "analyst")
    manager_password = secrets.token_urlsafe(24)
    analyst_password = secrets.token_urlsafe(24)
    auth.register(
        "manager",
        "manager@example.test",
        manager_password,
        "admin",
        tenant_id=manager_tenant.tenant_id,
        actor_id="manager-actor",
    )
    auth.register(
        "analyst",
        "analyst@example.test",
        analyst_password,
        "analyst",
        tenant_id=manager_tenant.tenant_id,
        actor_id="analyst-actor",
    )
    clock = Clock(datetime.now(timezone.utc))
    authorizations = PilotAuthorizationService(
        db,
        auth_service=auth,
        canonical_authority=authority,
        audit_service=audit,
        clock=clock,
    )
    provisioning = PilotAccountProvisioningService(
        db,
        auth_service=auth,
        canonical_authority=authority,
        pilot_authorization_service=authorizations,
        audit_service=audit,
        clock=clock,
    )
    return db, auth, authority, audit, provisioning, clock, manager_tenant.tenant_id, manager_password, analyst_password


def provision(provisioning, clock, manager_tenant_id, **overrides):
    values = {
        "manager_tenant_id": manager_tenant_id,
        "provisioned_by": "manager-actor",
        "username": "remote-analyst",
        "email": "remote.analyst@example.test",
        "display_name": "Remote Analyst",
        "tenant_name": "Remote analyst pilot",
        "expires_at": (clock.value + timedelta(days=2)).isoformat(),
        "approved_scenarios": ["phishing_compromise", "suspicious_authentication"],
        "audit_correlation_id": "corr-provision",
    }
    values.update(overrides)
    return provisioning.provision(**values)


def test_provisioning_creates_inactive_account_isolated_tenant_and_bounded_authorization(provisioning_services):
    db, auth, authority, audit, provisioning, clock, manager_tenant_id, _manager_password, _analyst_password = provisioning_services
    result = provision(provisioning, clock, manager_tenant_id)

    with db.session() as connection:
        user = auth.get_by_username("remote-analyst", connection=connection)
    assert result.account_status == "pending_activation"
    assert result.authorization_status == "active"
    assert result.tenant_status == "active"
    assert result.activation_token
    assert user.is_active is False
    assert user.role == "analyst"
    assert user.expires_at == result.expires_at
    assert user.password_hash != result.activation_token
    assert result.tenant_id != manager_tenant_id
    with pytest.raises(Exception):
        authority.resolve(manager_tenant_id, result.analyst_id)
    assert authority.resolve(result.tenant_id, result.analyst_id)[2].role == "analyst"
    events = audit.list_for_tenant(result.tenant_id)
    event_types = {event["event_type"] for event in events}
    assert {"PILOT_TENANT_CREATED", "PILOT_ACCOUNT_PROVISIONED", "PILOT_AUTHORIZATION_CREATED"} <= event_types
    assert all(result.activation_token not in json.dumps(event) for event in events)


def test_duplicate_identity_and_unbounded_expiry_are_rejected(provisioning_services):
    _db, _auth, _authority, _audit, provisioning, clock, manager_tenant_id, _manager_password, _analyst_password = provisioning_services
    provision(provisioning, clock, manager_tenant_id)
    with pytest.raises(PilotProvisioningError, match="duplicate_account_identifier"):
        provision(provisioning, clock, manager_tenant_id, username="other-name")
    with pytest.raises(PilotProvisioningError, match="expires_at_exceeds_pilot_limit"):
        provision(
            provisioning,
            clock,
            manager_tenant_id,
            username="other-analyst",
            email="other.analyst@example.test",
            expires_at=(clock.value + timedelta(days=31)).isoformat(),
        )


def test_inactive_manager_cannot_provision(provisioning_services):
    _db, auth, _authority, _audit, provisioning, clock, manager_tenant_id, _manager_password, _analyst_password = provisioning_services
    manager = auth.get_by_username("manager")
    assert auth.deactivate_user(manager.id) is True
    with pytest.raises(Exception, match="active_manager_account_required"):
        provision(provisioning, clock, manager_tenant_id)


def test_activation_is_expiring_single_use_and_does_not_store_plaintext_password(provisioning_services):
    db, auth, _authority, audit, provisioning, clock, manager_tenant_id, _manager_password, _analyst_password = provisioning_services
    result = provision(provisioning, clock, manager_tenant_id)
    activation_password = secrets.token_urlsafe(24)
    replay_password = secrets.token_urlsafe(24)
    activated = provisioning.activate(
        token=result.activation_token,
        password=activation_password,
        audit_correlation_id="corr-activate",
    )
    assert activated.account_status == "active"
    assert auth.authenticate("remote-analyst", activation_password) is not None
    with pytest.raises(PilotProvisioningError, match="activation_invalid"):
        provisioning.activate(
            token=result.activation_token,
            password=replay_password,
            audit_correlation_id="corr-replay",
        )
    with db.session() as connection:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE username=?", ("remote-analyst",)
        ).fetchone()
        activation = connection.execute(
            "SELECT token_hash FROM pilot_account_activations WHERE activation_id=?",
            (result.activation_id,),
        ).fetchone()
    assert row["password_hash"] != activation_password
    assert activation["token_hash"] != result.activation_token
    events = audit.list_for_tenant(result.tenant_id)
    assert any(event["event_type"] == "PILOT_ANALYST_ACTIVATED" for event in events)
    assert all(result.activation_token not in json.dumps(event) for event in events)


def test_expired_activation_is_denied(provisioning_services):
    _db, _auth, _authority, _audit, provisioning, clock, manager_tenant_id, _manager_password, _analyst_password = provisioning_services
    result = provision(provisioning, clock, manager_tenant_id)
    clock.value += timedelta(days=3)
    with pytest.raises(PilotProvisioningError, match="activation_invalid"):
        provisioning.activate(
            token=result.activation_token,
            password=secrets.token_urlsafe(24),
            audit_correlation_id="corr-expired",
        )


def test_revoke_deactivates_account_tenant_authorization_and_sessions(provisioning_services):
    db, auth, authority, audit, provisioning, clock, manager_tenant_id, _manager_password, _analyst_password = provisioning_services
    activation_password = secrets.token_urlsafe(24)
    result = provision(provisioning, clock, manager_tenant_id)
    provisioning.activate(
        token=result.activation_token,
        password=activation_password,
        audit_correlation_id="corr-activate",
    )
    user = auth.authenticate("remote-analyst", activation_password)
    old_version = user.session_version
    revoked = provisioning.revoke(
        provisioning_id=result.provisioning_id,
        manager_tenant_id=manager_tenant_id,
        revoked_by="manager-actor",
        reason="pilot complete",
        audit_correlation_id="corr-revoke",
    )
    assert revoked.account_status == "revoked"
    assert revoked.authorization_status == "revoked"
    assert revoked.tenant_status == "revoked"
    assert auth.session_user(user.id, old_version) is None
    with pytest.raises(Exception):
        authority.resolve(result.tenant_id, result.analyst_id)
    events = audit.list_for_tenant(result.tenant_id)
    event_types = {event["event_type"] for event in events}
    assert {"PILOT_ACCOUNT_DEACTIVATED", "PILOT_TENANT_REVOKED", "PILOT_AUTHORIZATION_REVOKED"} <= event_types


def test_http_provisioning_is_manager_only_csrf_protected_and_registration_is_disabled(provisioning_services):
    _db, auth, authority, _audit, provisioning, clock, manager_tenant_id, manager_password, analyst_password = provisioning_services
    registry = ServiceRegistry()
    registry.register("auth_service", auth)
    registry.register("canonical_authority", authority)
    registry.register("pilot_authorization_service", provisioning.pilot_authorization_service)
    registry.register("pilot_account_provisioning_service", provisioning)
    application = Flask(__name__)
    application.secret_key = secrets.token_urlsafe(32)
    application.config["PILOT_ACCESS_REQUIRED"] = True
    application.config["AUTH_LEGACY_JSON_COMPAT"] = True
    application.container = registry
    application.register_blueprint(auth_api)
    application.register_blueprint(pilot_provisioning_api)
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
    csrf = manager.get("/api/auth/csrf").get_json()["csrf_token"]
    payload = {
        "username": "http-analyst",
        "email": "http.analyst@example.test",
        "display_name": "HTTP Analyst",
        "tenant_name": "HTTP pilot",
        "expires_at": (clock.value + timedelta(days=1)).isoformat(),
        "approved_scenarios": ["phishing_compromise"],
    }
    analyst_response = analyst.post("/api/pilot-provisioning", json=payload, headers={"X-CSRF-Token": csrf})
    assert analyst_response.status_code == 403, analyst_response.get_json()
    assert manager.post("/api/pilot-provisioning", json=payload).status_code == 403
    assert manager.post(
        "/api/pilot-provisioning",
        json=payload,
        headers={"Origin": "https://untrusted.example"},
    ).status_code == 403
    response = manager.post(
        "/api/pilot-provisioning", json=payload, headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 201
    result = response.get_json()
    assert result["account_status"] == "pending_activation"
    assert result["activation_token"]
    assert manager.get("/api/pilot-provisioning").status_code == 200
    registration_csrf = manager.get("/api/auth/csrf").get_json()["csrf_token"]
    assert manager.post(
        "/api/auth/register",
        json={"username": "self-service", "email": "self@example.test", "password": secrets.token_urlsafe(24)},
        headers={"X-CSRF-Token": registration_csrf},
    ).status_code == 403
