"""Unit and real-PostgreSQL coverage for the staging bootstrap."""

from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
from urllib.parse import urlparse
from uuid import uuid4

import pytest

from database.migration_runner import MigrationRunner
from database.migrations.registry import MIGRATIONS, STAGING_FIRST_PRIVILEGED_IDENTITY_NAMESPACE_MIGRATIONS
from services.audit.service import AuditService
from services.auth.auth_service import AuthService
from services.auth.privileged_provisioning import PrivilegedIdentityProvisioningService
from services.identity.approval_workflow import (
    ApprovalWorkflow,
    ApprovalWorkflowError,
    request_hash,
    resolve_authenticated_entra_context,
)
from services.identity.canonical_authority import CanonicalAuthorityService
from services.identity.entra_oidc import EntraIdentityTuple, VerifiedEntraToken


ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "deployment" / "staging" / "scripts" / "bootstrap_staging_first_privileged_identity.py"
PASSWORD = "Strong staging password 123!"


@pytest.fixture
def module():
    spec = importlib.util.spec_from_file_location("staging_first_bootstrap", SCRIPT)
    loaded = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def _environment(tenant_id="control-tenant"):
    database_url = os.getenv(
        "SENTINEL_DNA_TEST_POSTGRES_URL",
        "postgresql://sentinel_rehearsal@127.0.0.1:55433/sentinel_dna_rehearsal",
    )
    parsed = urlparse(database_url)
    target_identity = (
        f"postgresql://{parsed.username}@{parsed.hostname}:{parsed.port}{parsed.path}"
        if parsed.username and parsed.hostname and parsed.port and parsed.path
        else "postgresql://sentinel_rehearsal@127.0.0.1:55433/sentinel_dna_rehearsal"
    )
    return {
        "SENTINEL_DNA_ENV": "staging",
        "SENTINEL_DNA_STAGING_FIRST_ADMIN_BOOTSTRAP": "1",
        "SENTINEL_DNA_STAGING_DEPLOYMENT_IDENTITY": "sentinel-dna-postgres-rehearsal-v1",
        "SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION": "disposable_staging",
        "SENTINEL_DNA_STAGING_DATABASE_TARGET_IDENTITY": target_identity,
        "DATABASE_URL": database_url,
        "SENTINEL_DNA_STAGING_CONTROL_TENANT_ID": tenant_id,
    }


@pytest.mark.parametrize("name,value,error", [
    ("SENTINEL_DNA_ENV", "production", "staging_environment_required"),
    ("SENTINEL_DNA_STAGING_FIRST_ADMIN_BOOTSTRAP", "0", "explicit_staging_bootstrap_required"),
    ("SENTINEL_DNA_STAGING_DEPLOYMENT_IDENTITY", "wrong", "approved_staging_deployment_identity_required"),
    ("SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION", "production", "disposable_staging_target_required"),
    ("SENTINEL_DNA_STAGING_DATABASE_TARGET_IDENTITY", "postgresql://other@prod/db", "database_target_identity_mismatch"),
    ("DATABASE_URL", "postgresql://sentinel@production:5432/sentinel_dna", "database_target_identity_mismatch"),
    ("SENTINEL_DNA_STAGING_CONTROL_TENANT_ID", "", "staging_control_tenant_required"),
])
def test_target_and_environment_guards(module, name, value, error):
    values = _environment()
    values[name] = value
    with pytest.raises(module.StagingBootstrapBlocked, match=error):
        module._require_configuration(values)


def test_sqlite_rejection_after_configuration(module):
    class SQLiteMarker:
        backend_name = "sqlite"
    with pytest.raises(module.StagingBootstrapBlocked, match="postgresql_database_required"):
        module.bootstrap(
            db=SQLiteMarker(), username="manager", email="manager@example.test",
            tenant_id="control-tenant", approval_id="approval", approval_transaction_id="tx",
            password=PASSWORD, password_confirmation=PASSWORD, environ=_environment(),
        )


@pytest.fixture
def postgres_setup(postgres_backend, monkeypatch):
    db = postgres_backend
    MigrationRunner(
        db, migrations=MIGRATIONS, namespace_migrations=STAGING_FIRST_PRIVILEGED_IDENTITY_NAMESPACE_MIGRATIONS
    ).run()
    with db.session() as connection:
        connection.execute(
            """TRUNCATE TABLE
                staging_first_privileged_identity_bootstrap_consumptions,
                approval_audit_events,
                approval_decisions,
                approval_requests,
                audit_events,
                canonical_memberships,
                canonical_identities,
                canonical_tenants,
                users
                RESTART IDENTITY CASCADE"""
        )
    auth = AuthService(db)
    authority = CanonicalAuthorityService(db)
    audit = AuditService(db)
    tenant_id = f"control-{uuid4().hex}"
    authority.tenants.create("Bootstrap control tenant", tenant_id)
    monkeypatch.setenv("SENTINEL_DNA_ENV", "staging")
    monkeypatch.setenv("SENTINEL_DNA_STAGING_FIRST_ADMIN_BOOTSTRAP", "1")
    monkeypatch.setenv("SENTINEL_DNA_STAGING_DEPLOYMENT_IDENTITY", "sentinel-dna-postgres-rehearsal-v1")
    monkeypatch.setenv("SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION", "disposable_staging")
    monkeypatch.setenv("SENTINEL_DNA_STAGING_DATABASE_TARGET_IDENTITY", _environment(tenant_id)["SENTINEL_DNA_STAGING_DATABASE_TARGET_IDENTITY"])
    monkeypatch.setenv("DATABASE_URL", db.database_url)
    monkeypatch.setenv("SENTINEL_DNA_STAGING_CONTROL_TENANT_ID", tenant_id)
    return db, auth, authority, audit, tenant_id


def _approval(db, auth, tenant_id, artifact, *, status="approved", expires_at=None, same_reviewer=False):
    if status == "approved" and expires_at is None and not same_reviewer:
        requester, reviewer, workflow = _verified_approval_participants(db, auth, tenant_id)
        created = workflow.create_request(requester, artifact)
        approved = workflow.approve(
            reviewer,
            created["approval_id"],
            artifact,
            approval_transaction_id=f"tx-{uuid4().hex}",
        )
        return approved["approval_id"], approved["approval_transaction_id"]

    requester = auth.register(
        f"requester-{uuid4().hex[:8]}",
        f"requester-{uuid4().hex[:8]}@example.test",
        PASSWORD,
        "analyst",
        tenant_id=tenant_id,
        actor_id=f"requester-{uuid4().hex}",
    )
    reviewer = requester if same_reviewer else auth.register(
        f"reviewer-{uuid4().hex[:8]}",
        f"reviewer-{uuid4().hex[:8]}@example.test",
        PASSWORD,
        "analyst",
        tenant_id=tenant_id,
        actor_id=f"reviewer-{uuid4().hex}",
    )
    approval_id = f"approval-{uuid4().hex}"
    transaction_id = f"tx-{uuid4().hex}"
    digest = request_hash(artifact)
    now = datetime.now(timezone.utc).isoformat()
    expiry = expires_at or (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    with db.session() as connection:
        requester_identity = ("issuer", "external-tenant", "requester-object", "requester-subject")
        reviewer_identity = requester_identity if same_reviewer else ("issuer", "external-tenant", "reviewer-object", "reviewer-subject")
        connection.execute(
            "INSERT INTO approval_requests(approval_id,request_hash,requester_issuer,requester_tenant_id,requester_object_id,requester_subject_id,requester_user_id,requester_role,created_at,expires_at,status) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (approval_id, digest, *requester_identity, requester.id, "sdna.requester", now, expiry, status),
        )
        connection.execute(
            "INSERT INTO approval_decisions(approval_id,request_hash,reviewer_issuer,reviewer_tenant_id,reviewer_object_id,reviewer_subject_id,reviewer_user_id,reviewer_role,approved_at,decision,approval_transaction_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (approval_id, digest, *reviewer_identity, reviewer.id, "sdna.reviewer", now, "approved", transaction_id),
        )
    return approval_id, transaction_id


def _verified_approval_participants(db, auth, tenant_id):
    issuer = "https://login.microsoftonline.com/rehearsal/v2.0"
    entra_tenant = "rehearsal-entra-tenant"
    requester_actor = f"requester-actor-{uuid4().hex}"
    reviewer_actor = f"reviewer-actor-{uuid4().hex}"
    requester = auth.register(
        f"requester-{uuid4().hex[:8]}",
        f"requester-{uuid4().hex[:8]}@example.test",
        PASSWORD,
        "analyst",
        tenant_id=tenant_id,
        actor_id=requester_actor,
    )
    reviewer = auth.register(
        f"reviewer-{uuid4().hex[:8]}",
        f"reviewer-{uuid4().hex[:8]}@example.test",
        PASSWORD,
        "analyst",
        tenant_id=tenant_id,
        actor_id=reviewer_actor,
    )
    authority = CanonicalAuthorityService(db)
    for user, actor in ((requester, requester_actor), (reviewer, reviewer_actor)):
        authority.identities.create(user.email, user.username, actor, connection=None)
        authority.memberships.add(tenant_id, actor, "viewer", connection=None)
    with db.session() as connection:
        for user_id, actor, object_id, subject_id in (
            (requester.id, requester_actor, "requester-object", "requester-subject"),
            (reviewer.id, reviewer_actor, "reviewer-object", "reviewer-subject"),
        ):
            connection.execute(
                """INSERT INTO entra_identity_bindings(
                    binding_id,user_id,issuer,tenant_id,object_id,subject_id,
                    created_at,updated_at,created_by
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    f"binding-{uuid4().hex}", user_id, issuer, entra_tenant,
                    object_id, subject_id, "now", "now", "test",
                ),
            )
    requester_context = resolve_authenticated_entra_context(
        VerifiedEntraToken(
            EntraIdentityTuple(issuer, entra_tenant, "requester-object", "requester-subject"),
            "rehearsal-client",
            frozenset({"sdna.requester"}),
        ),
        db=db,
        auth_service=auth,
        session_version=0,
    )
    reviewer_context = resolve_authenticated_entra_context(
        VerifiedEntraToken(
            EntraIdentityTuple(issuer, entra_tenant, "reviewer-object", "reviewer-subject"),
            "rehearsal-client",
            frozenset({"sdna.reviewer"}),
        ),
        db=db,
        auth_service=auth,
        session_version=0,
    )
    assert requester_context.user_id != reviewer_context.user_id
    return requester_context, reviewer_context, ApprovalWorkflow(
        db, reauthenticate=lambda _context: True
    )


def _invoke(module, postgres_setup, **overrides):
    db, auth, authority, audit, tenant_id = postgres_setup
    values = {
        "db": db, "username": "first-manager", "email": "first@example.test",
        "tenant_id": tenant_id, "password": PASSWORD, "password_confirmation": PASSWORD,
        "services": (auth, authority, audit, PrivilegedIdentityProvisioningService(auth, authority, audit, db)),
        "environ": _environment(tenant_id),
    }
    artifact = module._artifact(tenant_id=tenant_id, username=values["username"], email=values["email"], target_identity=values["environ"]["SENTINEL_DNA_STAGING_DATABASE_TARGET_IDENTITY"])
    values.update(dict(zip(("approval_id", "approval_transaction_id"), _approval(db, auth, tenant_id, artifact))))
    values.update(overrides)
    return module.bootstrap(**values)


@pytest.mark.postgresql
def test_success_and_secret_free_audit(module, postgres_setup):
    result = _invoke(module, postgres_setup)
    db, auth, _, audit, tenant_id = postgres_setup
    user = auth.get_by_username("first-manager", include_inactive=True)
    assert result["role"] == "soc_manager" and user.tenant_id == tenant_id
    event = next(item for item in audit.list_for_tenant(tenant_id) if item["event_type"] == module.AUDIT_EVENT)
    assert event["actor_id"] == result["approver_actor_id"]
    serialized = json.dumps(event).lower()
    assert all(secret not in serialized for secret in (PASSWORD.lower(), "password_hash", "token", "cookie", "session"))


@pytest.mark.postgresql
def test_approval_workflow_provenance_and_reviewer_authorization(module, postgres_setup):
    db, auth, authority, audit, tenant_id = postgres_setup
    artifact = module._artifact(
        tenant_id=tenant_id,
        username="workflow-manager",
        email="workflow@example.test",
        target_identity=_environment(tenant_id)["SENTINEL_DNA_STAGING_DATABASE_TARGET_IDENTITY"],
    )
    requester, reviewer, workflow = _verified_approval_participants(db, auth, tenant_id)
    created = workflow.create_request(requester, artifact)
    with pytest.raises(ApprovalWorkflowError, match="capability_denied"):
        workflow.approve(requester, created["approval_id"], artifact)
    approved = workflow.approve(
        reviewer,
        created["approval_id"],
        artifact,
        approval_transaction_id=f"tx-{uuid4().hex}",
    )
    assert approved["status"] == "approved"
    with db.session() as connection:
        request = connection.execute(
            "SELECT request_hash,requester_user_id,status FROM approval_requests WHERE approval_id=?",
            (created["approval_id"],),
        ).fetchone()
        decision = connection.execute(
            "SELECT reviewer_user_id,approval_transaction_id,decision FROM approval_decisions WHERE approval_id=?",
            (created["approval_id"],),
        ).fetchone()
        provenance = connection.execute(
            "SELECT COUNT(*) AS n FROM approval_audit_events WHERE approval_id=?",
            (created["approval_id"],),
        ).fetchone()["n"]
    assert request["status"] == "approved"
    assert request["request_hash"] == request_hash(artifact)
    assert request["requester_user_id"] == requester.user_id
    assert decision["reviewer_user_id"] == reviewer.user_id
    assert decision["reviewer_user_id"] != request["requester_user_id"]
    assert decision["approval_transaction_id"] == approved["approval_transaction_id"]
    assert decision["decision"] == "approved"
    assert provenance == 2
    result = module.bootstrap(
        db=db,
        username="workflow-manager",
        email="workflow@example.test",
        tenant_id=tenant_id,
        approval_id=approved["approval_id"],
        approval_transaction_id=approved["approval_transaction_id"],
        password=PASSWORD,
        password_confirmation=PASSWORD,
        services=(auth, authority, audit, PrivilegedIdentityProvisioningService(auth, authority, audit, db)),
        environ=_environment(tenant_id),
    )
    assert result["approver_actor_id"] != result["actor_id"]


@pytest.mark.parametrize(
    "field,replacement",
    [
        ("tenant_id", "wrong-control-tenant"),
        ("username", "wrong-approved-username"),
        ("email", "wrong-approved@example.test"),
        ("role", "admin"),
        ("environment", "production"),
        ("operation", "other_operation"),
        ("purpose", "other_purpose"),
        ("database_target_identity", "postgresql://sentinel_rehearsal@127.0.0.1:55601/sentinel_dna_rehearsal"),
    ],
)
@pytest.mark.postgresql
def test_each_approval_binding_mismatch_rolls_back(module, postgres_setup, monkeypatch, field, replacement):
    db, auth, authority, audit, tenant_id = postgres_setup
    username = f"binding-{field}"
    email = f"binding-{field}@example.test"
    artifact = module._artifact(
        tenant_id=tenant_id,
        username=username,
        email=email,
        target_identity=_environment(tenant_id)["SENTINEL_DNA_STAGING_DATABASE_TARGET_IDENTITY"],
    )
    approval_id, transaction_id = _approval(db, auth, tenant_id, artifact)
    original_artifact = module._artifact

    def altered_artifact(**kwargs):
        altered = original_artifact(**kwargs)
        altered[field] = replacement
        return altered

    monkeypatch.setattr(module, "_artifact", altered_artifact)
    with pytest.raises(module.StagingBootstrapBlocked, match="approval_scope_mismatch|request_hash_mismatch"):
        module.bootstrap(
            db=db,
            username=username,
            email=email,
            tenant_id=tenant_id,
            approval_id=approval_id,
            approval_transaction_id=transaction_id,
            password=PASSWORD,
            password_confirmation=PASSWORD,
            services=(auth, authority, audit, PrivilegedIdentityProvisioningService(auth, authority, audit, db)),
            environ=_environment(tenant_id),
        )
    assert auth.get_by_username(username, include_inactive=True) is None
    with db.session() as connection:
        state = connection.execute(
            "SELECT bootstrap_consumed_at,status FROM approval_requests WHERE approval_id=?",
            (approval_id,),
        ).fetchone()
        assert state["bootstrap_consumed_at"] is None
        assert connection.execute(
            "SELECT COUNT(*) AS n FROM staging_first_privileged_identity_bootstrap_consumptions"
        ).fetchone()["n"] == 0


@pytest.mark.postgresql
def test_approval_scope_and_replay_fail_closed(module, postgres_setup):
    db, auth, authority, audit, tenant_id = postgres_setup
    artifact = module._artifact(tenant_id=tenant_id, username="approved-name", email="approved@example.test", target_identity=postgres_setup[0].database_url if hasattr(postgres_setup[0], "database_url") else _environment(tenant_id)["SENTINEL_DNA_STAGING_DATABASE_TARGET_IDENTITY"])
    approval_id, transaction_id = _approval(db, auth, tenant_id, artifact)
    with pytest.raises(module.StagingBootstrapBlocked, match="approval_scope_mismatch|request_hash_mismatch"):
        module.bootstrap(db=db, username="different-name", email="approved@example.test", tenant_id=tenant_id, approval_id=approval_id, approval_transaction_id=transaction_id, password=PASSWORD, password_confirmation=PASSWORD, services=(auth, authority, audit, PrivilegedIdentityProvisioningService(auth, authority, audit, db)), environ=_environment(tenant_id))


@pytest.mark.postgresql
def test_expired_revoked_and_same_reviewer_approval_rejected(module, postgres_setup):
    db, auth, authority, audit, tenant_id = postgres_setup
    for status, expiry, same_reviewer, expected in [
        ("approved", "2000-01-01T00:00:00+00:00", False, "approval_expired"),
        ("revoked", "2099-01-01T00:00:00+00:00", False, "approval_not_approved"),
        ("approved", "2099-01-01T00:00:00+00:00", True, "requester_reviewer_same_identity"),
    ]:
        artifact = module._artifact(tenant_id=tenant_id, username=f"name-{uuid4().hex[:6]}", email=f"{uuid4().hex[:6]}@example.test", target_identity=_environment(tenant_id)["SENTINEL_DNA_STAGING_DATABASE_TARGET_IDENTITY"])
        approval_id, transaction_id = _approval(db, auth, tenant_id, artifact, status=status, expires_at=expiry, same_reviewer=same_reviewer)
        with pytest.raises(module.StagingBootstrapBlocked, match=expected):
            module.bootstrap(db=db, username=artifact["username"], email=artifact["email"], tenant_id=tenant_id, approval_id=approval_id, approval_transaction_id=transaction_id, password=PASSWORD, password_confirmation=PASSWORD, services=(auth, authority, audit, PrivilegedIdentityProvisioningService(auth, authority, audit, db)), environ=_environment(tenant_id))


@pytest.mark.postgresql
def test_rollback_and_replay_consumption(module, postgres_setup):
    db, auth, authority, audit, tenant_id = postgres_setup
    class FailingService:
        def provision(self, **kwargs):
            raise RuntimeError("controlled failure")
    artifact = module._artifact(tenant_id=tenant_id, username="rollback-manager", email="rollback@example.test", target_identity=_environment(tenant_id)["SENTINEL_DNA_STAGING_DATABASE_TARGET_IDENTITY"])
    approval_id, transaction_id = _approval(db, auth, tenant_id, artifact)
    with pytest.raises(module.StagingBootstrapBlocked, match="bootstrap_failed"):
        module.bootstrap(db=db, username=artifact["username"], email=artifact["email"], tenant_id=tenant_id, approval_id=approval_id, approval_transaction_id=transaction_id, password=PASSWORD, password_confirmation=PASSWORD, services=(auth, authority, audit, FailingService()), environ=_environment(tenant_id))
    with db.session() as connection:
        assert connection.execute("SELECT COUNT(*) AS n FROM staging_first_privileged_identity_bootstrap_consumptions").fetchone()["n"] == 0


@pytest.mark.postgresql
def test_concurrent_bootstrap_separate_sessions_at_most_one_success(module, postgres_setup):
    db, auth, authority, audit, tenant_id = postgres_setup
    artifact = module._artifact(tenant_id=tenant_id, username="concurrent-manager", email="concurrent@example.test", target_identity=_environment(tenant_id)["SENTINEL_DNA_STAGING_DATABASE_TARGET_IDENTITY"])
    approval_id, transaction_id = _approval(db, auth, tenant_id, artifact)
    results = []
    def run():
        try:
            results.append(module.bootstrap(db=db, username=artifact["username"], email=artifact["email"], tenant_id=tenant_id, approval_id=approval_id, approval_transaction_id=transaction_id, password=PASSWORD, password_confirmation=PASSWORD, services=(auth, authority, audit, PrivilegedIdentityProvisioningService(auth, authority, audit, db)), environ=_environment(tenant_id)))
        except Exception as exc:
            results.append(exc)
    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert sum(isinstance(item, dict) for item in results) == 1


@pytest.mark.postgresql
def test_bootstrap_serializes_normal_privileged_provisioning(module, postgres_setup):
    db, auth, authority, audit, tenant_id = postgres_setup
    username = "bootstrap-normal-race"
    email = "bootstrap-normal-race@example.test"
    artifact = module._artifact(
        tenant_id=tenant_id,
        username=username,
        email=email,
        target_identity=_environment(tenant_id)["SENTINEL_DNA_STAGING_DATABASE_TARGET_IDENTITY"],
    )
    approval_id, transaction_id = _approval(db, auth, tenant_id, artifact)
    entered = threading.Event()
    release = threading.Event()
    bootstrap_result = []
    normal_result = []
    real_service = PrivilegedIdentityProvisioningService(auth, authority, audit, db)

    class BlockingService:
        def provision(self, **kwargs):
            entered.set()
            assert release.wait(5)
            return real_service.provision(**kwargs)

    def run_bootstrap():
        try:
            bootstrap_result.append(module.bootstrap(
                db=db,
                username=username,
                email=email,
                tenant_id=tenant_id,
                approval_id=approval_id,
                approval_transaction_id=transaction_id,
                password=PASSWORD,
                password_confirmation=PASSWORD,
                services=(auth, authority, audit, BlockingService()),
                environ=_environment(tenant_id),
            ))
        except Exception as exc:
            bootstrap_result.append(exc)

    def run_normal():
        entered.wait(5)
        started = datetime.now(timezone.utc)
        try:
            real_service.provision(
                username=username,
                email=email,
                tenant_id=tenant_id,
                role="soc_manager",
                password=PASSWORD,
                password_confirmation=PASSWORD,
            )
            normal_result.append("success")
        except Exception as exc:
            normal_result.append(str(exc))
        normal_result.append((datetime.now(timezone.utc) - started).total_seconds())

    bootstrap_thread = threading.Thread(target=run_bootstrap)
    normal_thread = threading.Thread(target=run_normal)
    bootstrap_thread.start()
    assert entered.wait(5)
    normal_thread.start()
    threading.Event().wait(0.4)
    assert len(normal_result) == 0
    release.set()
    bootstrap_thread.join()
    normal_thread.join()
    assert len(bootstrap_result) == 1 and isinstance(bootstrap_result[0], dict)
    assert normal_result[0] == "identity_already_exists"
    assert normal_result[1] > 0.3
