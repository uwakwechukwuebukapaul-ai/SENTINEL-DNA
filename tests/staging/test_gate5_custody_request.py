import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from deployment.staging.scripts.verify_gate5_custody_request import (
    request_hash,
    verify_external_authorization,
    verify_package,
    verify_request,
)


ROOT = Path(__file__).parents[2]
REQUEST_PATH = ROOT / "deployment/staging/GATE5_CUSTODY_REQUEST.json"
COMMIT = "4e35f0cb20cfab4779e1a567342e1855962ac58e"
IMAGE = "sentinel-dna:pilot-staging-candidate-4e35f0c"
DIGEST = "sha256:45ce0498839eb12fe07f08c9bb153bab5c9c7f2531b2b7a991f2ad1eec2e3995"
NOW = datetime(2026, 9, 10, 12, tzinfo=timezone.utc)


def request():
    return json.loads(REQUEST_PATH.read_text(encoding="utf-8"))


def test_current_candidate_request_is_valid_but_not_authorized():
    value = request()
    assert verify_request(value, expected_commit=COMMIT, expected_image_reference=IMAGE, expected_image_digest=DIGEST, now=NOW)["status"] == "PASS"
    result = verify_package(value, None, expected_commit=COMMIT, expected_image_reference=IMAGE, expected_image_digest=DIGEST, now=NOW)
    assert result == {"status": "BLOCKED", "errors": ["external_authorization:missing"], "authorizes_release": False}


def test_request_artifact_is_pending_and_integrity_bound():
    value = request()
    assert value["request_status"] == "PENDING_EXTERNAL_AUTHORIZATION"
    assert value["integrity"]["request_hash"] == request_hash(value)
    assert value["verifier_identity"] is None
    assert value["operator_approval_reference"] is None
    assert value["signature_reference"] is None
    assert value["candidate_branch"] == "gate5-controlled-pilot-activation"


def test_historical_digest_is_rejected():
    value = request()
    value["image_digest"] = "sha256:0ce1ef605201f5f8e2d5b47c0bffae3eaa13da68952a14229faf2c97477bacec"
    value["integrity"]["request_hash"] = request_hash(value)
    result = verify_request(value, expected_commit=COMMIT, expected_image_reference=IMAGE, expected_image_digest=DIGEST, now=NOW)
    assert "image_digest:mismatch" in result["errors"]
    assert "integrity:original_record_mismatch" in result["errors"]


def test_recomputed_hash_cannot_relabel_evidence_or_provenance():
    for field, replacement in (("evidence_reference", "historical-relabelled-artifact"), ("provenance_reference", ["historical-provenance"])):
        value = request()
        value[field] = replacement
        value["integrity"]["request_hash"] = request_hash(value)
        result = verify_request(value, expected_commit=COMMIT, expected_image_reference=IMAGE, expected_image_digest=DIGEST, now=NOW)
        assert result["status"] == "BLOCKED"
        assert "integrity:original_record_mismatch" in result["errors"] or f"{field}:mismatch" in result["errors"]


def test_wrong_digest_and_commit_are_rejected():
    value = request()
    result = verify_request(value, expected_commit="1" * 40, expected_image_reference=IMAGE, expected_image_digest="sha256:" + "1" * 64, now=NOW)
    assert "candidate_commit:mismatch" in result["errors"]
    assert "image_digest:mismatch" in result["errors"]
    result = verify_request(value, expected_commit=COMMIT, expected_image_reference="wrong-image", expected_image_digest=DIGEST, now=NOW)
    assert "image_reference:mismatch" in result["errors"]
    result = verify_request(value, expected_commit="2" * 40, expected_image_reference=IMAGE, expected_image_digest=DIGEST, now=NOW)
    assert "candidate_commit:mismatch" in result["errors"]


def external_authorization(value=None):
    value = value or request()
    return {
        "authorization_type": "GATE5_CUSTODY_AUTHORIZATION",
        "request_id": value["governance_package_id"],
        "candidate_commit": value["candidate_commit"],
        "repository": value["repository"],
        "image_reference": value["image_reference"],
        "image_digest": value["image_digest"],
        "issued_at": "2026-09-10T01:00:00Z",
        "expires_at": "2026-09-11T01:00:00Z",
        "rollback_reference": "external-rollback:gate5-001",
        "evidence_reference": "external-evidence:gate5-001",
        "verifier_identity": "release-security-authority:prod-1",
        "operator_approval_reference": "external-approval:gate5-001",
        "signature_reference": "external-signature:gate5-001",
        "integrity": {"algorithm": "sha256", "reference": "external-integrity:gate5-001"},
        "external_verification": {
            "status": "VERIFIED",
            "trust_root_reference": "external-trust-root:release-security",
            "evidence_reference": "external-evidence:gate5-001",
            "evidence_digest": "sha256:" + "a" * 64,
            "verification_method": "independent-release-verifier-v1",
        },
    }


def test_missing_authority_fields_are_rejected():
    value = external_authorization()
    for field in ("verifier_identity", "operator_approval_reference", "signature_reference", "integrity", "rollback_reference", "evidence_reference"):
        candidate = copy.deepcopy(value)
        candidate.pop(field)
        result = verify_external_authorization(request(), candidate, now=NOW, external_verifier=lambda _: True)
        assert result["status"] == "BLOCKED"
        assert any(field in error for error in result["errors"])


def test_expired_authorization_is_rejected():
    value = external_authorization()
    value["expires_at"] = "2026-09-09T01:00:00Z"
    result = verify_external_authorization(request(), value, now=NOW, external_verifier=lambda _: True)
    assert "authorization:expired" in result["errors"]


def test_repository_self_generated_or_unverifiable_authorization_is_rejected():
    value = external_authorization()
    value["verifier_identity"] = "repository-local-verifier"
    result = verify_external_authorization(request(), value, now=NOW, external_verifier=lambda _: True)
    assert "authorization.verifier_identity:external_identity_required" in result["errors"]
    value = external_authorization()
    result = verify_external_authorization(request(), value, now=NOW)
    assert result["errors"] == ["cryptographic_evidence_verifier:external_authority_required"]


def test_lambda_true_cannot_manufacture_external_authorization():
    value = request()
    authorization = external_authorization(value)
    blocked = verify_package(value, authorization, expected_commit=COMMIT, expected_image_reference=IMAGE, expected_image_digest=DIGEST, now=NOW)
    assert blocked["status"] == "BLOCKED"
    result = verify_package(value, authorization, expected_commit=COMMIT, expected_image_reference=IMAGE, expected_image_digest=DIGEST, now=NOW, external_verifier=lambda _: True)
    assert result["status"] == "BLOCKED"
    assert result["authorizes_release"] is False
    assert "external_verifier:repository_local_callable_forbidden" in result["errors"]


def test_missing_trust_root_and_rollback_are_rejected():
    authorization = external_authorization()
    authorization["external_verification"].pop("trust_root_reference")
    result = verify_external_authorization(request(), authorization, now=NOW)
    assert "external_verification.trust_root_reference:missing" in result["errors"]

    value = request()
    value["rollback_reference"] = ""
    value["integrity"]["request_hash"] = request_hash(value)
    result = verify_request(value, expected_commit=COMMIT, expected_image_reference=IMAGE, expected_image_digest=DIGEST, now=NOW)
    assert "rollback_reference:external_reference_required" in result["errors"]


def test_pending_status_has_no_local_promotion_path():
    value = request()
    for status in ("APPROVED", "AUTHORIZED", "READY_FOR_ANALYST_PILOT", "GATE_5A_PASS"):
        candidate = copy.deepcopy(value)
        candidate["request_status"] = status
        candidate["integrity"]["request_hash"] = request_hash(candidate)
        result = verify_request(candidate, expected_commit=COMMIT, expected_image_reference=IMAGE, expected_image_digest=DIGEST, now=NOW)
        assert result["status"] == "BLOCKED"
        assert "request_status:must_remain_pending" in result["errors"]


def test_historical_request_relabel_is_rejected():
    value = external_authorization()
    value["request_id"] = "historical-request-relabelled-as-current"
    result = verify_external_authorization(request(), value, now=NOW)
    assert "authorization.request_id:mismatch" in result["errors"]


def test_review_files_contain_no_secret_material():
    files = (
        ROOT / "deployment/staging/GATE5_CUSTODY_REQUEST.schema.json",
        ROOT / "deployment/staging/GATE5_CUSTODY_REQUEST.json",
        ROOT / "deployment/staging/scripts/verify_gate5_custody_request.py",
    )
    text = "\n".join(path.read_text(encoding="utf-8") for path in files).lower()
    assert "begin private key" not in text
    assert "client_secret=" not in text
    assert "mfa_code" not in text
    assert "password=" not in text
