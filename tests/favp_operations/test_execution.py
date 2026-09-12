from datetime import datetime, timedelta, timezone

import pytest

from database.connection import DatabaseConnection
from database.errors import DatabaseError
from services.audit.service import AuditService
from services.favp_operations import (
    FAVPOperationsRepository,
    FAVPOperationsService,
    FAVPExecutionError,
    FAVPExecutionService,
    FAVPExecutionReadiness,
    FAVP_EXECUTION_SCENARIOS,
)


def build(tmp_path):
    db = DatabaseConnection(tmp_path / "favp-execution.sqlite")
    audit = AuditService(db)
    operations = FAVPOperationsService(FAVPOperationsRepository(db), audit, platform_build_version="build-execution-test")
    execution = FAVPExecutionService(operations, audit)
    organization = operations.create_organization(tenant_id="tenant-a", organization_ref="org-a", display_name="Sanitized Org A", actor_ref="manager-a")
    participant = operations.create_participant(tenant_id="tenant-a", organization_id=organization["organization_id"], participant_ref="participant-a", display_name="Analyst A", actor_identity_ref="actor-a", actor_ref="manager-a")
    return db, audit, operations, execution, participant


def activate(execution, participant):
    profile = execution.create_profile(tenant_id="tenant-a", participant_id=participant["participant_id"], access_expires_at=(datetime.now(timezone.utc) + timedelta(days=30)).isoformat(), actor_ref="manager-a")
    execution.update_compliance(tenant_id="tenant-a", profile_id=profile["profile_id"], actor_ref="manager-a", nda_status="ACCEPTED", terms_status="ACCEPTED", onboarding_status="COMPLETED")
    for state in ("APPLIED", "APPROVED", "ONBOARDED", "ACTIVE"):
        profile = execution.transition_profile(tenant_id="tenant-a", profile_id=profile["profile_id"], to_state=state, actor_ref="manager-a")
    return profile


def test_readiness_requires_explicit_non_production_activation(tmp_path):
    db, audit, _operations, _execution, _participant = build(tmp_path)
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    values = {
        "SENTINEL_DNA_ENV": "testing",
        "SENTINEL_DNA_FAVP_OPERATIONS_ENABLED": "1",
        "SENTINEL_DNA_FAVP_SYNTHETIC_ONLY": "1",
        "SENTINEL_DNA_FAVP_PRODUCTION_ACCESS": "0",
        "SENTINEL_DNA_TENANT_ISOLATION_ENABLED": "1",
        "SENTINEL_DNA_AUDIT_LOGGING_ENABLED": "1",
    }
    ready = FAVPExecutionReadiness(db, audit, evidence_dir=evidence_dir, environ=values).check()
    assert ready["status"] == "READY_FOR_FAVP_EXECUTION"
    values.pop("SENTINEL_DNA_FAVP_OPERATIONS_ENABLED")
    blocked = FAVPExecutionReadiness(db, audit, evidence_dir=evidence_dir, environ=values).check()
    assert blocked["status"] == "BLOCKED_WITH_REASON"
    assert any(item["name"] == "operations_feature_flag" and item["status"] == "BLOCKED" for item in blocked["checks"])


def test_execution_profile_state_machine_requires_compliance_and_expiry(tmp_path):
    _db, _audit, _operations, execution, participant = build(tmp_path)
    profile = execution.create_profile(tenant_id="tenant-a", participant_id=participant["participant_id"], access_expires_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(), actor_ref="manager-a")
    for state in ("APPLIED", "APPROVED"):
        profile = execution.transition_profile(tenant_id="tenant-a", profile_id=profile["profile_id"], to_state=state, actor_ref="manager-a")
    with pytest.raises(FAVPExecutionError, match="nda_and_terms_acceptance_required"):
        execution.transition_profile(tenant_id="tenant-a", profile_id=profile["profile_id"], to_state="ONBOARDED", actor_ref="manager-a")
    execution.update_compliance(tenant_id="tenant-a", profile_id=profile["profile_id"], actor_ref="manager-a", nda_status="ACCEPTED", terms_status="ACCEPTED", onboarding_status="COMPLETED")
    execution.transition_profile(tenant_id="tenant-a", profile_id=profile["profile_id"], to_state="ONBOARDED", actor_ref="manager-a")
    profile = execution.transition_profile(tenant_id="tenant-a", profile_id=profile["profile_id"], to_state="ACTIVE", actor_ref="manager-a")
    assert profile["state"] == "ACTIVE"


def test_scenario_execution_preserves_analyst_authority_and_validates_evidence(tmp_path):
    _db, _audit, _operations, execution, participant = build(tmp_path)
    profile = activate(execution, participant)
    assert len(execution.list_scenarios()) == 8
    session = execution.start_session(tenant_id="tenant-a", profile_id=profile["profile_id"], scenario_id="FAVP-EXE-001", actor_ref="actor-a", ai_investigation_version="ai-v1", platform_build_version="build-v1")
    review = execution.submit_review(tenant_id="tenant-a", session_id=session["session_id"], actor_ref="actor-a", analyst_decision="Escalate after reviewing the synthetic timeline", ai_recommendation={"summary": "Review the timeline", "confidence": 0.8}, disagreement=True, confidence_score=4, usability_score=5, explanation_usefulness=4, uncertainty_reported=True, features_used=["timeline", "provenance"])
    assert review["analyst_decision"] != review["ai_recommendation"]["summary"]
    assert review["ai_recommendation"]["advisory_only"] is True
    statuses = {field: "PASS" for field in ("evidence_completeness", "provenance_integrity", "timestamp_consistency", "chain_of_custody", "reproducibility", "ai_explanation_quality", "uncertainty_reporting")}
    validation = execution.validate_evidence(tenant_id="tenant-a", session_id=session["session_id"], evidence_reference="synthetic:FAVP-EXE-001:bundle", provenance_reference="catalog:FAVP-EXE-001:v1", statuses=statuses, validator_ref="validator-a", actor_ref="manager-a")
    assert execution.verify_evidence_validation(tenant_id="tenant-a", validation_id=validation["validation_id"])
    dashboard = execution.progress_dashboard(tenant_id="tenant-a")
    assert dashboard["usage"]["investigations_completed"] == 1
    assert dashboard["trust"]["evidence_confidence"] == 4.0
    assert dashboard["limitations"]["disagreements_recorded"] == 1
    organization_report = execution.organization_summary(tenant_id="tenant-a")
    assert set(("observed_evidence", "analyst_feedback", "system_measurements", "limitations", "future_improvements")).issubset(organization_report)


def test_execution_tenant_isolation_revocation_and_append_only_validation(tmp_path):
    _db, _audit, _operations, execution, participant = build(tmp_path)
    profile = activate(execution, participant)
    session = execution.start_session(tenant_id="tenant-a", profile_id=profile["profile_id"], scenario_id="FAVP-EXE-001", actor_ref="actor-a", ai_investigation_version="ai-v1", platform_build_version="build-v1")
    execution.submit_review(tenant_id="tenant-a", session_id=session["session_id"], actor_ref="actor-a", analyst_decision="Analyst decision", ai_recommendation={"summary": "Review", "advisory_only": True}, disagreement=False, confidence_score=3, usability_score=3, explanation_usefulness=3, uncertainty_reported=True, features_used=["timeline"])
    statuses = {field: "PASS" for field in ("evidence_completeness", "provenance_integrity", "timestamp_consistency", "chain_of_custody", "reproducibility", "ai_explanation_quality", "uncertainty_reporting")}
    execution.validate_evidence(tenant_id="tenant-a", session_id=session["session_id"], evidence_reference="synthetic:bundle", provenance_reference="catalog:FAVP-EXE-001:v1", statuses=statuses, validator_ref="validator-a", actor_ref="manager-a")
    with pytest.raises(FAVPExecutionError, match="execution_profile_not_found"):
        execution.workspace(tenant_id="tenant-b", profile_id=profile["profile_id"], actor_ref="actor-a")
    with pytest.raises(FAVPExecutionError, match="execution_profile_forbidden"):
        execution.workspace(tenant_id="tenant-a", profile_id=profile["profile_id"], actor_ref="other-actor")
    revoked = execution.revoke_profile(tenant_id="tenant-a", profile_id=profile["profile_id"], actor_ref="manager-a")
    assert revoked["state"] == "REVOKED"
    with pytest.raises(FAVPExecutionError, match="execution_profile_not_active"):
        execution.start_session(tenant_id="tenant-a", profile_id=profile["profile_id"], scenario_id="FAVP-EXE-001", actor_ref="actor-a", ai_investigation_version="ai-v1", platform_build_version="build-v1")
    with pytest.raises(DatabaseError):
        with execution.db.session() as connection:
            connection.execute("UPDATE favp_evidence_validations SET validator_ref='tampered' WHERE tenant_id=?", ("tenant-a",))


def test_ai_boundary_and_final_report_template_do_not_fabricate(tmp_path):
    _db, _audit, _operations, execution, _participant = build(tmp_path)
    assert execution.final_report_template(tenant_id="tenant-a")["data_status"] == "template_not_filled"
    profile = activate(execution, _participant)
    session = execution.start_session(tenant_id="tenant-a", profile_id=profile["profile_id"], scenario_id="FAVP-EXE-002", actor_ref="actor-a", ai_investigation_version="ai-v1", platform_build_version="build-v1")
    with pytest.raises(FAVPExecutionError, match="sensitive_data_prohibited"):
        execution.submit_review(tenant_id="tenant-a", session_id=session["session_id"], actor_ref="actor-a", analyst_decision="Analyst decision", ai_recommendation={"password": "blocked"}, disagreement=False, confidence_score=3, usability_score=3, explanation_usefulness=3, uncertainty_reported=True, features_used=["timeline"])
    with pytest.raises(FAVPExecutionError, match="ai_must_remain_advisory"):
        execution.submit_review(tenant_id="tenant-a", session_id=session["session_id"], actor_ref="actor-a", analyst_decision="Analyst decision", ai_recommendation={"autonomous_action": True}, disagreement=False, confidence_score=3, usability_score=3, explanation_usefulness=3, uncertainty_reported=True, features_used=["timeline"])
