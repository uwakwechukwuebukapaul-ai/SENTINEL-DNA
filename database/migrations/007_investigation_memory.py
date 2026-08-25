"""Tenant-scoped investigation memory, feedback, and audit tables."""

VERSION = 7
DESCRIPTION = "Investigation memory learning records and append-only feedback audit"


def upgrade(connection):
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS investigation_memory (
            memory_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            case_id TEXT NOT NULL,
            investigation_id TEXT NOT NULL DEFAULT '',
            investigation_type TEXT NOT NULL,
            scenario TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            confidence REAL NOT NULL,
            evidence_summary TEXT NOT NULL DEFAULT '{}',
            reasoning_summary TEXT NOT NULL DEFAULT '{}',
            mitre_techniques TEXT NOT NULL DEFAULT '[]',
            outcome TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            synthetic_only INTEGER NOT NULL DEFAULT 1 CHECK (synthetic_only IN (0, 1)),
            provenance TEXT NOT NULL DEFAULT '{}',
            verdict TEXT NOT NULL DEFAULT '',
            attack_pattern TEXT NOT NULL DEFAULT '[]',
            evidence_fingerprint TEXT NOT NULL DEFAULT '',
            validation_result TEXT NOT NULL DEFAULT 'validated',
            audit_hash TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS investigation_memory_feedback (
            feedback_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            investigation_id TEXT NOT NULL,
            analyst_id TEXT NOT NULL,
            verdict TEXT NOT NULL,
            confidence REAL,
            reason TEXT NOT NULL DEFAULT '',
            evidence_references TEXT NOT NULL DEFAULT '[]',
            provenance TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            audit_hash TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_investigation_memory_feedback_tenant
            ON investigation_memory_feedback(tenant_id, investigation_id, created_at);
        CREATE TABLE IF NOT EXISTS investigation_memory_audit (
            audit_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            event_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_investigation_memory_audit_tenant
            ON investigation_memory_audit(tenant_id, created_at);
        """
    )
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(investigation_memory)").fetchall()
    }
    additions = {
        "tenant_id": "ALTER TABLE investigation_memory ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'",
        "investigation_id": "ALTER TABLE investigation_memory ADD COLUMN investigation_id TEXT NOT NULL DEFAULT ''",
        "provenance": "ALTER TABLE investigation_memory ADD COLUMN provenance TEXT NOT NULL DEFAULT '{}'",
        "verdict": "ALTER TABLE investigation_memory ADD COLUMN verdict TEXT NOT NULL DEFAULT ''",
        "attack_pattern": "ALTER TABLE investigation_memory ADD COLUMN attack_pattern TEXT NOT NULL DEFAULT '[]'",
        "evidence_fingerprint": "ALTER TABLE investigation_memory ADD COLUMN evidence_fingerprint TEXT NOT NULL DEFAULT ''",
        "validation_result": "ALTER TABLE investigation_memory ADD COLUMN validation_result TEXT NOT NULL DEFAULT 'validated'",
        "audit_hash": "ALTER TABLE investigation_memory ADD COLUMN audit_hash TEXT NOT NULL DEFAULT ''",
    }
    for column, statement in additions.items():
        if column not in columns:
            connection.execute(statement)
    connection.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_investigation_memory_tenant_case
            ON investigation_memory(tenant_id, case_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_investigation_memory_tenant_type
            ON investigation_memory(tenant_id, investigation_type, created_at);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_investigation_memory_tenant_fingerprint
            ON investigation_memory(tenant_id, evidence_fingerprint)
            WHERE evidence_fingerprint <> '';
        """
    )
