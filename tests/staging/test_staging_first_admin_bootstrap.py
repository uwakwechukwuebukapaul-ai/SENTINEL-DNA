"""Current-main-native staging bootstrap authorization coverage."""

from datetime import datetime, timedelta, timezone
import importlib
import json

import pytest

from database.canonical_authority import CanonicalUnitOfWork
from database.connection import DatabaseConnection
from services.audit.service import AuditService
from services.auth.auth_service import AuthService
from services.auth.privileged_provisioning import PrivilegedIdentityProvisioningService
from services.auth.staging_bootstrap_authorization import (
    BOOTSTRAP_OPERATION,
    BOOTSTRAP_PURPOSE,
    BOOTSTRAP_ROLE,
    StagingBootstrapAuthorizationError,
    StagingBootstrapAuthorizationService,
    VerifiedBootstrapPrincipal,
    artifact_hash,
    canonical_artifact,
)
from services.identity.authentication import (
    AuthenticatedProviderPrincipal,
    CanonicalAuthenticationBoundary,
)
from services.identity.canonical_authority import CanonicalAuthorityService
from services.identity.request_context import CanonicalRequestContextService


PASSWORD = "Strong staging password 123!"


def services_for(tmp_path):
    db = DatabaseConnection(tmp_path / "bootstrap.sqlite")
    auth = AuthService(db)
    authority = CanonicalAuthorityService(db)
    audit = AuditService(db)
    migration = importlib.import_module("database.migrations.011_staging_first_privileged_identity")
    with db.session() as connection:
        migration.upgrade(connection)
    tenant = authority.tenants.create("Bootstrap control tenant", "control-tenant")
    return db, auth, authority, audit, tenant.tenant_id


def principal(db, auth, authority, tenant_id, role, label):
    actor_id = f"actor-{label}"
    user = auth.register(
        f"{label}-user", f"{label}@example.test", PASSWORD, role,
        tenant_id=tenant_id, actor_id=actor_id,
    )
    authority.identities.create(user.email, user.username, actor_id)
    authority.memberships.add(tenant_id, actor_id, role)
    with db.session() as connection:
        connection.execute(
            """INSERT INTO canonical_identity_bindings(
               binding_id,provider,external_subject,actor_id,status,created_at,updated_at,created_by,revoked_at
            ) VALUES(?,?,?,?,?,?,?,?,NULL)""",
            (f"binding-{label}", "entra", f"subject-{label}", actor_id,
             "active", "now", "now", "test"),
        )
    boundary = CanonicalAuthenticationBoundary(CanonicalRequestContextService(authority))
    return VerifiedBootstrapPrincipal.from_provider_principal(
        AuthenticatedProviderPrincipal(
            provider="entra", subject=f"subject-{label}", tenant_id=tenant_id,
            actor_id=actor_id, authentication_method="oidc",
            credential_id=f"credential-{label}", external_subject=f"subject-{label}",
        ),
        boundary=boundary,
        db=db,
    )


def create_approved(db, auth, authority, audit, tenant_id):
    requester = principal(db, auth, authority, tenant_id, "analyst", "requester")
    reviewer = principal(db, auth, authority, tenant_id, "soc_manager", "reviewer")
    service = StagingBootstrapAuthorizationService(db, authority=authority, audit=audit)
    authorization = service.create_request(
        requester,
        control_tenant_id=tenant_id,
        target_username="first-manager",
        target_email="first-manager@example.test",
        database_target_identity="postgresql://sentinel@rehearsal:5432/sentinel_dna",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    approved = service.approve(reviewer, authorization.authorization_id)
    return service, requester, reviewer, approved


def test_success_consumes_approval_and_preserves_provenance(tmp_path):
    db, auth, authority, audit, tenant_id = services_for(tmp_path)
    service, requester, reviewer, approved = create_approved(db, auth, authority, audit, tenant_id)
    provisioning = PrivilegedIdentityProvisioningService(auth, authority, audit, db)
    artifact = canonical_artifact(
        operation=BOOTSTRAP_OPERATION, purpose=BOOTSTRAP_PURPOSE, environment="staging",
        control_tenant_id=tenant_id, target_username="first-manager",
        target_email="first-manager@example.test", target_role=BOOTSTRAP_ROLE,
        database_target_identity="postgresql://sentinel@rehearsal:5432/sentinel_dna",
        requester_actor_id=requester.actor_id,
        approval_transaction_id=approved.approval_transaction_id,
        expires_at=approved.expires_at,
    )
    with CanonicalUnitOfWork(db) as unit:
        result = provisioning.provision(
            username="first-manager", email="first-manager@example.test",
            tenant_id=tenant_id, role="soc_manager", password=PASSWORD,
            password_confirmation=PASSWORD, connection=unit.conn,
            audit_actor_id=reviewer.actor_id,
        )
        consumed = service.consume(
            unit.conn, authorization_id=approved.authorization_id,
            approval_transaction_id=approved.approval_transaction_id,
            artifact=artifact, control_tenant_id=tenant_id,
            correlation_id="bootstrap-correlation", created_user_id=result.user_id,
            created_actor_id=result.actor_id,
        )
        audit.record(
            "STAGING_FIRST_PRIVILEGED_IDENTITY_BOOTSTRAPPED",
            user_id=result.user_id, tenant_id=tenant_id, actor_id=reviewer.actor_id,
            operation=BOOTSTRAP_OPERATION, outcome="success",
            metadata={
                "requester_actor_id": requester.actor_id,
                "requester_user_id": requester.user_id,
                "reviewer_actor_id": reviewer.actor_id,
                "reviewer_user_id": reviewer.user_id,
                "created_actor_id": result.actor_id,
                "created_user_id": result.user_id,
                "approval_id": consumed.authorization_id,
                "approval_transaction_id": consumed.approval_transaction_id,
                "bootstrap_correlation_id": "bootstrap-correlation",
                "role": BOOTSTRAP_ROLE,
            },
            connection=unit.conn,
        )
    assert consumed.status == "CONSUMED"
    assert result.role == "soc_manager"
    events = audit.list_for_tenant(tenant_id)
    event = next(item for item in events if item["event_type"] == "STAGING_FIRST_PRIVILEGED_IDENTITY_BOOTSTRAPPED")
    assert event["actor_id"] == reviewer.actor_id
    assert event["details"]["requester_actor_id"] == requester.actor_id
    assert event["details"]["created_actor_id"] == result.actor_id
    assert PASSWORD.lower() not in json.dumps(events).lower()


def test_requester_cannot_approve_own_request(tmp_path):
    db, auth, authority, audit, tenant_id = services_for(tmp_path)
    requester = principal(db, auth, authority, tenant_id, "analyst", "requester")
    service = StagingBootstrapAuthorizationService(db, authority=authority, audit=audit)
    authorization = service.create_request(
        requester, control_tenant_id=tenant_id, target_username="manager",
        target_email="manager@example.test",
        database_target_identity="postgresql://sentinel@rehearsal:5432/sentinel_dna",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    with pytest.raises(StagingBootstrapAuthorizationError, match="requester_reviewer_same_identity"):
        service.approve(requester, authorization.authorization_id)


def test_analyst_cannot_approve(tmp_path):
    db, auth, authority, audit, tenant_id = services_for(tmp_path)
    service, requester, _reviewer, authorization = create_approved(db, auth, authority, audit, tenant_id)
    analyst = principal(db, auth, authority, tenant_id, "analyst", "second-analyst")
    with db.session() as connection:
        connection.execute(
            "UPDATE staging_bootstrap_authorizations SET status='REQUESTED' WHERE authorization_id=?",
            (authorization.authorization_id,),
        )
    with pytest.raises(StagingBootstrapAuthorizationError, match="capability_denied"):
        service.approve(analyst, authorization.authorization_id)


def test_artifact_hash_is_exact_and_secret_free():
    artifact = canonical_artifact(
        operation=BOOTSTRAP_OPERATION, purpose=BOOTSTRAP_PURPOSE, environment="staging",
        control_tenant_id="tenant", target_username="manager", target_email="manager@example.test",
        target_role="soc_manager", database_target_identity="postgresql://u@h:5432/db",
        requester_actor_id="requester", approval_transaction_id="transaction",
        expires_at="2030-01-01T00:00:00+00:00",
    )
    assert artifact_hash(artifact) == artifact_hash(dict(reversed(list(artifact.items()))))
    assert all(secret not in json.dumps(artifact).lower() for secret in ("password", "token", "cookie", "private_key"))
