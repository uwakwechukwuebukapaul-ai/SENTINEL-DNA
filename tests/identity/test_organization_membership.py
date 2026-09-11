from types import SimpleNamespace

import pytest

from database.connection import DatabaseConnection
from services.auth.auth_service import AuthService
from services.audit.service import AuditService
from services.identity.canonical_authority import CanonicalAuthorityService
from services.identity.organization_membership import (
    OrganizationMembershipError,
    OrganizationMembershipService,
    normalize_domain,
    normalize_email,
)
from services.auth.providers import TestEmailProvider, TestSMSProvider
from app import create_app


PASSWORD = "ValidPassword!42"


@pytest.fixture
def services(tmp_path):
    db = DatabaseConnection(tmp_path / "organization-membership.sqlite")
    auth = AuthService(db)
    audit = AuditService(db)
    authority = CanonicalAuthorityService(db, auth=auth)
    organizations = OrganizationMembershipService(db, authority=authority, auth=auth, audit=audit)
    return db, auth, audit, authority, organizations


def admin_context(tenant_id="tenant-a", actor_id="admin-a"):
    return SimpleNamespace(tenant_id=tenant_id, actor_id=actor_id)


def create_admin(services):
    _db, auth, _audit, authority, organizations = services
    user = auth.register("org-admin", "admin@company.example", PASSWORD, role="admin")
    tenant = authority.tenants.create("Company", tenant_id="tenant-a")
    identity = authority.identities.create(user.email, display_name=user.username, actor_id="admin-a")
    authority.memberships.add(tenant.tenant_id, identity.actor_id, "admin")
    with auth.db.session() as connection:
        connection.execute("UPDATE users SET actor_id=?, tenant_id=? WHERE id=?", ("admin-a", tenant.tenant_id, user.id))
    organizations.configure_domain(
        admin_context(),
        "Company.Example.",
        verification_status="verified",
        enrollment_policy="ADMIN_APPROVAL_REQUIRED",
    )
    return user, tenant


def test_email_and_domain_normalization_is_canonical():
    assert normalize_domain(" Company.Example. ") == "company.example"
    assert normalize_email(" Analyst@Company.Example ") == "analyst@company.example"
    with pytest.raises(OrganizationMembershipError):
        normalize_domain("localhost")


def test_username_canonical_uniqueness_rejects_case_variants(services):
    auth = services[1]
    auth.register("CaseUser", "case-one@company.example", PASSWORD)
    with pytest.raises(Exception):
        auth.register("caseuser", "case-two@company.example", PASSWORD)
    with pytest.raises(ValueError, match="invalid_user_registration"):
        auth.register("admin", "reserved@company.example", PASSWORD)


def test_verified_existing_domain_is_detected_without_creating_a_tenant(services):
    _admin, tenant = create_admin(services)
    decision = services[-1].inspect_email("new.employee@company.example")
    assert decision.existing_verified_active
    assert decision.tenant_id == tenant.tenant_id
    assert decision.enrollment_policy == "ADMIN_APPROVAL_REQUIRED"


def test_domain_cannot_be_reassigned_to_another_tenant(services):
    _admin, _tenant = create_admin(services)
    authority = services[3]
    authority.tenants.create("Other", tenant_id="tenant-b")
    authority.identities.create("other-admin@other.example", actor_id="other-admin")
    authority.memberships.add("tenant-b", "other-admin", "admin")
    with pytest.raises(OrganizationMembershipError, match="domain_ownership_conflict"):
        services[-1].configure_domain(
            SimpleNamespace(tenant_id="tenant-b", actor_id="other-admin"),
            "company.example",
            verification_status="verified",
            enrollment_policy="ADMIN_APPROVAL_REQUIRED",
        )


def test_join_request_is_idempotent_and_admin_approval_is_authorized(services):
    _admin, tenant = create_admin(services)
    auth, authority, organizations = services[1], services[3], services[4]
    user = auth.register(
        "pending-user",
        "pending@company.example",
        PASSWORD,
        onboarding_state="ORGANIZATION_MEMBERSHIP_PENDING",
    )
    request_one = organizations.create_join_request(user.id, tenant.tenant_id)
    request_two = organizations.create_join_request(user.id, tenant.tenant_id)
    assert request_one["request_id"] == request_two["request_id"]
    with pytest.raises(OrganizationMembershipError, match="organization_authorization_denied"):
        organizations.decide_join_request(SimpleNamespace(tenant_id=tenant.tenant_id, actor_id="missing"), request_one["request_id"], approve=True)
    result = organizations.decide_join_request(admin_context(), request_one["request_id"], approve=True)
    assert result["status"] == "approved"
    membership = authority.memberships.get(tenant.tenant_id, user.actor_id or f"user-{user.id}")
    assert membership is not None and membership.status == "active"
    assert auth.get_by_id(user.id).onboarding_state == "ORGANIZATION_MEMBERSHIP_APPROVED"


def test_invitation_is_email_bound_single_use_and_role_is_server_assigned(services):
    admin, tenant = create_admin(services)
    auth, authority, organizations = services[1], services[3], services[4]
    invitation = organizations.create_invitation(admin_context(), "invitee@company.example")
    user = auth.register(
        "invitee-user",
        "invitee@company.example",
        PASSWORD,
        onboarding_state="ORGANIZATION_MEMBERSHIP_PENDING",
    )
    accepted = organizations.accept_invitation(user.id, invitation["token"])
    assert accepted["tenant_id"] == tenant.tenant_id
    membership = authority.memberships.get(tenant.tenant_id, user.actor_id or f"user-{user.id}")
    assert membership and membership.role == "analyst"
    with pytest.raises(OrganizationMembershipError, match="invitation_invalid"):
        organizations.accept_invitation(user.id, invitation["token"])

    wrong_user = auth.register(
        "wrong-invitee",
        "wrong@company.example",
        PASSWORD,
        onboarding_state="ORGANIZATION_MEMBERSHIP_PENDING",
    )
    second = organizations.create_invitation(admin_context(), "invitee@company.example")
    with pytest.raises(OrganizationMembershipError, match="invitation_invalid"):
        organizations.accept_invitation(wrong_user.id, second["token"])


def test_membership_revocation_invalidates_sessions_and_removes_authority(services):
    admin, tenant = create_admin(services)
    auth, authority, organizations = services[1], services[3], services[4]
    user = auth.register("revoked-user", "revoked@company.example", PASSWORD)
    actor = organizations.ensure_user_identity(user.id)
    authority.memberships.add(tenant.tenant_id, actor, "analyst")
    with auth.db.session() as connection:
        connection.execute("UPDATE users SET actor_id=?,tenant_id=? WHERE id=?", (actor, tenant.tenant_id, user.id))
    current = auth.get_by_id(user.id)
    auth.create_persistent_session(current, "opaque-token", tenant.tenant_id, "session-1", "2999-01-01T00:00:00+00:00")
    organizations.revoke_membership(admin_context(), actor_id=actor, user_id=user.id, tenant_id=tenant.tenant_id, reason="offboarding")
    membership = authority.memberships.get(tenant.tenant_id, actor)
    assert membership and membership.status == "inactive" and membership.lifecycle_state == "revoked"
    assert auth.get_by_id(user.id).onboarding_state == "ORGANIZATION_MEMBERSHIP_PENDING"
    assert auth.get_by_id(user.id).session_version == current.session_version + 1
    assert not auth.list_sessions(user.id)


def test_approved_membership_can_resume_verified_onboarding(services):
    _admin, tenant = create_admin(services)
    auth, organizations = services[1], services[4]
    user = auth.register(
        "resume-user",
        "resume@company.example",
        PASSWORD,
        phone_number="+2348031234567",
        phone_verified_at="2026-09-03T00:00:00+00:00",
        email_verified_at="2026-09-03T00:00:00+00:00",
        date_of_birth="2000-01-02",
        onboarding_state="ORGANIZATION_MEMBERSHIP_PENDING",
    )
    request = organizations.create_join_request(user.id, tenant.tenant_id)
    organizations.decide_join_request(admin_context(), request["request_id"], approve=True)
    completed = auth.complete_verified_onboarding(user.id)
    assert completed and completed.onboarding_state == "AUTHENTICATED"


def test_browser_registration_detects_existing_domain_and_stays_pending(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "browser-org.sqlite"))
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    application = create_app()
    application.config.update(TESTING=True, EMAIL_PROVIDER=TestEmailProvider(), SMS_PROVIDER=TestSMSProvider())
    auth = application.container.require("auth_service")
    authority = application.container.require("canonical_authority")
    organizations = application.container.require("organization_membership_service")
    admin = auth.register("browser-admin", "admin@enterprise.example", PASSWORD, role="admin")
    tenant = authority.tenants.create("Enterprise", tenant_id="enterprise-tenant")
    authority.identities.create(admin.email, actor_id="browser-admin-actor")
    authority.memberships.add(tenant.tenant_id, "browser-admin-actor", "admin")
    with auth.db.session() as connection:
        connection.execute("UPDATE users SET actor_id=?,tenant_id=? WHERE id=?", ("browser-admin-actor", tenant.tenant_id, admin.id))
    organizations.configure_domain(
        SimpleNamespace(tenant_id=tenant.tenant_id, actor_id="browser-admin-actor"),
        "enterprise.example",
        verification_status="verified",
        enrollment_policy="ADMIN_APPROVAL_REQUIRED",
    )

    with application.test_client() as client:
        csrf = client.get("/api/auth/csrf").get_json()["csrf_token"]
        sent_email = client.post("/api/auth/email/send-registration-code", json={"email": "new@enterprise.example"}, headers={"X-CSRF-Token": csrf})
        email_challenge = sent_email.get_json()["challenge_id"]
        email_code = application.config["EMAIL_PROVIDER"].messages[-1]["code"]
        assert client.post("/api/auth/email/verify-registration-code", json={"challenge_id": email_challenge, "code": email_code}, headers={"X-CSRF-Token": csrf}).status_code == 200
        response = client.post(
            "/api/auth/register",
            json={
                "username": "enterprise-analyst",
                "email": "new@enterprise.example",
                "password": PASSWORD,
                "email_challenge_id": email_challenge,
                "date_of_birth": "2000-01-02",
            },
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 202
        assert response.get_json() == {"status": "organization_approval_required"}
        assert client.get("/api/auth/me").status_code == 401
    user = auth.get_by_email("new@enterprise.example", include_inactive=True)
    assert user and user.onboarding_state == "ORGANIZATION_MEMBERSHIP_PENDING"
    assert organizations.inspect_email("new@enterprise.example").tenant_id == tenant.tenant_id


def test_legacy_json_registration_cannot_bypass_existing_verified_domain(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "legacy-org.sqlite"))
    monkeypatch.setenv("SENTINEL_DNA_ENV", "testing")
    application = create_app()
    application.config.update(TESTING=True, EMAIL_PROVIDER=TestEmailProvider(), SMS_PROVIDER=TestSMSProvider())
    auth = application.container.require("auth_service")
    authority = application.container.require("canonical_authority")
    organizations = application.container.require("organization_membership_service")
    admin = auth.register("legacy-admin", "admin@legacy.example", PASSWORD, role="admin")
    tenant = authority.tenants.create("Legacy Enterprise", tenant_id="legacy-tenant")
    authority.identities.create(admin.email, actor_id="legacy-admin-actor")
    authority.memberships.add(tenant.tenant_id, "legacy-admin-actor", "admin")
    with auth.db.session() as connection:
        connection.execute("UPDATE users SET actor_id=?,tenant_id=? WHERE id=?", ("legacy-admin-actor", tenant.tenant_id, admin.id))
    organizations.configure_domain(
        SimpleNamespace(tenant_id=tenant.tenant_id, actor_id="legacy-admin-actor"),
        "legacy.example",
        verification_status="verified",
        enrollment_policy="ADMIN_APPROVAL_REQUIRED",
    )

    with application.test_client() as client:
        csrf = client.get("/api/auth/csrf").get_json()["csrf_token"]
        response = client.post(
            "/api/auth/register",
            json={"username": "legacy-analyst", "email": "new@legacy.example", "password": PASSWORD},
            headers={"X-CSRF-Token": csrf},
        )

    assert response.status_code == 400
    assert auth.get_by_email("new@legacy.example", include_inactive=True) is None
