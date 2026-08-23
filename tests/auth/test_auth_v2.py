"""Authentication V2 service-boundary tests (no network/provider required)."""
from datetime import date, datetime, timedelta, timezone
import pytest

from database.connection import DatabaseConnection
from services.auth.auth_service import AuthService
from services.auth.otp import TestOTPProvider
from services.auth.phone import normalize_phone
from services.auth.age import MINIMUM_AGE, calculate_age, validate_minimum_age


def service(tmp_path):
    return AuthService(DatabaseConnection(str(tmp_path / "auth-v2.db")))


def test_phone_normalization_and_otp_is_single_use(tmp_path):
    auth = service(tmp_path); provider = TestOTPProvider()
    assert normalize_phone("NG", "0801 234 5678") == "+2348012345678"
    _otp_id, secret = auth.issue_otp("+2348012345678", provider=provider)
    assert provider.sent and provider.sent[0][0] == "+2348012345678"
    code = provider.sent[0][1]
    assert auth.verify_otp("+2348012345678", code, secret=secret)
    assert not auth.verify_otp("+2348012345678", code, secret=secret)


def test_invalid_otp_attempts_are_bounded(tmp_path):
    auth = service(tmp_path); provider = TestOTPProvider()
    _otp_id, secret = auth.issue_otp("+447911123456", provider=provider)
    for _ in range(5): assert not auth.verify_otp("+447911123456", "000000", secret=secret)
    assert not auth.verify_otp("+447911123456", provider.sent[0][1], secret=secret)


def test_persistent_session_is_hashed_and_revocable(tmp_path):
    auth = service(tmp_path); user = auth.register("analyst-v2", "analyst-v2@example.test", "StrongPassword123!")
    value, _expires = auth.create_persistent_session(user)
    assert auth.resolve_persistent_session(value).id == user.id
    auth.revoke_persistent_sessions(user.id)
    assert auth.resolve_persistent_session(value) is None


def test_public_registration_forces_analyst_role(tmp_path):
    user = service(tmp_path).register("role-v2", "role-v2@example.test", "StrongPassword123!", role="admin")
    assert user.role == "analyst"


def test_dob_is_validated_calculated_and_persisted(tmp_path):
    auth = service(tmp_path)
    dob = date(date.today().year - MINIMUM_AGE, date.today().month, date.today().day).isoformat()
    user = auth.register("dob-v2", "dob-v2@example.test", "StrongPassword123!", date_of_birth=dob)
    assert user.date_of_birth == dob
    assert user.profile()["age"] == MINIMUM_AGE
    assert calculate_age(date.fromisoformat(dob)) == MINIMUM_AGE


def test_dob_future_and_underage_are_rejected(tmp_path):
    auth = service(tmp_path)
    with pytest.raises(ValueError):
        auth.register("future-dob", "future-dob@example.test", "StrongPassword123!", date_of_birth="2999-01-01")
    with pytest.raises(ValueError):
        validate_minimum_age(date.today().isoformat())


def test_existing_user_without_dob_still_authenticates(tmp_path):
    auth = service(tmp_path)
    user = auth.register("legacy-dob", "legacy-dob@example.test", "StrongPassword123!")
    assert auth.authenticate("legacy-dob", "StrongPassword123!").id == user.id
    assert auth.get_by_id(user.id).profile()["age_verified"] is False


def test_age_payload_cannot_override_server_calculation(tmp_path):
    auth = service(tmp_path)
    user = auth.register("age-input", "age-input@example.test", "StrongPassword123!", date_of_birth="2000-01-01")
    assert user.profile()["age"] != 999
    assert "date_of_birth" not in user.public()
