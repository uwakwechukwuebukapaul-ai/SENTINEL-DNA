import inspect

from config.runtime import RuntimeConfig
from services.auth.auth_service import AuthService


def test_otp_secrets_have_no_development_default():
    issue_secret = inspect.signature(AuthService.issue_otp).parameters["secret"]
    verify_secret = inspect.signature(AuthService.verify_otp).parameters["secret"]

    assert issue_secret.default is inspect.Parameter.empty
    assert verify_secret.default is inspect.Parameter.empty


def test_otp_secret_is_required_for_direct_service_calls():
    service = object.__new__(AuthService)

    try:
        service.issue_otp("user@example.test", "login_email_otp")
    except TypeError as exc:
        assert "secret" in str(exc)
    else:  # pragma: no cover - the signature must reject omitted secrets
        raise AssertionError("issue_otp accepted an omitted secret")

    try:
        service.verify_otp("challenge", "000000")
    except TypeError as exc:
        assert "secret" in str(exc)
    else:  # pragma: no cover - the signature must reject omitted secrets
        raise AssertionError("verify_otp accepted an omitted secret")


def test_runtime_config_does_not_materialize_a_development_secret(monkeypatch):
    monkeypatch.delenv("SENTINEL_DNA_SECRET_KEY", raising=False)

    config = RuntimeConfig.from_environment()

    assert len(config.secret_key) >= 32
    assert config.secret_key not in {"development-only-secret", ""}
