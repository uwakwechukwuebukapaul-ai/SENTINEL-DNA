"""Security-contract checks for the local two-human ceremony."""

import json
from pathlib import Path

from flask import Flask

from services.auth.local_two_human_staging_ceremony import EXPECTED_RELEASE, local_two_human_ceremony_api


def test_release_constants_are_exact():
    assert EXPECTED_RELEASE == {
        "application_commit": "e5a71f16a56e2cddf7c4c3c3295aaa53eee10f38",
        "repository_tree": "8577fadc6c1dedb665f57f0c82378f4613d71a1e",
        "image_digest": "sha256:b4aaede8c74ab0609ce3932b16e42980eb1793c42590e77766c400afffe952ed",
        "environment": "staging",
        "database_target_identity": "postgresql://sentinel@postgres:5432/sentinel_dna",
    }


def test_source_contains_no_enrollment_call():
    source = Path("services/auth/local_two_human_staging_ceremony.py").read_text(encoding="utf-8")
    assert "StagingAuthorityEnrollmentService" not in source
    assert "def enroll" not in source


def test_source_does_not_store_raw_mfa_token_or_private_key():
    source = Path("services/auth/local_two_human_staging_ceremony.py").read_text(encoding="utf-8").lower()
    assert "private_key" not in source
    assert "mfa_session_token" in source
    assert "insert into staging_two_human_approvals" in source
    assert "mfa_session_reference_hash" in source


def test_documented_identity_limitation_is_present():
    doc = Path("docs/staging/LOCAL_TWO_HUMAN_CEREMONY.md").read_text(encoding="utf-8")
    assert "does **not** prove that two separate real-world humans" in doc


def test_mutating_route_requires_csrf_before_service_access():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.register_blueprint(local_two_human_ceremony_api)
    response = app.test_client().post(
        "/api/staging/authority-ceremony",
        json={"release_confirmation": {}},
    )
    assert response.status_code == 403
    assert response.get_json()["error"] == "csrf_validation_failed"
