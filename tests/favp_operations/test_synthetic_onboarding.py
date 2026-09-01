from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from database.connection import DatabaseConnection
from database.migration_runner import MigrationRunner, STAGING_MIGRATIONS
from deployment.staging.scripts import onboard_favp_participant as onboarding
from deployment.staging.scripts import activate_favp_participant as activation
from deployment.staging.scripts import recover_favp_staging as recovery
from services.audit.service import AuditService
from services.favp_operations import (
    FAVPActivationError,
    FAVPExecutionService,
    FAVPOperationsRepository,
    FAVPOperationsService,
    FAVPParticipantActivationService,
    FAVPStagingLaunchReadiness,
)


ROOT = Path(__file__).resolve().parents[2]


def _args(**overrides):
    values = {
        "synthetic": True,
        "operator_confirmation": True,
        "synthetic_access_days": 30,
    }
    values.update(overrides)
    return Namespace(**values)


def _environment(monkeypatch):
    for key, value in {
        "SENTINEL_DNA_ENV": "staging",
        "SENTINEL_DNA_FAVP_OPERATIONS_ENABLED": "1",
        "SENTINEL_DNA_FAVP_SYNTHETIC_ONLY": "1",
        "SENTINEL_DNA_FAVP_PRODUCTION_ACCESS": "0",
        "SENTINEL_DNA_AUDIT_LOGGING_ENABLED": "1",
        "SENTINEL_DNA_TENANT_ISOLATION_ENABLED": "1",
    }.items():
        monkeypatch.setenv(key, value)


def test_synthetic_onboarding_only_creates_invited_state(tmp_path, monkeypatch):
    _environment(monkeypatch)
    db = DatabaseConnection(tmp_path / "favp.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    monkeypatch.setattr(onboarding, "database_for_environment", lambda require_postgresql: db)

    result = onboarding.onboard(_args())

    assert result["status"] == "FAVP_SYNTHETIC_PARTICIPANT_INVITED"
    assert result["synthetic_only"] is True
    assert result["participant_state"] == "INVITED"
    assert result["profile_state"] == "INVITED"
    assert result["invitation_status"] == "SENT"
    assert result["access_granted"] is False
    assert result["activation_performed"] is False
    assert result["credentials_stored"] is False
    assert result["audit_recorded"] is True

    with db.session() as connection:
        participant = connection.execute(
            "SELECT * FROM favp_participants WHERE participant_id=?",
            (result["participant_id"],),
        ).fetchone()
        profile = connection.execute(
            "SELECT * FROM favp_execution_profiles WHERE profile_id=?",
            (result["profile_id"],),
        ).fetchone()
        events = connection.execute(
            "SELECT event_type FROM audit_events WHERE tenant_id=?",
            (onboarding.SYNTHETIC_TENANT_ID,),
        ).fetchall()

    assert participant["actor_identity_ref"] == onboarding.SYNTHETIC_ACTOR_IDENTITY_REF
    assert participant["state"] == "INVITED"
    assert participant["nda_status"] == "NOT_STARTED"
    assert participant["terms_status"] == "NOT_STARTED"
    assert participant["onboarding_status"] == "NOT_STARTED"
    assert profile["state"] == "INVITED"
    assert profile["nda_status"] == "NOT_STARTED"
    assert profile["terms_status"] == "NOT_STARTED"
    assert profile["onboarding_status"] == "NOT_STARTED"
    assert datetime.fromisoformat(profile["access_expires_at"]) > datetime.now(timezone.utc)
    assert "FAVP_SYNTHETIC_INVITATION_CREATED" in {row[0] for row in events}


def test_synthetic_onboarding_reuses_existing_organization_participant_and_invitation(tmp_path, monkeypatch):
    _environment(monkeypatch)
    db = DatabaseConnection(tmp_path / "reconcile.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    monkeypatch.setattr(onboarding, "database_for_environment", lambda require_postgresql: db)

    first = onboarding.onboard(_args())
    second = onboarding.onboard(_args())

    assert second["organization_id"] == first["organization_id"]
    assert second["participant_id"] == first["participant_id"]
    assert second["invitation_id"] == first["invitation_id"]
    assert second["profile_id"] == first["profile_id"]
    with db.session() as connection:
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("favp_organizations", "favp_participants", "favp_invitations", "favp_execution_profiles")
        }
    assert counts == {
        "favp_organizations": 1,
        "favp_participants": 1,
        "favp_invitations": 1,
        "favp_execution_profiles": 1,
    }


def test_synthetic_activation_requires_confirmation_and_records_required_events(tmp_path, monkeypatch):
    _environment(monkeypatch)
    db = DatabaseConnection(tmp_path / "activation.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    monkeypatch.setattr(onboarding, "database_for_environment", lambda require_postgresql: db)
    monkeypatch.setattr(activation, "database_for_environment", lambda require_postgresql: db)

    invited = onboarding.onboard(_args())
    with pytest.raises(RuntimeError, match="operator-confirmation"):
        activation.activate(_args(operator_confirmation=False))

    result = activation.activate(_args())
    assert result["status"] == "FAVP_SYNTHETIC_PARTICIPANT_ACTIVATED"
    assert result["participant_state"] == "ACTIVE_VALIDATION"
    assert result["profile_state"] == "ACTIVE"
    assert result["invitation_status"] == "ACCEPTED"
    assert result["production_access"] == "0"
    assert result["synthetic_only"] is True
    assert result["human_program_owner_authorization_required"] is True
    assert result["activation_performed"] is False
    assert result["invitation_id"] == invited["invitation_id"]

    events = AuditService(db).list_for_tenant(onboarding.SYNTHETIC_TENANT_ID, limit=100)
    event_types = {event["event_type"] for event in events}
    assert {
        "FAVP_INVITATION_ACCEPTED",
        "FAVP_NDA_ACCEPTED",
        "FAVP_TERMS_ACCEPTED",
        "FAVP_PARTICIPANT_ACTIVATED",
    }.issubset(event_types)
    with db.session() as connection:
        rows = connection.execute(
            "SELECT state,access_status,nda_status,terms_status,onboarding_status FROM favp_participants WHERE participant_id=?",
            (invited["participant_id"],),
        ).fetchone()
        invitation_rows = connection.execute(
            "SELECT invitation_id,status,response_at FROM favp_invitations WHERE tenant_id=? AND participant_id=?",
            (onboarding.SYNTHETIC_TENANT_ID, invited["participant_id"]),
        ).fetchall()
    assert tuple(rows) == ("ACTIVE_VALIDATION", "ACTIVE", "ACCEPTED", "ACCEPTED", "COMPLETED")
    assert len(invitation_rows) == 1
    assert tuple(invitation_rows[0]) == (invited["invitation_id"], "SENT", None)


def test_repeated_synthetic_activation_is_idempotent_and_does_not_duplicate_audit(tmp_path, monkeypatch):
    _environment(monkeypatch)
    db = DatabaseConnection(tmp_path / "activation-replay.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    monkeypatch.setattr(onboarding, "database_for_environment", lambda require_postgresql: db)
    monkeypatch.setattr(activation, "database_for_environment", lambda require_postgresql: db)

    onboarding.onboard(_args())
    first = activation.activate(_args())
    with db.session() as connection:
        first_counts = {
            event: connection.execute(
                "SELECT COUNT(*) FROM audit_events WHERE tenant_id=? AND event_type=?",
                (onboarding.SYNTHETIC_TENANT_ID, event),
            ).fetchone()[0]
            for event in ("FAVP_INVITATION_ACCEPTED", "FAVP_NDA_ACCEPTED", "FAVP_TERMS_ACCEPTED", "FAVP_PARTICIPANT_ACTIVATED")
        }

    second = activation.activate(_args())

    assert first["idempotent_replay"] is False
    assert second["idempotent_replay"] is True
    assert second["participant_state"] == "ACTIVE_VALIDATION"
    assert second["profile_state"] == "ACTIVE"
    assert second["invitation_status"] == "ACCEPTED"
    assert second["invitation_record_status"] == "SENT"
    with db.session() as connection:
        second_counts = {
            event: connection.execute(
                "SELECT COUNT(*) FROM audit_events WHERE tenant_id=? AND event_type=?",
                (onboarding.SYNTHETIC_TENANT_ID, event),
            ).fetchone()[0]
            for event in first_counts
        }
    assert second_counts == first_counts


def test_activation_command_explains_missing_invitation_lifecycle_transition(tmp_path, monkeypatch):
    _environment(monkeypatch)
    db = DatabaseConnection(tmp_path / "activation-missing-invitation.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    audit = AuditService(db)
    operations = FAVPOperationsService(FAVPOperationsRepository(db), audit)
    execution = FAVPExecutionService(operations, audit)
    organization = operations.create_organization(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        organization_ref="synthetic-org-without-invitation",
        display_name="Synthetic Organization",
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )
    participant = operations.create_participant(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        organization_id=organization["organization_id"],
        participant_ref=onboarding.SYNTHETIC_PARTICIPANT_REF,
        display_name="Synthetic Participant",
        actor_identity_ref=onboarding.SYNTHETIC_ACTOR_IDENTITY_REF,
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )
    profile = execution.create_profile(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        participant_id=participant["participant_id"],
        access_expires_at="2030-01-01T00:00:00+00:00",
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )
    monkeypatch.setattr(activation, "database_for_environment", lambda require_postgresql: db)

    with pytest.raises(RuntimeError, match="run onboard_favp_participant.py.*recover_favp_staging.py"):
        activation.activate(_args(participant_id=participant["participant_id"], profile_id=profile["profile_id"]))


def test_recovery_reconciles_missing_records_and_is_safe_to_repeat(tmp_path, monkeypatch):
    _environment(monkeypatch)
    db = DatabaseConnection(tmp_path / "recovery.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    monkeypatch.setattr(onboarding, "database_for_environment", lambda require_postgresql: db)
    monkeypatch.setattr(activation, "database_for_environment", lambda require_postgresql: db)

    first = recovery.recover_synthetic(_args())
    second = recovery.recover_synthetic(_args())

    assert first["status"] == "FAVP_STAGING_RECOVERED"
    assert first["activation"]["idempotent_replay"] is False
    assert second["activation"]["idempotent_replay"] is True
    assert second["reconciliation"]["participant_id"] == first["reconciliation"]["participant_id"]
    with db.session() as connection:
        assert connection.execute("SELECT COUNT(*) FROM favp_organizations").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM favp_participants").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM favp_invitations").fetchone()[0] == 1


def test_recovery_reuses_a_reserved_row_when_create_reports_a_race(
    tmp_path, monkeypatch
):
    _environment(monkeypatch)
    db = DatabaseConnection(tmp_path / "recovery-race.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    monkeypatch.setattr(onboarding, "database_for_environment", lambda require_postgresql: db)
    monkeypatch.setattr(activation, "database_for_environment", lambda require_postgresql: db)

    original_create = FAVPOperationsService.create_organization
    raced = False

    def create_then_report_race(service, **kwargs):
        nonlocal raced
        result = original_create(service, **kwargs)
        if not raced:
            raced = True
            raise RuntimeError("simulated_unique_race_after_commit")
        return result

    monkeypatch.setattr(FAVPOperationsService, "create_organization", create_then_report_race)

    result = recovery.recover_synthetic(_args())
    replay = recovery.recover_synthetic(_args())

    assert result["status"] == "FAVP_STAGING_RECOVERED"
    assert replay["activation"]["idempotent_replay"] is True
    assert replay["reconciliation"]["invitation_id"] == result["reconciliation"]["invitation_id"]
    with db.session() as connection:
        assert connection.execute("SELECT COUNT(*) FROM favp_organizations").fetchone()[0] == 1


def test_recovery_preserves_colliding_invitation_and_uses_replacement(
    tmp_path, monkeypatch
):
    _environment(monkeypatch)
    db = DatabaseConnection(tmp_path / "recovery-invitation-collision.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    monkeypatch.setattr(onboarding, "database_for_environment", lambda require_postgresql: db)
    monkeypatch.setattr(activation, "database_for_environment", lambda require_postgresql: db)

    audit = AuditService(db)
    operations = FAVPOperationsService(FAVPOperationsRepository(db), audit)
    organization = operations.create_organization(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        organization_ref=onboarding.SYNTHETIC_ORGANIZATION_REF,
        display_name=onboarding.SYNTHETIC_ORGANIZATION_NAME,
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )
    colliding_participant = operations.create_participant(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        organization_id=organization["organization_id"],
        participant_ref="stale-synthetic-participant",
        display_name="Stale Synthetic Participant",
        actor_identity_ref="stale-synthetic-actor",
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )
    colliding_invitation = operations.record_invitation(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        participant_id=colliding_participant["participant_id"],
        invitation_ref=onboarding.SYNTHETIC_INVITATION_REF,
        channel="operator_handoff",
        status="SENT",
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )

    result = recovery.recover_synthetic(_args())

    assert result["status"] == "FAVP_STAGING_RECOVERED"
    assert result["reconciliation"]["invitation_id"] != colliding_invitation["invitation_id"]
    assert result["reconciliation"]["invitation_ref"].startswith(
        f"{onboarding.SYNTHETIC_INVITATION_REF}-recovery-"
    )
    with db.session() as connection:
        rows = connection.execute(
            "SELECT participant_id,invitation_ref FROM favp_invitations "
            "WHERE tenant_id=? ORDER BY created_at,invitation_id",
            (onboarding.SYNTHETIC_TENANT_ID,),
        ).fetchall()
        preserved = connection.execute(
            "SELECT participant_id,invitation_ref FROM favp_invitations "
            "WHERE invitation_id=?",
            (colliding_invitation["invitation_id"],),
        ).fetchone()
    assert len(rows) == 2
    assert rows[0][0] == colliding_participant["participant_id"]
    assert tuple(preserved) == (
        colliding_participant["participant_id"],
        onboarding.SYNTHETIC_INVITATION_REF,
    )


def test_recovery_reuses_valid_linked_invitation_before_creating_replacement(
    tmp_path, monkeypatch
):
    _environment(monkeypatch)
    db = DatabaseConnection(tmp_path / "recovery-valid-invitation.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    monkeypatch.setattr(onboarding, "database_for_environment", lambda require_postgresql: db)
    monkeypatch.setattr(activation, "database_for_environment", lambda require_postgresql: db)

    audit = AuditService(db)
    operations = FAVPOperationsService(FAVPOperationsRepository(db), audit)
    organization = operations.create_organization(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        organization_ref=onboarding.SYNTHETIC_ORGANIZATION_REF,
        display_name=onboarding.SYNTHETIC_ORGANIZATION_NAME,
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )
    participant = operations.create_participant(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        organization_id=organization["organization_id"],
        participant_ref=onboarding.SYNTHETIC_PARTICIPANT_REF,
        display_name=onboarding.SYNTHETIC_PARTICIPANT_NAME,
        actor_identity_ref=onboarding.SYNTHETIC_ACTOR_IDENTITY_REF,
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )
    valid_invitation = operations.record_invitation(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        participant_id=participant["participant_id"],
        invitation_ref="legacy-valid-synthetic-invitation",
        channel="operator_handoff",
        status="SENT",
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )
    stale_participant = operations.create_participant(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        organization_id=organization["organization_id"],
        participant_ref="stale-synthetic-participant",
        display_name="Stale Synthetic Participant",
        actor_identity_ref="stale-synthetic-actor",
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )
    operations.record_invitation(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        participant_id=stale_participant["participant_id"],
        invitation_ref=onboarding.SYNTHETIC_INVITATION_REF,
        channel="operator_handoff",
        status="SENT",
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )

    result = recovery.recover_synthetic(_args())

    assert result["reconciliation"]["invitation_id"] == valid_invitation["invitation_id"]
    with db.session() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM favp_invitations WHERE tenant_id=?",
            (onboarding.SYNTHETIC_TENANT_ID,),
        ).fetchone()[0] == 2


def test_recovery_discovers_valid_synthetic_identity_with_legacy_refs(
    tmp_path, monkeypatch
):
    _environment(monkeypatch)
    db = DatabaseConnection(tmp_path / "recovery-legacy-identity.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    monkeypatch.setattr(onboarding, "database_for_environment", lambda require_postgresql: db)
    monkeypatch.setattr(activation, "database_for_environment", lambda require_postgresql: db)

    audit = AuditService(db)
    operations = FAVPOperationsService(FAVPOperationsRepository(db), audit)
    execution = FAVPExecutionService(operations, audit)
    organization = operations.create_organization(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        organization_ref="legacy-synthetic-organization-ref",
        display_name=onboarding.SYNTHETIC_ORGANIZATION_NAME,
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )
    participant = operations.create_participant(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        organization_id=organization["organization_id"],
        participant_ref="legacy-synthetic-participant-ref",
        display_name=onboarding.SYNTHETIC_PARTICIPANT_NAME,
        actor_identity_ref="legacy-synthetic-identity",
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )
    invitation = operations.record_invitation(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        participant_id=participant["participant_id"],
        invitation_ref=onboarding.SYNTHETIC_INVITATION_REF,
        channel="operator_handoff",
        status="SENT",
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )
    profile = execution.create_profile(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        participant_id=participant["participant_id"],
        access_expires_at="2030-01-01T00:00:00+00:00",
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )

    result = recovery.recover_synthetic(_args())

    assert result["reconciliation"]["organization_id"] == organization["organization_id"]
    assert result["reconciliation"]["participant_id"] == participant["participant_id"]
    assert result["reconciliation"]["invitation_id"] == invitation["invitation_id"]
    assert result["reconciliation"]["profile_id"] == profile["profile_id"]
    with db.session() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM favp_participants WHERE tenant_id=?",
            (onboarding.SYNTHETIC_TENANT_ID,),
        ).fetchone()[0] == 1


def test_recovery_reconciles_existing_sent_invitation_without_mutating_it(
    tmp_path, monkeypatch
):
    _environment(monkeypatch)
    db = DatabaseConnection(tmp_path / "recovery-existing-invitation.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    monkeypatch.setattr(onboarding, "database_for_environment", lambda require_postgresql: db)
    monkeypatch.setattr(activation, "database_for_environment", lambda require_postgresql: db)

    audit = AuditService(db)
    operations = FAVPOperationsService(FAVPOperationsRepository(db), audit)
    organization = operations.create_organization(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        organization_ref=onboarding.SYNTHETIC_ORGANIZATION_REF,
        display_name=onboarding.SYNTHETIC_ORGANIZATION_NAME,
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )
    participant = operations.create_participant(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        organization_id=organization["organization_id"],
        participant_ref=onboarding.SYNTHETIC_PARTICIPANT_REF,
        display_name=onboarding.SYNTHETIC_PARTICIPANT_NAME,
        actor_identity_ref=onboarding.SYNTHETIC_ACTOR_IDENTITY_REF,
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
        contact_reference=onboarding.SYNTHETIC_CONTACT_REFERENCE,
    )
    invitation = operations.record_invitation(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        participant_id=participant["participant_id"],
        invitation_ref=onboarding.SYNTHETIC_INVITATION_REF,
        channel="operator_handoff",
        status="SENT",
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )
    with db.session() as connection:
        before = tuple(
            connection.execute(
                "SELECT invitation_id,tenant_id,participant_id,invitation_ref,status,sent_at,response_at,created_at "
                "FROM favp_invitations WHERE invitation_id=?",
                (invitation["invitation_id"],),
            ).fetchone()
        )

    result = recovery.recover_synthetic(_args())

    assert result["reconciliation"]["participant_id"] == participant["participant_id"]
    assert result["reconciliation"]["invitation_id"] == invitation["invitation_id"]
    assert result["reconciliation"]["invitation_ref"] == onboarding.SYNTHETIC_INVITATION_REF
    assert result["reconciliation"]["participant_state"] == "ACTIVE_VALIDATION"
    assert result["reconciliation"]["profile_state"] == "ACTIVE"
    assert result["activation"]["invitation_record_status"] == "SENT"

    with db.session() as connection:
        after = tuple(
            connection.execute(
                "SELECT invitation_id,tenant_id,participant_id,invitation_ref,status,sent_at,response_at,created_at "
                "FROM favp_invitations WHERE invitation_id=?",
                (invitation["invitation_id"],),
            ).fetchone()
        )
        timeline_types = {
            row[0]
            for row in connection.execute(
                "SELECT event_type FROM favp_timeline WHERE tenant_id=? AND participant_id=?",
                (onboarding.SYNTHETIC_TENANT_ID, participant["participant_id"]),
            ).fetchall()
        }
        audit_types = {
            row[0]
            for row in connection.execute(
                "SELECT event_type FROM audit_events WHERE tenant_id=? AND resource_id IN (?,?)",
                (onboarding.SYNTHETIC_TENANT_ID, participant["participant_id"], invitation["invitation_id"]),
            ).fetchall()
        }

    assert after == before
    assert "INVITATION_ACCEPTED" in timeline_types
    assert {
        "FAVP_INVITATION_ACCEPTED",
        "FAVP_NDA_ACCEPTED",
        "FAVP_TERMS_ACCEPTED",
        "FAVP_PARTICIPANT_ACTIVATED",
    }.issubset(audit_types)


def test_recovery_replay_returns_already_reconciled_state_without_new_events(
    tmp_path, monkeypatch
):
    _environment(monkeypatch)
    db = DatabaseConnection(tmp_path / "recovery-replay-existing.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    monkeypatch.setattr(onboarding, "database_for_environment", lambda require_postgresql: db)
    monkeypatch.setattr(activation, "database_for_environment", lambda require_postgresql: db)

    first = recovery.recover_synthetic(_args())
    with db.session() as connection:
        first_timeline_count = connection.execute(
            "SELECT COUNT(*) FROM favp_timeline WHERE tenant_id=? AND participant_id=?",
            (onboarding.SYNTHETIC_TENANT_ID, first["reconciliation"]["participant_id"]),
        ).fetchone()[0]
        first_audit_count = connection.execute(
            "SELECT COUNT(*) FROM audit_events WHERE tenant_id=?",
            (onboarding.SYNTHETIC_TENANT_ID,),
        ).fetchone()[0]

    second = recovery.recover_synthetic(_args())

    assert second["activation"]["idempotent_replay"] is True
    assert second["reconciliation"] == first["reconciliation"]
    with db.session() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM favp_timeline WHERE tenant_id=? AND participant_id=?",
            (onboarding.SYNTHETIC_TENANT_ID, first["reconciliation"]["participant_id"]),
        ).fetchone()[0] == first_timeline_count
        assert connection.execute(
            "SELECT COUNT(*) FROM audit_events WHERE tenant_id=?",
            (onboarding.SYNTHETIC_TENANT_ID,),
        ).fetchone()[0] == first_audit_count


def test_invitation_reconciliation_resolves_by_participant_before_reference(
    tmp_path, monkeypatch
):
    _environment(monkeypatch)
    db = DatabaseConnection(tmp_path / "invitation-participant-first.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))

    audit = AuditService(db)
    operations = FAVPOperationsService(FAVPOperationsRepository(db), audit)
    organization = operations.create_organization(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        organization_ref="participant-first-org",
        display_name="Participant First Organization",
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )
    participant = operations.create_participant(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        organization_id=organization["organization_id"],
        participant_ref="participant-first-ref",
        display_name="Participant First",
        actor_identity_ref="participant-first-identity",
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )
    invitation = operations.record_invitation(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        participant_id=participant["participant_id"],
        invitation_ref="existing-participant-invitation",
        channel="operator_handoff",
        status="SENT",
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )

    resolved = onboarding._resolve_or_create_invitation(
        operations,
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        participant_id=participant["participant_id"],
        invitation_ref="stale-reference",
        channel="operator_handoff",
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )

    assert resolved["invitation_id"] == invitation["invitation_id"]


def test_invitation_lookup_requires_tenant_participant_and_reference(
    tmp_path,
):
    db = DatabaseConnection(tmp_path / "invitation-lookup-isolation.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    audit = AuditService(db)
    operations = FAVPOperationsService(FAVPOperationsRepository(db), audit)
    organization_a = operations.create_organization(
        tenant_id="tenant-a",
        organization_ref="org-a",
        display_name="Organization A",
        actor_ref="operator-a",
    )
    organization_b = operations.create_organization(
        tenant_id="tenant-b",
        organization_ref="org-b",
        display_name="Organization B",
        actor_ref="operator-b",
    )
    participant_a = operations.create_participant(
        tenant_id="tenant-a",
        organization_id=organization_a["organization_id"],
        participant_ref="participant-a",
        display_name="Participant A",
        actor_ref="operator-a",
    )
    participant_b = operations.create_participant(
        tenant_id="tenant-b",
        organization_id=organization_b["organization_id"],
        participant_ref="participant-b",
        display_name="Participant B",
        actor_ref="operator-b",
    )
    invitation_a = operations.record_invitation(
        tenant_id="tenant-a",
        participant_id=participant_a["participant_id"],
        invitation_ref="shared-invitation-ref",
        channel="operator_handoff",
        status="SENT",
        actor_ref="operator-a",
    )
    invitation_b = operations.record_invitation(
        tenant_id="tenant-b",
        participant_id=participant_b["participant_id"],
        invitation_ref="shared-invitation-ref",
        channel="operator_handoff",
        status="SENT",
        actor_ref="operator-b",
    )
    repository = operations.repository

    assert repository.get_invitation_by_participant_and_ref(
        "tenant-a", participant_a["participant_id"], "shared-invitation-ref"
    )["invitation_id"] == invitation_a["invitation_id"]
    assert repository.get_invitation_by_participant_and_ref(
        "tenant-b", participant_b["participant_id"], "shared-invitation-ref"
    )["invitation_id"] == invitation_b["invitation_id"]
    assert repository.get_invitation_by_participant_and_ref(
        "tenant-a", participant_b["participant_id"], "shared-invitation-ref"
    ) is None


def test_recovery_reuses_explicit_existing_synthetic_participant_id(
    tmp_path, monkeypatch
):
    _environment(monkeypatch)
    db = DatabaseConnection(tmp_path / "recovery-explicit-participant.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    monkeypatch.setattr(onboarding, "database_for_environment", lambda require_postgresql: db)
    monkeypatch.setattr(activation, "database_for_environment", lambda require_postgresql: db)

    audit = AuditService(db)
    operations = FAVPOperationsService(FAVPOperationsRepository(db), audit)
    organization = operations.create_organization(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        organization_ref="explicit-participant-org",
        display_name=onboarding.SYNTHETIC_ORGANIZATION_NAME,
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )
    participant = operations.create_participant(
        tenant_id=onboarding.SYNTHETIC_TENANT_ID,
        organization_id=organization["organization_id"],
        participant_ref=onboarding.SYNTHETIC_PARTICIPANT_REF,
        display_name=onboarding.SYNTHETIC_PARTICIPANT_NAME,
        actor_identity_ref=onboarding.SYNTHETIC_ACTOR_IDENTITY_REF,
        actor_ref=onboarding.SYNTHETIC_ACTOR_REF,
    )

    result = recovery.recover_synthetic(
        _args(
            participant_id=participant["participant_id"],
            participant_ref="legacy-mismatched-participant-ref",
        )
    )

    assert result["reconciliation"]["participant_id"] == participant["participant_id"]
    with db.session() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM favp_participants WHERE tenant_id=?",
            (onboarding.SYNTHETIC_TENANT_ID,),
        ).fetchone()[0] == 1


def test_recovery_rejects_wrong_tenant_before_reconciliation(tmp_path, monkeypatch):
    _environment(monkeypatch)
    monkeypatch.setattr(
        recovery.onboarding,
        "onboard_synthetic",
        lambda _args: pytest.fail("wrong tenant must not enter reconciliation"),
    )
    with pytest.raises(RuntimeError, match="reserved staging tenant"):
        recovery.recover_synthetic(_args(tenant_id="wrong-tenant"))


def test_activation_requires_the_onboarding_invitation(tmp_path):
    db = DatabaseConnection(tmp_path / "activation-without-invitation.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    audit = AuditService(db)
    operations = FAVPOperationsService(FAVPOperationsRepository(db), audit)
    execution = FAVPExecutionService(operations, audit)
    organization = operations.create_organization(
        tenant_id="tenant-a",
        organization_ref="org-a",
        display_name="Synthetic Organization",
        actor_ref="manager-a",
    )
    participant = operations.create_participant(
        tenant_id="tenant-a",
        organization_id=organization["organization_id"],
        participant_ref="participant-a",
        display_name="Synthetic Participant",
        actor_identity_ref="actor-a",
        actor_ref="manager-a",
    )
    profile = execution.create_profile(
        tenant_id="tenant-a",
        participant_id=participant["participant_id"],
        access_expires_at="2030-01-01T00:00:00+00:00",
        actor_ref="manager-a",
    )

    with pytest.raises(FAVPActivationError, match="invitation_not_found"):
        FAVPParticipantActivationService(operations, execution, audit).activate(
            tenant_id="tenant-a",
            participant_id=participant["participant_id"],
            profile_id=profile["profile_id"],
            actor_ref="manager-a",
            operator_confirmation=True,
        )


def test_activation_rejects_a_participant_from_another_tenant(tmp_path):
    db = DatabaseConnection(tmp_path / "activation-wrong-tenant.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    audit = AuditService(db)
    operations = FAVPOperationsService(FAVPOperationsRepository(db), audit)
    execution = FAVPExecutionService(operations, audit)
    organization = operations.create_organization(
        tenant_id="tenant-a", organization_ref="org-a", display_name="Org A", actor_ref="manager-a"
    )
    participant = operations.create_participant(
        tenant_id="tenant-a", organization_id=organization["organization_id"],
        participant_ref="participant-a", display_name="Participant A",
        actor_identity_ref="actor-a", actor_ref="manager-a",
    )
    invitation = operations.record_invitation(
        tenant_id="tenant-a", participant_id=participant["participant_id"],
        invitation_ref="invitation-a", channel="operator_handoff", status="SENT", actor_ref="manager-a",
    )
    profile = execution.create_profile(
        tenant_id="tenant-a", participant_id=participant["participant_id"],
        access_expires_at="2030-01-01T00:00:00+00:00", actor_ref="manager-a",
    )

    with pytest.raises(FAVPActivationError, match="participant_not_found"):
        FAVPParticipantActivationService(operations, execution, audit).activate(
            tenant_id="tenant-b", participant_id=participant["participant_id"],
            profile_id=profile["profile_id"], invitation_id=invitation["invitation_id"],
            actor_ref="manager-b", operator_confirmation=True,
        )


def test_synthetic_activation_is_tenant_scoped_and_atomic_on_audit_failure(tmp_path, monkeypatch):
    _environment(monkeypatch)
    db = DatabaseConnection(tmp_path / "activation-security.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    monkeypatch.setattr(onboarding, "database_for_environment", lambda require_postgresql: db)
    monkeypatch.setattr(activation, "database_for_environment", lambda require_postgresql: db)
    invited = onboarding.onboard(_args())

    with pytest.raises(RuntimeError):
        activation.activate(_args(tenant_id="another-tenant"))
    with db.session() as connection:
        assert connection.execute("SELECT state FROM favp_participants WHERE participant_id=?", (invited["participant_id"],)).fetchone()[0] == "INVITED"

    original_record = AuditService.record
    def fail_on_activation(self, event_type, *args, **kwargs):
        if event_type == "FAVP_PARTICIPANT_ACTIVATED":
            raise RuntimeError("activation_audit_failure")
        return original_record(self, event_type, *args, **kwargs)
    monkeypatch.setattr(AuditService, "record", fail_on_activation)
    with pytest.raises(RuntimeError, match="activation_audit_failure"):
        activation.activate(_args())
    with db.session() as connection:
        state = connection.execute("SELECT state FROM favp_participants WHERE participant_id=?", (invited["participant_id"],)).fetchone()[0]
        event_types = {row[0] for row in connection.execute("SELECT event_type FROM audit_events WHERE tenant_id=?", (onboarding.SYNTHETIC_TENANT_ID,)).fetchall()}
    assert state == "INVITED"
    assert "FAVP_PARTICIPANT_ACTIVATED" not in event_types


def test_synthetic_onboarding_clears_only_participant_readiness_blocker(
    tmp_path, monkeypatch
):
    _environment(monkeypatch)
    db = DatabaseConnection(tmp_path / "readiness.sqlite")
    assert MigrationRunner(db, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    monkeypatch.setattr(onboarding, "database_for_environment", lambda require_postgresql: db)
    monkeypatch.setattr(activation, "database_for_environment", lambda require_postgresql: db)
    audit = AuditService(db)
    audit.record(
        "FAVP_STAGING_BASELINE",
        tenant_id="staging-bootstrap",
        actor_id="staging-operator",
        resource_type="favp_staging",
        resource_id="baseline",
        operation="staging_baseline_recorded",
        outcome="success",
    )

    def readiness():
        operations = FAVPOperationsService(FAVPOperationsRepository(db), audit)
        execution = FAVPExecutionService(operations, audit)
        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir(exist_ok=True)
        return FAVPStagingLaunchReadiness(
            db,
            audit,
            execution,
            environ={
                "SENTINEL_DNA_ENV": "staging",
                "SENTINEL_DNA_FAVP_OPERATIONS_ENABLED": "1",
                "SENTINEL_DNA_FAVP_SYNTHETIC_ONLY": "1",
                "SENTINEL_DNA_FAVP_PRODUCTION_ACCESS": "0",
                "SENTINEL_DNA_CONFIG_SOURCE_CLASSIFICATION": "external_non_production",
                "SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION": "disposable_staging",
                "SENTINEL_DNA_TENANT_ISOLATION_ENABLED": "1",
                "SENTINEL_DNA_AUDIT_LOGGING_ENABLED": "1",
                "DATABASE_URL": "postgresql://sentinel@postgres:5432/sentinel_dna",
            },
            evidence_dir=evidence_dir,
            compose_path=ROOT / "deployment" / "staging" / "docker-compose.yml",
        ).check()

    before = readiness()
    before_blocked = set(before["summary"]["blocking_checks"])
    assert before["status"] == "FAVP_STAGING_LAUNCH_BLOCKED"
    assert "participant_onboarding" in before_blocked

    onboarding.onboard(_args())
    after_invitation = readiness()
    after_invitation_blocked = set(after_invitation["summary"]["blocking_checks"])
    assert "participant_onboarding" in after_invitation_blocked

    activated = activation.activate(_args())
    after = readiness()
    after_blocked = set(after["summary"]["blocking_checks"])

    assert activated["activation_performed"] is False
    assert after_blocked == before_blocked - {"participant_onboarding", "participant_activation_audit"}
    # The local fixture remains blocked by the deliberate PostgreSQL-only
    # staging gate; the activation-related readiness checks are now ready.
    assert next(item for item in after["checks"] if item["name"] == "participant_onboarding")["status"] == "PASS"
    assert next(item for item in after["checks"] if item["name"] == "participant_activation_audit")["status"] == "PASS"
    assert after["status"] == "FAVP_STAGING_LAUNCH_BLOCKED"
    assert after["environment"]["synthetic_only"] is True
    assert after["environment"]["production_access"] == "0"
    assert after["launch_gate"]["human_program_owner_authorization_required"] is True
    assert after["launch_gate"]["activation_performed"] is False


def test_synthetic_onboarding_requires_explicit_confirmation(tmp_path, monkeypatch):
    _environment(monkeypatch)
    monkeypatch.setattr(
        onboarding,
        "database_for_environment",
        lambda require_postgresql: DatabaseConnection(tmp_path / "favp.sqlite"),
    )

    with pytest.raises(RuntimeError, match="operator-confirmation"):
        onboarding.onboard(_args(operator_confirmation=False))


def test_synthetic_onboarding_refuses_non_synthetic_environment(monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "staging")
    monkeypatch.setenv("SENTINEL_DNA_FAVP_OPERATIONS_ENABLED", "1")
    monkeypatch.setenv("SENTINEL_DNA_FAVP_SYNTHETIC_ONLY", "0")
    monkeypatch.setenv("SENTINEL_DNA_FAVP_PRODUCTION_ACCESS", "0")
    monkeypatch.setenv("SENTINEL_DNA_AUDIT_LOGGING_ENABLED", "1")
    monkeypatch.setenv("SENTINEL_DNA_TENANT_ISOLATION_ENABLED", "1")

    with pytest.raises(RuntimeError, match="SENTINEL_DNA_FAVP_SYNTHETIC_ONLY"):
        onboarding.onboard(_args())


@pytest.mark.parametrize(
    ("missing_field", "message"),
    [
        ("tenant_id", "tenant-id is required"),
        ("actor_ref", "actor-ref is required"),
        ("actor_identity_ref", "actor-identity-ref is required"),
        ("participant_ref", "participant-ref is required"),
        ("participant_name", "participant-name is required"),
        ("invitation_ref", "invitation-ref is required"),
        ("access_expires_at", "access-expires-at is required"),
    ],
)
def test_real_onboarding_rejects_missing_required_fields_before_writes(
    monkeypatch, missing_field, message
):
    _environment(monkeypatch)
    monkeypatch.setattr(
        onboarding,
        "database_for_environment",
        lambda require_postgresql: pytest.fail("database must not be opened"),
    )
    args = Namespace(
        synthetic=False,
        operator_confirmation=True,
        tenant_id="",
        actor_ref="",
        actor_identity_ref="",
        participant_ref="",
        participant_name="",
        organization_id=None,
        create_organization=False,
        organization_ref=None,
        organization_name=None,
        sector=None,
        size_band=None,
        role_title=None,
        contact_reference=None,
        invitation_ref="",
        invitation_channel=None,
        access_expires_at="",
    )
    args.tenant_id = "tenant-a"
    args.actor_ref = "manager-a"
    args.actor_identity_ref = "actor-a"
    args.participant_ref = "participant-a"
    args.participant_name = "Synthetic Test Participant"
    args.invitation_ref = "invitation-a"
    args.invitation_channel = "operator_handoff"
    args.access_expires_at = "2030-01-01T00:00:00+00:00"
    setattr(args, missing_field, "")

    with pytest.raises(RuntimeError, match=message):
        onboarding.onboard(args)


def test_onboarding_rejects_production_before_any_write(monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.setenv("SENTINEL_DNA_FAVP_OPERATIONS_ENABLED", "1")
    monkeypatch.setenv("SENTINEL_DNA_FAVP_SYNTHETIC_ONLY", "1")
    monkeypatch.setenv("SENTINEL_DNA_FAVP_PRODUCTION_ACCESS", "0")
    monkeypatch.setenv("SENTINEL_DNA_AUDIT_LOGGING_ENABLED", "1")
    monkeypatch.setenv("SENTINEL_DNA_TENANT_ISOLATION_ENABLED", "1")
    monkeypatch.setattr(
        onboarding,
        "_services",
        lambda: pytest.fail("production onboarding must not open services"),
    )

    with pytest.raises(RuntimeError, match="SENTINEL_DNA_ENV=staging"):
        onboarding.onboard(_args())
