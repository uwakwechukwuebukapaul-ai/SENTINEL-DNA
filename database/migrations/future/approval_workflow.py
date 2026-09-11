"""Persistence for the requester/reviewer approval workflow."""

from __future__ import annotations

from typing import Any

from database.migrations.registry import MigrationRef


NAMESPACE = "future"
MIGRATION_KEY = "approval_workflow"
DESCRIPTION = "Requester and reviewer approval workflow"
PREREQUISITES = (MigrationRef("future", "entra_identity_bindings"),)


def _backend_name(connection: Any) -> str:
    return getattr(connection, "backend_name", "sqlite")


def upgrade(connection: Any) -> None:
    user_id_type = "BIGINT" if _backend_name(connection) == "postgresql" else "INTEGER"
    connection.execute(
        f"""CREATE TABLE IF NOT EXISTS approval_requests (
            approval_id TEXT PRIMARY KEY,
            request_hash TEXT NOT NULL,
            requester_issuer TEXT NOT NULL,
            requester_tenant_id TEXT NOT NULL,
            requester_object_id TEXT NOT NULL,
            requester_subject_id TEXT NOT NULL,
            requester_user_id {user_id_type} NOT NULL,
            requester_role TEXT NOT NULL CHECK(requester_role = 'sdna.requester'),
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending', 'approved', 'rejected', 'expired', 'revoked')),
            consumed_at TEXT,
            FOREIGN KEY(requester_user_id) REFERENCES users(id),
            UNIQUE(approval_id, request_hash)
        )"""
    )
    connection.execute(
        f"""CREATE TABLE IF NOT EXISTS approval_decisions (
            approval_id TEXT PRIMARY KEY,
            request_hash TEXT NOT NULL,
            reviewer_issuer TEXT NOT NULL,
            reviewer_tenant_id TEXT NOT NULL,
            reviewer_object_id TEXT NOT NULL,
            reviewer_subject_id TEXT NOT NULL,
            reviewer_user_id {user_id_type} NOT NULL,
            reviewer_role TEXT NOT NULL CHECK(reviewer_role = 'sdna.reviewer'),
            approved_at TEXT NOT NULL,
            decision TEXT NOT NULL CHECK(decision IN ('approved', 'rejected')),
            approval_transaction_id TEXT NOT NULL UNIQUE,
            FOREIGN KEY(approval_id, request_hash)
                REFERENCES approval_requests(approval_id, request_hash),
            FOREIGN KEY(reviewer_user_id) REFERENCES users(id)
        )"""
    )
    audit_user_id_type = "BIGINT" if _backend_name(connection) == "postgresql" else "INTEGER"
    connection.execute(
        f"""CREATE TABLE IF NOT EXISTS approval_audit_events (
            event_id TEXT PRIMARY KEY,
            approval_id TEXT NOT NULL,
            request_hash TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            issuer TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            object_id TEXT NOT NULL,
            user_id {audit_user_id_type} NOT NULL,
            role TEXT NOT NULL,
            action TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            transaction_id TEXT NOT NULL,
            previous_status TEXT NOT NULL,
            new_status TEXT NOT NULL,
            FOREIGN KEY(approval_id, request_hash)
                REFERENCES approval_requests(approval_id, request_hash)
        )"""
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_approval_requests_requester "
        "ON approval_requests(requester_user_id, created_at)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_approval_audit_approval "
        "ON approval_audit_events(approval_id, occurred_at)"
    )
    if _backend_name(connection) == "postgresql":
        connection.execute(
            """CREATE OR REPLACE FUNCTION approval_request_integrity_guard() RETURNS trigger
               LANGUAGE plpgsql AS $$
               BEGIN
                   IF NEW.approval_id <> OLD.approval_id OR NEW.request_hash <> OLD.request_hash
                      OR NEW.requester_user_id <> OLD.requester_user_id
                      OR NEW.requester_issuer <> OLD.requester_issuer
                      OR NEW.requester_tenant_id <> OLD.requester_tenant_id
                      OR NEW.requester_object_id <> OLD.requester_object_id
                      OR NEW.requester_subject_id <> OLD.requester_subject_id
                      OR NEW.requester_role <> OLD.requester_role
                      OR (OLD.status <> 'pending' AND NEW.status <> OLD.status)
                      OR (OLD.status = 'pending' AND NEW.status NOT IN ('pending','approved','rejected','expired','revoked')) THEN
                       RAISE EXCEPTION 'approval_request_immutable_or_invalid_transition';
                   END IF;
                   RETURN NEW;
               END; $$"""
        )
        connection.execute("DROP TRIGGER IF EXISTS approval_request_integrity_guard ON approval_requests")
        connection.execute(
            """CREATE TRIGGER approval_request_integrity_guard
               BEFORE UPDATE ON approval_requests
               FOR EACH ROW EXECUTE FUNCTION approval_request_integrity_guard()"""
        )
    else:
        connection.execute(
            """CREATE TRIGGER IF NOT EXISTS approval_request_integrity_guard
               BEFORE UPDATE ON approval_requests
               WHEN NEW.approval_id <> OLD.approval_id OR NEW.request_hash <> OLD.request_hash
                 OR NEW.requester_user_id <> OLD.requester_user_id
                 OR NEW.requester_issuer <> OLD.requester_issuer
                 OR NEW.requester_tenant_id <> OLD.requester_tenant_id
                 OR NEW.requester_object_id <> OLD.requester_object_id
                 OR NEW.requester_subject_id <> OLD.requester_subject_id
                 OR NEW.requester_role <> OLD.requester_role
                 OR (OLD.status <> 'pending' AND NEW.status <> OLD.status)
                 OR (OLD.status = 'pending' AND NEW.status NOT IN ('pending','approved','rejected','expired','revoked'))
               BEGIN SELECT RAISE(ABORT, 'approval_request_immutable_or_invalid_transition'); END"""
        )
    if _backend_name(connection) == "postgresql":
        connection.execute(
            """CREATE OR REPLACE FUNCTION approval_audit_append_only_guard() RETURNS trigger
               LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'approval_audit_events_are_append_only'; END; $$"""
        )
        connection.execute("DROP TRIGGER IF EXISTS approval_audit_append_only ON approval_audit_events")
        connection.execute("DROP TRIGGER IF EXISTS approval_decision_append_only ON approval_decisions")
        connection.execute(
            """CREATE TRIGGER approval_audit_append_only
               BEFORE UPDATE OR DELETE ON approval_audit_events
               FOR EACH ROW EXECUTE FUNCTION approval_audit_append_only_guard()"""
        )
        connection.execute(
            """CREATE TRIGGER approval_decision_append_only
               BEFORE UPDATE OR DELETE ON approval_decisions
               FOR EACH ROW EXECUTE FUNCTION approval_audit_append_only_guard()"""
        )
    else:
        connection.execute(
            """CREATE TRIGGER IF NOT EXISTS approval_audit_no_update
               BEFORE UPDATE ON approval_audit_events
               BEGIN SELECT RAISE(ABORT, 'approval_audit_events_are_append_only'); END"""
        )
        connection.execute(
            """CREATE TRIGGER IF NOT EXISTS approval_audit_no_delete
               BEFORE DELETE ON approval_audit_events
               BEGIN SELECT RAISE(ABORT, 'approval_audit_events_are_append_only'); END"""
        )
        connection.execute(
            """CREATE TRIGGER IF NOT EXISTS approval_decision_no_update
               BEFORE UPDATE ON approval_decisions
               BEGIN SELECT RAISE(ABORT, 'approval_decisions_are_append_only'); END"""
        )
        connection.execute(
            """CREATE TRIGGER IF NOT EXISTS approval_decision_no_delete
               BEFORE DELETE ON approval_decisions
               BEGIN SELECT RAISE(ABORT, 'approval_decisions_are_append_only'); END"""
        )
