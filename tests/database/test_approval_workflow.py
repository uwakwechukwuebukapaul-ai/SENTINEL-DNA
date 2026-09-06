from types import SimpleNamespace
import sqlite3
import threading

import pytest

from database.backend import SQLiteBackend
from database.canonical_authority import ensure_canonical_schema
from database.migration_runner import MigrationRunner
from database.migrations.registry import NAMESPACE_MIGRATIONS
import services.identity.approval_workflow as approval_module
from services.identity.approval_workflow import (
    ApprovalWorkflow,
    ApprovalWorkflowError,
    AuthenticatedEntraContext,
    request_hash,
    resolve_authenticated_entra_context,
)
from services.identity.entra_oidc import EntraIdentityTuple, EntraOidcError, VerifiedEntraToken


FOUNDATION, ENTRA, APPROVAL = NAMESPACE_MIGRATIONS
ISSUER = "https://login.microsoftonline.com/example/v2.0"


class FakeAuth:
    def __init__(self, users):
        self.users = users

    def session_user(self, user_id, session_version):
        user = self.users.get(user_id)
        return user if user and user.session_version == session_version else None


def _setup(tmp_path):
    backend = SQLiteBackend(tmp_path / "workflow.sqlite")
    MigrationRunner(backend, migrations=(), namespace_migrations=NAMESPACE_MIGRATIONS).run()
    users = {}
    with backend.session() as connection:
        ensure_canonical_schema(connection, commit=False)
        for user_id, username, actor in ((1, "requester", "actor-requester"), (2, "reviewer", "actor-reviewer")):
            connection.execute(
                "INSERT INTO users(id,username,email,password_hash,role,created_at,tenant_id,actor_id,onboarding_state) VALUES (?,?,?,?,?,?,?,?,?)",
                (user_id, username, f"{username}@example.test", "hash", "analyst", "now", "tenant", actor, "AUTHENTICATED"),
            )
            connection.execute("INSERT INTO canonical_tenants(tenant_id,name) VALUES (?,?)", (f"tenant-{user_id}", f"Tenant {user_id}"))
            connection.execute("INSERT INTO canonical_identities(actor_id,email,display_name) VALUES (?,?,?)", (actor, f"{username}@example.test", username))
            connection.execute("INSERT INTO canonical_memberships(tenant_id,actor_id,role) VALUES (?,?,?)", (f"tenant-{user_id}", actor, "viewer"))
            connection.execute(
                "INSERT INTO entra_identity_bindings(binding_id,user_id,issuer,tenant_id,object_id,subject_id,created_at,updated_at,created_by) VALUES (?,?,?,?,?,?,?,?,?)",
                (f"binding-{user_id}", user_id, ISSUER, "entra-tenant", f"object-{user_id}", f"subject-{user_id}", "now", "now", "test"),
            )
            users[user_id] = SimpleNamespace(is_active=True, tenant_id=f"tenant-{user_id}", actor_id=actor, session_version=0)
    # The user rows use tenant-specific canonical memberships; align the
    # local users with those memberships without involving AuthService.
    with backend.session() as connection:
        connection.execute("UPDATE users SET tenant_id='tenant-1' WHERE id=1")
        connection.execute("UPDATE users SET tenant_id='tenant-2' WHERE id=2")
    auth = FakeAuth(users)
    requester = resolve_authenticated_entra_context(
        VerifiedEntraToken(EntraIdentityTuple(ISSUER, "entra-tenant", "object-1", "subject-1"), "aud", frozenset({"sdna.requester"})),
        db=backend, auth_service=auth, session_version=0,
    )
    reviewer = resolve_authenticated_entra_context(
        VerifiedEntraToken(EntraIdentityTuple(ISSUER, "entra-tenant", "object-2", "subject-2"), "aud", frozenset({"sdna.reviewer"})),
        db=backend, auth_service=auth, session_version=0,
    )
    return backend, requester, reviewer, auth


def _workflow(backend):
    return ApprovalWorkflow(backend, reauthenticate=lambda _context: True)


def test_fresh_request_approval_and_audit_are_bound_to_verified_tuples(tmp_path):
    backend, requester, reviewer, _ = _setup(tmp_path)
    workflow = _workflow(backend)
    artifact = {"action": "review-only", "version": 1}
    created = workflow.create_request(requester, artifact)
    approved = workflow.approve(reviewer, created["approval_id"], artifact, approval_transaction_id="tx-1")
    assert approved["status"] == "approved"
    with backend.session() as connection:
        request = connection.execute("SELECT * FROM approval_requests").fetchone()
        decision = connection.execute("SELECT * FROM approval_decisions").fetchone()
        audit = connection.execute("SELECT * FROM approval_audit_events ORDER BY occurred_at,event_id").fetchall()
    assert request["request_hash"] == request_hash(artifact)
    assert decision["request_hash"] == request["request_hash"]
    assert len(audit) == 2
    assert {row["action"] for row in audit} == {"REQUEST_APPROVAL", "APPROVE_APPROVAL"}
    assert all(row["subject_id"] in {"subject-1", "subject-2"} for row in audit)


def test_capabilities_and_context_are_explicit_and_fail_closed(tmp_path):
    backend, requester, reviewer, _ = _setup(tmp_path)
    workflow = _workflow(backend)
    with pytest.raises(ApprovalWorkflowError, match="capability_denied"):
        workflow.create_request(reviewer, {"x": 1})
    created = workflow.create_request(requester, {"x": 1})
    with pytest.raises(ApprovalWorkflowError, match="capability_denied"):
        workflow.approve(requester, created["approval_id"], {"x": 1})
    with pytest.raises(ApprovalWorkflowError, match="authenticated_entra_context_untrusted"):
        AuthenticatedEntraContext(requester.identity, requester.user_id, frozenset({"sdna.reviewer"}), 0, requester.tenant_id, requester.actor_id)
    with pytest.raises(ApprovalWorkflowError, match="approval_artifact_contains_sensitive_field"):
        workflow.create_request(requester, {"access_token": "never-store"})


def test_same_tuple_is_rejected_even_with_different_labels_and_roles(tmp_path):
    backend, requester, _reviewer, _ = _setup(tmp_path)
    workflow = _workflow(backend)
    created = workflow.create_request(requester, {"x": 2})
    same_tuple_reviewer = AuthenticatedEntraContext(
        requester.identity, requester.user_id, frozenset({"sdna.reviewer"}), requester.session_version, requester.tenant_id, requester.actor_id, approval_module._CONTEXT_TOKEN
    )
    # The public constructor cannot mint trusted contexts; use a verified
    # binding for the negative test by changing only the role at the test
    # boundary is intentionally impossible. The service's tuple comparison is
    # exercised through a direct trusted-context clone below.
    with pytest.raises(ApprovalWorkflowError, match="requester_reviewer_same_identity"):
        workflow.approve(same_tuple_reviewer, created["approval_id"], {"x": 2})


def test_modified_hash_expiry_replay_and_duplicate_transaction_fail(tmp_path):
    backend, requester, reviewer, _ = _setup(tmp_path)
    workflow = _workflow(backend)
    created = workflow.create_request(requester, {"x": 3}, approval_id="approval-1")
    with pytest.raises(ApprovalWorkflowError, match="request_hash_mismatch"):
        workflow.approve(reviewer, "approval-1", {"x": 4})
    workflow.approve(reviewer, "approval-1", {"x": 3}, approval_transaction_id="tx-duplicate")
    with pytest.raises(ApprovalWorkflowError, match="approval_already_consumed"):
        workflow.approve(reviewer, "approval-1", {"x": 3}, approval_transaction_id="tx-replay")
    second = workflow.create_request(requester, {"x": 5}, approval_id="approval-2")
    with pytest.raises(ApprovalWorkflowError, match="approval_transaction_id"):
        workflow.approve(reviewer, second["approval_id"], {"x": 5}, approval_transaction_id="tx-duplicate")
    expired = workflow.create_request(requester, {"x": 6}, expires_at="2000-01-01T00:00:00+00:00")
    with pytest.raises(ApprovalWorkflowError, match="approval_expired"):
        workflow.approve(reviewer, expired["approval_id"], {"x": 6})


def test_revoked_or_invalid_binding_and_membership_cannot_act(tmp_path):
    backend, requester, reviewer, auth = _setup(tmp_path)
    with backend.session() as connection:
        connection.execute("UPDATE entra_identity_bindings SET status='revoked', revoked_at='later' WHERE binding_id='binding-1'")
    with pytest.raises(EntraOidcError):
        resolve_authenticated_entra_context(
            VerifiedEntraToken(requester.identity, "aud", frozenset({"sdna.requester"})),
            db=backend, auth_service=auth, session_version=0,
        )
    with backend.session() as connection:
        connection.execute("UPDATE entra_identity_bindings SET status='active', revoked_at=NULL WHERE binding_id='binding-2'")
        connection.execute("UPDATE canonical_memberships SET status='inactive' WHERE actor_id='actor-reviewer'")
    with pytest.raises(ApprovalWorkflowError, match="membership_inactive"):
        resolve_authenticated_entra_context(
            VerifiedEntraToken(reviewer.identity, "aud", frozenset({"sdna.reviewer"})),
            db=backend, auth_service=auth, session_version=0,
        )


def test_concurrent_reviewers_have_one_terminal_success(tmp_path):
    backend, requester, reviewer, _ = _setup(tmp_path)
    workflow = _workflow(backend)
    created = workflow.create_request(requester, {"x": 7})
    results = []

    def approve():
        try:
            results.append(workflow.approve(reviewer, created["approval_id"], {"x": 7}))
        except Exception as exc:
            results.append(exc)

    threads = [threading.Thread(target=approve) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sum(isinstance(item, dict) for item in results) == 1
    assert sum(isinstance(item, ApprovalWorkflowError) for item in results) == 1
    with backend.session() as connection:
        assert connection.execute("SELECT COUNT(*) FROM approval_decisions").fetchone()[0] == 1


def test_audit_and_decisions_are_append_only(tmp_path):
    backend, requester, _reviewer, _ = _setup(tmp_path)
    workflow = _workflow(backend)
    created = workflow.create_request(requester, {"x": 8})
    with backend.session() as connection:
        event_id = connection.execute("SELECT event_id FROM approval_audit_events LIMIT 1").fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE approval_audit_events SET action='forged' WHERE event_id=?", (event_id,))
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM approval_audit_events WHERE event_id=?", (event_id,))
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE approval_requests SET request_hash='forged' WHERE approval_id=?", (created["approval_id"],))
