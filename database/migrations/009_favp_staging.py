"""Create the disposable, staging-only FAVP schema and catalogs.

This migration is deliberately not part of ``database.migration_runner``'s
default production chain. It is selected only by the staging migration
entrypoint, after the core migrations have completed.
"""

from __future__ import annotations

import json

VERSION = 9
DESCRIPTION = "Disposable staging FAVP operations and execution schema"


def _catalog_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def upgrade(connection) -> None:
    from database.portability import append_only_statements, identity_primary_key, table_columns
    from services.favp_operations.execution_scenarios import FAVP_EXECUTION_SCENARIOS
    from services.favp_operations.scenarios import FAVP_SCENARIOS

    identity = identity_primary_key(getattr(connection, "backend_name", "sqlite"))
    statements = (
        f"""CREATE TABLE IF NOT EXISTS audit_events (
            id {identity}, event_type TEXT NOT NULL, case_id TEXT, user_id INTEGER,
            details_json TEXT NOT NULL, created_at TEXT NOT NULL,
            event_id TEXT, tenant_id TEXT, actor_id TEXT, correlation_id TEXT,
            request_id TEXT, resource_type TEXT, resource_id TEXT, operation TEXT,
            outcome TEXT, latency_ms REAL, sequence_number INTEGER,
            schema_version TEXT NOT NULL DEFAULT 'audit-event-v1'
        )""",
        """CREATE TABLE IF NOT EXISTS favp_organizations (
            organization_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            organization_ref TEXT NOT NULL, display_name TEXT NOT NULL,
            sector TEXT, size_band TEXT, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, UNIQUE(tenant_id, organization_ref)
        )""",
        """CREATE TABLE IF NOT EXISTS favp_participants (
            participant_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            organization_id TEXT NOT NULL, participant_ref TEXT NOT NULL,
            display_name TEXT NOT NULL, actor_identity_ref TEXT,
            role_title TEXT, contact_reference TEXT, state TEXT NOT NULL,
            nda_status TEXT NOT NULL, terms_status TEXT NOT NULL,
            onboarding_status TEXT NOT NULL, access_status TEXT NOT NULL,
            validation_phase TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, completed_at TEXT,
            UNIQUE(tenant_id, participant_ref)
        )""",
        """CREATE TABLE IF NOT EXISTS favp_invitations (
            invitation_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            participant_id TEXT NOT NULL, invitation_ref TEXT NOT NULL,
            channel TEXT NOT NULL, status TEXT NOT NULL, sent_at TEXT NOT NULL,
            response_at TEXT, created_at TEXT NOT NULL,
            UNIQUE(tenant_id, invitation_ref)
        )""",
        """CREATE TABLE IF NOT EXISTS favp_timeline (
            timeline_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            participant_id TEXT NOT NULL, event_type TEXT NOT NULL,
            from_state TEXT, to_state TEXT, actor_ref TEXT NOT NULL,
            notes TEXT, occurred_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS favp_scenarios (
            scenario_id TEXT PRIMARY KEY, name TEXT NOT NULL,
            description TEXT NOT NULL, evidence_package_json TEXT NOT NULL,
            objectives_json TEXT NOT NULL, mitre_mapping_json TEXT NOT NULL,
            evaluation_criteria_json TEXT NOT NULL, difficulty TEXT NOT NULL,
            version TEXT NOT NULL, synthetic INTEGER NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS favp_assignments (
            assignment_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            participant_id TEXT NOT NULL, scenario_id TEXT NOT NULL,
            assigned_by TEXT NOT NULL, assigned_at TEXT NOT NULL,
            status TEXT NOT NULL, UNIQUE(tenant_id, participant_id, scenario_id)
        )""",
        """CREATE TABLE IF NOT EXISTS favp_results (
            result_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            participant_id TEXT NOT NULL, scenario_id TEXT NOT NULL,
            started_at TEXT NOT NULL, completed_at TEXT NOT NULL,
            duration_seconds REAL NOT NULL, analyst_decision TEXT NOT NULL,
            ai_recommendation_json TEXT NOT NULL, evidence_references_json TEXT NOT NULL,
            provenance_references_json TEXT NOT NULL, features_used_json TEXT NOT NULL,
            limitations_json TEXT NOT NULL, ai_investigation_version TEXT NOT NULL,
            platform_build_version TEXT NOT NULL, created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS favp_feedback (
            feedback_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            participant_id TEXT NOT NULL, scenario_id TEXT NOT NULL,
            result_id TEXT NOT NULL, trust_evidence INTEGER NOT NULL,
            reasoning_understanding INTEGER NOT NULL, confidence_rating INTEGER NOT NULL,
            provenance_clarity INTEGER NOT NULL, timeline_usefulness INTEGER NOT NULL,
            ioc_enrichment_usefulness INTEGER NOT NULL, evidence_quality INTEGER NOT NULL,
            would_pay INTEGER, requested_tier TEXT, requested_integrations_json TEXT NOT NULL,
            deployment_requirements_json TEXT NOT NULL, incorrect_reasoning TEXT,
            limitations TEXT, comments TEXT, created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS favp_evidence_records (
            evidence_record_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            participant_id TEXT NOT NULL, result_id TEXT NOT NULL,
            evidence_reference TEXT NOT NULL, provenance_reference TEXT NOT NULL,
            evidence_sha256 TEXT NOT NULL, ai_investigation_version TEXT NOT NULL,
            platform_build_version TEXT NOT NULL, sequence_number INTEGER NOT NULL,
            previous_record_hash TEXT, record_hash TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS favp_execution_profiles (
            profile_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            participant_id TEXT NOT NULL, organization_id TEXT NOT NULL,
            state TEXT NOT NULL, nda_status TEXT NOT NULL, terms_status TEXT NOT NULL,
            onboarding_status TEXT NOT NULL, access_expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL, revoked_at TEXT,
            UNIQUE(tenant_id, participant_id)
        )""",
        """CREATE TABLE IF NOT EXISTS favp_execution_scenarios (
            scenario_id TEXT PRIMARY KEY, scenario_json TEXT NOT NULL,
            version TEXT NOT NULL, synthetic INTEGER NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS favp_execution_sessions (
            session_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            profile_id TEXT NOT NULL, participant_id TEXT NOT NULL,
            scenario_id TEXT NOT NULL, started_at TEXT NOT NULL,
            completed_at TEXT, status TEXT NOT NULL,
            ai_investigation_version TEXT NOT NULL, platform_build_version TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS favp_execution_reviews (
            review_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            session_id TEXT NOT NULL, profile_id TEXT NOT NULL,
            analyst_decision TEXT NOT NULL, ai_recommendation_json TEXT NOT NULL,
            disagreement INTEGER NOT NULL, confidence_score INTEGER NOT NULL,
            usability_score INTEGER NOT NULL, explanation_usefulness INTEGER NOT NULL,
            uncertainty_reported INTEGER NOT NULL, features_used_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS favp_evidence_validations (
            validation_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            session_id TEXT NOT NULL, profile_id TEXT NOT NULL,
            evidence_reference TEXT NOT NULL, provenance_reference TEXT NOT NULL,
            evidence_completeness TEXT NOT NULL, provenance_integrity TEXT NOT NULL,
            timestamp_consistency TEXT NOT NULL, chain_of_custody TEXT NOT NULL,
            reproducibility TEXT NOT NULL, ai_explanation_quality TEXT NOT NULL,
            uncertainty_reporting TEXT NOT NULL, validator_ref TEXT NOT NULL,
            validation_hash TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL
        )""",
    )
    for statement in statements:
        connection.execute(statement)

    # AuditService may have created the legacy base table before the staging
    # migration ran. Bring that table to the migration-owned shape before
    # creating indexes and append-only guards.
    audit_columns = table_columns(
        connection,
        "postgresql" if getattr(connection, "backend_name", "sqlite") == "postgresql" else "sqlite",
        "audit_events",
    )
    audit_additions = {
        "event_id": "ALTER TABLE audit_events ADD COLUMN event_id TEXT",
        "tenant_id": "ALTER TABLE audit_events ADD COLUMN tenant_id TEXT",
        "actor_id": "ALTER TABLE audit_events ADD COLUMN actor_id TEXT",
        "correlation_id": "ALTER TABLE audit_events ADD COLUMN correlation_id TEXT",
        "request_id": "ALTER TABLE audit_events ADD COLUMN request_id TEXT",
        "resource_type": "ALTER TABLE audit_events ADD COLUMN resource_type TEXT",
        "resource_id": "ALTER TABLE audit_events ADD COLUMN resource_id TEXT",
        "operation": "ALTER TABLE audit_events ADD COLUMN operation TEXT",
        "outcome": "ALTER TABLE audit_events ADD COLUMN outcome TEXT",
        "latency_ms": "ALTER TABLE audit_events ADD COLUMN latency_ms REAL",
        "sequence_number": "ALTER TABLE audit_events ADD COLUMN sequence_number INTEGER",
        "schema_version": "ALTER TABLE audit_events ADD COLUMN schema_version TEXT NOT NULL DEFAULT 'audit-event-v1'",
    }
    for column, statement in audit_additions.items():
        if column not in audit_columns:
            connection.execute(statement)
    connection.execute("UPDATE audit_events SET event_id='legacy-' || id WHERE event_id IS NULL OR event_id='' ")

    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_audit_events_event_id ON audit_events(event_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_audit_events_tenant_created ON audit_events(tenant_id, created_at, id)")
    for table, prefix in (
        ("audit_events", "audit_events_append_only"),
        ("favp_invitations", "favp_invitations_append_only"),
        ("favp_timeline", "favp_timeline_append_only"),
        ("favp_results", "favp_results_append_only"),
        ("favp_feedback", "favp_feedback_append_only"),
        ("favp_evidence_records", "favp_evidence_append_only"),
        ("favp_execution_reviews", "favp_execution_reviews_append_only"),
        ("favp_evidence_validations", "favp_evidence_validations_append_only"),
    ):
        for statement in append_only_statements(
            getattr(connection, "backend_name", "sqlite"),
            table_name=table,
            trigger_prefix=prefix,
            error_message=f"{table}_are_append_only",
        ):
            connection.execute(statement)

    for scenario in FAVP_SCENARIOS.values():
        connection.execute(
            """INSERT INTO favp_scenarios(
                scenario_id,name,description,evidence_package_json,objectives_json,
                mitre_mapping_json,evaluation_criteria_json,difficulty,version,synthetic
            ) VALUES(?,?,?,?,?,?,?,?,?,1)
            ON CONFLICT(scenario_id) DO NOTHING""",
            (
                scenario["scenario_id"], scenario["name"], scenario["description"],
                _catalog_json(scenario["evidence_package"]),
                _catalog_json(scenario["expected_investigation_objectives"]),
                _catalog_json(scenario["mitre_attack_mapping"]),
                _catalog_json(scenario["evaluation_criteria"]), scenario["difficulty"],
                scenario["version"],
            ),
        )
    for scenario in FAVP_EXECUTION_SCENARIOS.values():
        connection.execute(
            """INSERT INTO favp_execution_scenarios(scenario_id,scenario_json,version,synthetic)
            VALUES(?,?,?,1) ON CONFLICT(scenario_id) DO NOTHING""",
            (scenario["scenario_id"], _catalog_json(scenario), scenario["version"]),
        )

    for statement in (
        "CREATE INDEX IF NOT EXISTS idx_favp_org_tenant ON favp_organizations(tenant_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_favp_participant_tenant ON favp_participants(tenant_id, state, updated_at)",
        "CREATE INDEX IF NOT EXISTS idx_favp_timeline_participant ON favp_timeline(tenant_id, participant_id, occurred_at)",
        "CREATE INDEX IF NOT EXISTS idx_favp_assignment_participant ON favp_assignments(tenant_id, participant_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_favp_result_tenant ON favp_results(tenant_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_favp_feedback_tenant ON favp_feedback(tenant_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_favp_evidence_tenant ON favp_evidence_records(tenant_id, sequence_number)",
        "CREATE INDEX IF NOT EXISTS idx_favp_execution_profiles_tenant ON favp_execution_profiles(tenant_id, state, updated_at)",
        "CREATE INDEX IF NOT EXISTS idx_favp_execution_sessions_tenant ON favp_execution_sessions(tenant_id, started_at)",
        "CREATE INDEX IF NOT EXISTS idx_favp_execution_reviews_tenant ON favp_execution_reviews(tenant_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_favp_evidence_validations_tenant ON favp_evidence_validations(tenant_id, created_at)",
    ):
        connection.execute(statement)
