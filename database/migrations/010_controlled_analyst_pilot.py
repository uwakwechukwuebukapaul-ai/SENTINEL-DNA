"""Durable, append-only controlled analyst pilot workflow overlay.

This migration is intentionally opt-in.  The core and Gate 4 migration
chains remain unchanged; staging/development can compose this overlay when
the controlled analyst pilot application surface is enabled.
"""

from __future__ import annotations

VERSION = 10
DESCRIPTION = "Controlled analyst pilot tenant, feedback, review, and audit overlay"


def upgrade(connection) -> None:
    from database.portability import append_only_statements

    statements = (
        """CREATE TABLE IF NOT EXISTS controlled_pilot_tenant_events (
            event_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            manager_tenant_id TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('onboarded','suspended','resumed','revoked')),
            display_name TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            provisioning_id TEXT NOT NULL,
            analyst_id TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            sequence_number INTEGER NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS controlled_pilot_membership_events (
            event_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role = 'analyst'),
            action TEXT NOT NULL CHECK(action IN ('added','revoked')),
            source_event_id TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            sequence_number INTEGER NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS controlled_pilot_feedback (
            feedback_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            analyst_id TEXT NOT NULL,
            case_id TEXT NOT NULL,
            investigation_id TEXT NOT NULL,
            decision TEXT NOT NULL CHECK(decision IN ('accepted','rejected','modified','false_positive','escalated','needs_more_evidence')),
            helpful_rating INTEGER NOT NULL CHECK(helpful_rating BETWEEN 1 AND 5),
            confidence_rating INTEGER NOT NULL CHECK(confidence_rating BETWEEN 1 AND 5),
            estimated_time_saved REAL NOT NULL CHECK(estimated_time_saved >= 0 AND estimated_time_saved <= 10080),
            comments TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            sequence_number INTEGER NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS controlled_pilot_review_events (
            event_id TEXT PRIMARY KEY,
            review_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            case_id TEXT NOT NULL,
            investigation_id TEXT NOT NULL,
            analyst_id TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('submitted','accepted','rejected','needs_more_evidence','reopened','withdrawn')),
            decision TEXT NOT NULL,
            comments TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            sequence_number INTEGER NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS controlled_pilot_audit_events (
            audit_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            details_json TEXT NOT NULL,
            previous_hash TEXT,
            event_hash TEXT NOT NULL UNIQUE,
            occurred_at TEXT NOT NULL,
            sequence_number INTEGER NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_controlled_pilot_tenant_events_tenant ON controlled_pilot_tenant_events(tenant_id, sequence_number, event_id)",
        "CREATE INDEX IF NOT EXISTS idx_controlled_pilot_membership_events_tenant ON controlled_pilot_membership_events(tenant_id, actor_id, sequence_number, event_id)",
        "CREATE INDEX IF NOT EXISTS idx_controlled_pilot_feedback_tenant ON controlled_pilot_feedback(tenant_id, sequence_number, feedback_id)",
        "CREATE INDEX IF NOT EXISTS idx_controlled_pilot_review_events_tenant ON controlled_pilot_review_events(tenant_id, review_id, sequence_number, event_id)",
        "CREATE INDEX IF NOT EXISTS idx_controlled_pilot_audit_tenant ON controlled_pilot_audit_events(tenant_id, sequence_number, audit_id)",
    )
    for statement in statements:
        connection.execute(statement)

    for table, prefix in (
        ("controlled_pilot_tenant_events", "controlled_pilot_tenant_events_append_only"),
        ("controlled_pilot_membership_events", "controlled_pilot_membership_events_append_only"),
        ("controlled_pilot_feedback", "controlled_pilot_feedback_append_only"),
        ("controlled_pilot_review_events", "controlled_pilot_review_events_append_only"),
        ("controlled_pilot_audit_events", "controlled_pilot_audit_events_append_only"),
    ):
        for statement in append_only_statements(
            getattr(connection, "backend_name", "sqlite"),
            table_name=table,
            trigger_prefix=prefix,
            error_message=f"{table}_are_append_only",
        ):
            connection.execute(statement)
