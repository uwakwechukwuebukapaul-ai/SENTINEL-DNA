"""Explicit staging-only schema for the local two-human ceremony."""

from __future__ import annotations

VERSION = 13
NAMESPACE = "staging"
DESCRIPTION = "Local two-human staging authority ceremony"


def _require_staging(connection) -> None:
    import os

    if os.environ.get("SENTINEL_DNA_ENV", "").strip().lower() != "staging":
        raise RuntimeError("local_two_human_ceremony_requires_staging")


def upgrade(connection) -> None:
    _require_staging(connection)
    backend = getattr(connection, "backend_name", "sqlite")
    integer_type = "BIGINT" if backend == "postgresql" else "INTEGER"
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS staging_two_human_ceremonies (
            ceremony_id TEXT PRIMARY KEY,
            status TEXT NOT NULL CHECK(status IN (
                'REQUESTED','REQUESTER_APPROVED','REVIEWER_APPROVED',
                'FINALIZED','EXPIRED','CANCELLED'
            )),
            authority_id TEXT NOT NULL,
            control_tenant_id TEXT NOT NULL,
            approval_transaction_id TEXT NOT NULL UNIQUE,
            nonce TEXT NOT NULL UNIQUE,
            nonce_hash TEXT NOT NULL UNIQUE CHECK(length(nonce_hash) = 64),
            environment TEXT NOT NULL CHECK(environment = 'staging'),
            database_target_identity TEXT NOT NULL,
            application_commit TEXT NOT NULL,
            repository_tree TEXT NOT NULL,
            image_digest TEXT NOT NULL,
            issued_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            artifact_hash TEXT UNIQUE,
            requester_user_id %s NOT NULL,
            requester_actor_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            finalized_at TEXT
        )
        """ % integer_type
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS staging_two_human_approvals (
            approval_id TEXT PRIMARY KEY,
            ceremony_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('requester','reviewer')),
            human_user_id %s NOT NULL,
            actor_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            provider_subject TEXT NOT NULL,
            credential_id TEXT NOT NULL,
            mfa_session_reference_hash TEXT NOT NULL CHECK(length(mfa_session_reference_hash) = 64),
            key_id TEXT NOT NULL,
            public_key TEXT NOT NULL,
            public_key_fingerprint TEXT NOT NULL CHECK(length(public_key_fingerprint) = 64),
            signature TEXT NOT NULL,
            release_binding_hash TEXT NOT NULL CHECK(length(release_binding_hash) = 64),
            approved_at TEXT NOT NULL,
            result TEXT NOT NULL CHECK(result = 'APPROVED'),
            FOREIGN KEY(ceremony_id) REFERENCES staging_two_human_ceremonies(ceremony_id),
            UNIQUE(ceremony_id, role),
            UNIQUE(ceremony_id, human_user_id),
            UNIQUE(ceremony_id, actor_id),
            UNIQUE(ceremony_id, provider_subject),
            UNIQUE(ceremony_id, credential_id),
            UNIQUE(ceremony_id, mfa_session_reference_hash),
            UNIQUE(ceremony_id, key_id),
            UNIQUE(ceremony_id, public_key_fingerprint)
        )
        """ % integer_type
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_two_human_ceremony_status "
        "ON staging_two_human_ceremonies(status, expires_at)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_two_human_approval_ceremony "
        "ON staging_two_human_approvals(ceremony_id, role)"
    )
