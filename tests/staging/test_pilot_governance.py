import json

from deployment.staging.scripts.validate_pilot_governance import validate


def test_pilot_governance_blocks_without_external_authority(tmp_path):
    checklist = tmp_path / "checklist.json"
    checklist.write_text(json.dumps({
        "decision": "BLOCKED",
        "items": [{"control": "Gate 4", "status": "BLOCKED"}],
    }), encoding="utf-8")
    result = validate(checklist)
    assert result["status"] == "BLOCKED"
    assert result["authorizes_pilot"] is False
    assert "external_authority:external_verification_required" in result["errors"]


def test_pilot_governance_rejects_ready_with_unmeasured_control(tmp_path):
    checklist = tmp_path / "checklist.json"
    checklist.write_text(json.dumps({
        "decision": "READY",
        "external_authority_status": "EXTERNALLY_VERIFIED",
        "items": [
            {"control": "Gate 4", "status": "READY"},
            {"control": "Tenant isolation", "status": "NOT_MEASURED"},
        ],
    }), encoding="utf-8")
    result = validate(checklist)
    assert result["status"] == "BLOCKED"
    assert result["authorizes_pilot"] is False
