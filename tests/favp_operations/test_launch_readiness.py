from datetime import datetime, timedelta, timezone
from pathlib import Path

from database.connection import DatabaseConnection
from services.audit.service import AuditService
from services.favp_operations import (
    FAVPOperationsRepository,
    FAVPOperationsService,
    FAVPParticipantActivationService,
    FAVPExecutionService,
    FAVPStagingLaunchReadiness,
)


ROOT = Path(__file__).resolve().parents[2]


def build(tmp_path, *, active=True):
    db = DatabaseConnection(tmp_path / "launch-readiness.sqlite")
    audit = AuditService(db)
    operations = FAVPOperationsService(FAVPOperationsRepository(db), audit)
    execution = FAVPExecutionService(operations, audit)
    organization = operations.create_organization(tenant_id="tenant-a", organization_ref="org-a", display_name="Sanitized Organization", actor_ref="manager-a")
    participant = operations.create_participant(tenant_id="tenant-a", organization_id=organization["organization_id"], participant_ref="participant-a", display_name="Sanitized Analyst", actor_identity_ref="actor-a", actor_ref="manager-a")
    if active:
        operations.record_invitation(tenant_id="tenant-a", participant_id=participant["participant_id"], invitation_ref="invitation-a", channel="operator_handoff", status="SENT", actor_ref="manager-a")
        profile = execution.create_profile(tenant_id="tenant-a", participant_id=participant["participant_id"], access_expires_at=(datetime.now(timezone.utc) + timedelta(days=30)).isoformat(), actor_ref="manager-a")
        FAVPParticipantActivationService(operations, execution, audit).activate(
            tenant_id="tenant-a", participant_id=participant["participant_id"], profile_id=profile["profile_id"], actor_ref="manager-a", operator_confirmation=True
        )
    return db, audit, execution


def environment(tmp_path):
    return {
        "SENTINEL_DNA_ENV": "staging",
        "SENTINEL_DNA_FAVP_OPERATIONS_ENABLED": "1",
        "SENTINEL_DNA_FAVP_SYNTHETIC_ONLY": "1",
        "SENTINEL_DNA_FAVP_PRODUCTION_ACCESS": "0",
        "SENTINEL_DNA_CONFIG_SOURCE_CLASSIFICATION": "external_non_production",
        "SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION": "disposable_staging",
        "SENTINEL_DNA_TENANT_ISOLATION_ENABLED": "1",
        "SENTINEL_DNA_AUDIT_LOGGING_ENABLED": "1",
        "DATABASE_URL": "postgresql://sentinel@postgres:5432/sentinel_dna",
    }


def test_launch_dashboard_checks_all_operator_boundaries(tmp_path):
    db, audit, execution = build(tmp_path)
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    result = FAVPStagingLaunchReadiness(
        db,
        audit,
        execution,
        environ=environment(tmp_path),
        evidence_dir=evidence_dir,
        compose_path=ROOT / "deployment" / "staging" / "docker-compose.yml",
        tenant_id="tenant-a",
    ).check()
    # The unit backend is intentionally SQLite; a test fixture must never be
    # accepted as disposable PostgreSQL staging evidence.
    assert result["status"] == "FAVP_STAGING_LAUNCH_BLOCKED"
    assert "postgres_backend" in result["summary"]["blocking_checks"]
    assert result["summary"]["blocked"] == 1
    assert result["launch_gate"]["activation_performed"] is False
    assert result["no_fabricated_values"] is True
    statuses = {item["name"]: item["status"] for item in result["checks"]}
    assert statuses["favp_database_schema"] == "PASS"
    assert statuses["evidence_storage"] == "PASS"
    assert statuses["participant_onboarding"] == "PASS"
    assert statuses["scenario_packages"] == "PASS"
    assert statuses["report_generation"] == "PASS"
    assert statuses["audit_trail"] == "PASS"
    assert statuses["tenant_isolation"] == "PASS"
    assert statuses["disposable_postgres_provisioning"] == "PASS"


def test_launch_dashboard_blocks_without_onboarded_participant(tmp_path):
    db, audit, execution = build(tmp_path, active=False)
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    result = FAVPStagingLaunchReadiness(
        db,
        audit,
        execution,
        environ=environment(tmp_path),
        evidence_dir=evidence_dir,
        compose_path=ROOT / "deployment" / "staging" / "docker-compose.yml",
    ).check()
    blocked = set(result["summary"]["blocking_checks"])
    assert "participant_onboarding" in blocked
    assert result["status"] == "FAVP_STAGING_LAUNCH_BLOCKED"


def test_launch_dashboard_blocks_when_synthetic_or_production_boundary_is_wrong(tmp_path):
    db, audit, execution = build(tmp_path)
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    values = environment(tmp_path)
    values["SENTINEL_DNA_FAVP_SYNTHETIC_ONLY"] = "0"
    values["SENTINEL_DNA_FAVP_PRODUCTION_ACCESS"] = "1"
    result = FAVPStagingLaunchReadiness(db, audit, execution, environ=values, evidence_dir=evidence_dir).check()
    blocked = set(result["summary"]["blocking_checks"])
    assert {"synthetic_only", "production_isolation"}.issubset(blocked)
