from datetime import datetime, timedelta, timezone

import pytest

from database.connection import DatabaseConnection
from database.errors import DatabaseError
from services.audit.service import AuditService
from services.favp_operations import (
    FAVP_PROGRAM_STATES,
    FAVP_SCENARIOS,
    FAVPOperationsError,
    FAVPOperationsRepository,
    FAVPOperationsService,
)


def make_service(tmp_path):
    db = DatabaseConnection(tmp_path / "favp.sqlite")
    audit = AuditService(db)
    service = FAVPOperationsService(FAVPOperationsRepository(db), audit, platform_build_version="build-test-1")
    return service, db


def make_program(tmp_path):
    service, db = make_service(tmp_path)
    organization = service.create_organization(
        tenant_id="tenant-a",
        organization_ref="org-ref-a",
        display_name="Sanitized Organization A",
        actor_ref="manager-a",
    )
    participant = service.create_participant(
        tenant_id="tenant-a",
        organization_id=organization["organization_id"],
        participant_ref="analyst-ref-a",
        display_name="Analyst A",
        actor_identity_ref="analyst-actor-a",
        role_title="SOC analyst",
        contact_reference="approved-contact-ref-a",
        actor_ref="manager-a",
    )
    for state in ("APPLIED", "SCREENING", "ACCEPTED", "ONBOARDING", "ACTIVE_VALIDATION"):
        participant = service.transition_participant(
            tenant_id="tenant-a",
            participant_id=participant["participant_id"],
            to_state=state,
            actor_ref="manager-a",
        )
    return service, db, organization, participant


def result_input():
    started = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    completed = started + timedelta(minutes=12)
    return {
        "started_at": started.isoformat(),
        "completed_at": completed.isoformat(),
        "analyst_decision": "Escalate for human review based on the linked synthetic observations.",
        "ai_recommendation": {"summary": "Review the linked observations", "confidence": 0.72},
        "evidence_references": [
            {"reference_id": "synthetic:evidence:1", "sha256": "a" * 64},
            {"reference_id": "synthetic:timeline:1", "sha256": "b" * 64},
        ],
        "provenance_references": ["catalog:FAVP-SCN-001", "fixture:sanitized-package-v1"],
        "features_used": ["timeline", "ioc_enrichment"],
        "limitations": ["No production telemetry was used."],
        "ai_investigation_version": "ai-investigation-test-1",
        "platform_build_version": "build-test-1",
    }


def test_catalog_contains_exactly_ten_synthetic_scenarios():
    assert len(FAVP_SCENARIOS) == 10
    assert all(item["synthetic"] for item in FAVP_SCENARIOS.values())
    assert all(item["evidence_package"]["contains_customer_data"] is False for item in FAVP_SCENARIOS.values())


def test_state_machine_and_requirements_are_explicit(tmp_path):
    service, _db, _organization, participant = make_program(tmp_path)
    updated = service.update_participation_requirements(
        tenant_id="tenant-a",
        participant_id=participant["participant_id"],
        actor_ref="manager-a",
        nda_status="ACCEPTED",
        terms_status="ACCEPTED",
        onboarding_status="COMPLETED",
    )
    assert updated["state"] == "ACTIVE_VALIDATION"
    assert updated["access_status"] == "ACTIVE"
    assert updated["nda_status"] == "ACCEPTED"
    assert updated["validation_phase"] == "ACTIVE_VALIDATION"
    with pytest.raises(FAVPOperationsError, match="invalid_program_state_transition"):
        service.transition_participant(
            tenant_id="tenant-a",
            participant_id=participant["participant_id"],
            to_state="INVITED",
            actor_ref="manager-a",
        )
    assert set(FAVP_PROGRAM_STATES) == {
        "INVITED", "APPLIED", "SCREENING", "ACCEPTED", "ONBOARDING",
        "ACTIVE_VALIDATION", "COMPLETED", "DESIGN_PARTNER_CANDIDATE",
        "DECLINED", "REVOKED",
    }


def test_workspace_result_feedback_kpis_and_report_are_evidence_based(tmp_path):
    service, db, _organization, participant = make_program(tmp_path)
    participant_id = participant["participant_id"]
    service.assign_scenario(
        tenant_id="tenant-a", participant_id=participant_id,
        scenario_id="FAVP-SCN-001", actor_ref="manager-a",
    )
    result = service.record_result(
        tenant_id="tenant-a", participant_id=participant_id,
        scenario_id="FAVP-SCN-001", actor_ref=participant_id,
        **result_input(),
    )
    assert result["analyst_decision"] != result["ai_recommendation"]["summary"]
    assert result["ai_recommendation"]["advisory_only"] is True
    assert result["duration_seconds"] == 720.0
    assert len(service.repository.list_evidence("tenant-a")) == 2
    feedback = service.record_feedback(
        tenant_id="tenant-a", participant_id=participant_id,
        scenario_id="FAVP-SCN-001", result_id=result["result_id"], actor_ref=participant_id,
        scores={field: 4 for field in ("trust_evidence", "reasoning_understanding", "confidence_rating", "provenance_clarity", "timeline_usefulness", "ioc_enrichment_usefulness", "evidence_quality")},
        would_pay=True, requested_tier="PROFESSIONAL",
        requested_integrations=["SIEM reference connector"],
        deployment_requirements=["private network path"],
        incorrect_reasoning="None identified", limitations="Synthetic scope only", comments="Useful timeline",
    )
    assert feedback["would_pay"] == 1
    kpis = service.kpis(tenant_id="tenant-a")
    assert kpis["data_status"] == "measured"
    assert kpis["program"]["active_participants"] == 1
    assert kpis["product"]["investigations_completed"] == 1
    assert kpis["product"]["trust_score"] == 4.0
    assert kpis["commercial"]["pilot_interest_signals"] == 1
    report = service.report(tenant_id="tenant-a", generated_by="manager-a")
    assert report["report_type"] == "FAVP Validation Report"
    assert report["synthetic_only"] is True
    assert report["evidence_quality_assessment"]["raw_evidence_stored"] is False
    with db.session() as connection:
        audit = connection.execute("SELECT COUNT(*) AS count FROM audit_events WHERE tenant_id=?", ("tenant-a",)).fetchone()
    assert audit["count"] >= 6


def test_tenant_isolation_and_participant_ownership_fail_closed(tmp_path):
    service, _db, _organization, participant = make_program(tmp_path)
    with pytest.raises(FAVPOperationsError, match="participant_not_found"):
        service.workspace(tenant_id="tenant-b", participant_id=participant["participant_id"])
    assert service.workspace(tenant_id="tenant-a", participant_id=participant["participant_id"], actor_identity_ref="analyst-actor-a")["synthetic_only"] is True
    with pytest.raises(FAVPOperationsError, match="participant_workspace_forbidden"):
        service.workspace(tenant_id="tenant-a", participant_id=participant["participant_id"], actor_identity_ref="other-analyst")
    with pytest.raises(FAVPOperationsError, match="organization_not_found"):
        service.create_participant(
            tenant_id="tenant-b", organization_id="missing", participant_ref="x",
            display_name="X", actor_ref="manager-b",
        )


def test_sensitive_data_and_autonomous_actions_are_rejected(tmp_path):
    service, _db, _organization, participant = make_program(tmp_path)
    participant_id = participant["participant_id"]
    service.assign_scenario(tenant_id="tenant-a", participant_id=participant_id, scenario_id="FAVP-SCN-001", actor_ref="manager-a")
    with pytest.raises(FAVPOperationsError, match="sensitive_data_prohibited"):
        service.record_result(
            tenant_id="tenant-a", participant_id=participant_id, scenario_id="FAVP-SCN-001", actor_ref=participant_id,
            **{**result_input(), "ai_recommendation": {"summary": "x", "password": "not allowed"}},
        )
    with pytest.raises(FAVPOperationsError, match="ai_must_remain_advisory"):
        service.record_result(
            tenant_id="tenant-a", participant_id=participant_id, scenario_id="FAVP-SCN-001", actor_ref=participant_id,
            **{**result_input(), "ai_recommendation": {"summary": "isolate host", "autonomous_action": True}},
        )


def test_revocation_blocks_future_work_and_rows_are_append_only(tmp_path):
    service, db, _organization, participant = make_program(tmp_path)
    participant_id = participant["participant_id"]
    service.transition_participant(tenant_id="tenant-a", participant_id=participant_id, to_state="REVOKED", actor_ref="manager-a", notes="validation access ended")
    with pytest.raises(FAVPOperationsError, match="participant_not_active_validation"):
        service.assign_scenario(tenant_id="tenant-a", participant_id=participant_id, scenario_id="FAVP-SCN-001", actor_ref="manager-a")
    with pytest.raises(DatabaseError):
        with db.session() as connection:
            connection.execute("UPDATE favp_timeline SET notes='tampered' WHERE tenant_id=?", ("tenant-a",))
    with pytest.raises(DatabaseError):
        with db.session() as connection:
            connection.execute("DELETE FROM favp_timeline WHERE tenant_id=?", ("tenant-a",))
