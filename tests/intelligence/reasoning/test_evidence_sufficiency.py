from services.intelligence.reasoning.evidence_sufficiency import (
    EvidenceSufficiencyEvaluator,
    SufficiencyStatus,
)


def evaluate(result):
    return EvidenceSufficiencyEvaluator().evaluate(
        result, case_id="CASE-1", investigation_id="INV-1", tenant_id="tenant-a", correlation_id="CORR-1"
    )


def test_successful_canonical_result_is_sufficient_and_references_observed_evidence():
    result = evaluate({
        "success": True, "status": "completed",
        "evidence": [{"evidence_id": "E-2"}, {"evidence_id": "E-1"}],
    })
    assert result.status is SufficiencyStatus.SUFFICIENT
    assert result.supporting_evidence_ids == ("E-1", "E-2")
    assert result.input_evidence_digest


def test_insufficient_result_preserves_gap_and_safe_follow_up_recommendation():
    result = evaluate({
        "success": True, "status": "completed", "evidence": [{"evidence_id": "E-1"}],
        "evidence_sufficiency": "INSUFFICIENT", "evidence_gaps": ["host timeline"],
        "recommended_follow_up": {
            "capability": "evidence_lookup", "required_evidence": ["host timeline"],
            "authorization_reference": "policy:read-only-evidence",
        },
    })
    assert result.status is SufficiencyStatus.INSUFFICIENT
    assert result.evidence_gaps == ("host timeline",)
    assert result.recommended_follow_up["capability"] == "evidence_lookup"


def test_unknown_and_blocked_are_fail_closed():
    assert evaluate({"success": False, "status": "unavailable"}).status is SufficiencyStatus.UNKNOWN
    blocked = evaluate({
        "success": True, "status": "completed", "evidence_sufficiency": "INSUFFICIENT",
        "evidence_gaps": ["host timeline"], "supporting_evidence_ids": ["NOT-OBSERVED"],
    })
    assert blocked.status is SufficiencyStatus.BLOCKED


def test_invalid_status_is_blocked_and_no_evidence_is_invented():
    result = evaluate({
        "success": True, "status": "completed", "evidence_sufficiency": "MAYBE",
        "evidence": [{"evidence_id": "E-1"}],
    })
    assert result.status is SufficiencyStatus.BLOCKED
    assert result.supporting_evidence_ids == ()


def test_evaluation_digest_is_deterministic():
    payload = {
        "success": True, "status": "completed", "evidence": [{"evidence_id": "E-1"}],
        "evidence_sufficiency": "SUFFICIENT",
    }
    assert evaluate(payload).to_dict() == evaluate(payload).to_dict()
