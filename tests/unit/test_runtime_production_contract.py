import os
from pathlib import Path

import pytest

from config.runtime import RuntimeConfig


def _set_production(monkeypatch, tmp_path, secret="s" * 40):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", secret)
    monkeypatch.setenv("SENTINEL_DNA_SECURE_COOKIES", "1")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "soc.db"))


def test_omitted_environment_preserves_development_compatibility(monkeypatch):
    monkeypatch.delenv("SENTINEL_DNA_ENV", raising=False)
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECRET_KEY", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_DB_PATH", raising=False)
    monkeypatch.delenv("SENTINEL_DNA_SECURE_COOKIES", raising=False)

    config = RuntimeConfig.from_environment()

    assert config.environment == "development"
    config.validate()


def test_explicit_development_mode_remains_compatible(monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "development")
    config = RuntimeConfig.from_environment()
    config.validate()
    assert config.debug is True


def test_production_requires_explicit_database_path(monkeypatch, tmp_path):
    _set_production(monkeypatch, tmp_path)
    monkeypatch.delenv("SENTINEL_DNA_DB_PATH")

    with pytest.raises(RuntimeError, match="SENTINEL_DNA_DB_PATH"):
        RuntimeConfig.from_environment().validate()


def test_production_rejects_missing_or_default_secret(monkeypatch, tmp_path):
    _set_production(monkeypatch, tmp_path, secret="")
    with pytest.raises(RuntimeError, match="SENTINEL_DNA_SECRET_KEY"):
        RuntimeConfig.from_environment().validate()

    _set_production(monkeypatch, tmp_path, secret="development-only-secret")
    with pytest.raises(RuntimeError, match="SENTINEL_DNA_SECRET_KEY"):
        RuntimeConfig.from_environment().validate()


def test_production_rejects_insecure_cookie_setting(monkeypatch, tmp_path):
    _set_production(monkeypatch, tmp_path)
    monkeypatch.setenv("SENTINEL_DNA_SECURE_COOKIES", "0")

    with pytest.raises(RuntimeError, match="SENTINEL_DNA_SECURE_COOKIES"):
        RuntimeConfig.from_environment().validate()


def test_valid_production_config_is_debug_free_and_secure(monkeypatch, tmp_path):
    _set_production(monkeypatch, tmp_path)
    config = RuntimeConfig.from_environment()
    config.validate()

    assert config.debug is False
    assert config.secure_cookies is True
    assert Path(config.database_path).parent == tmp_path.resolve()


def test_production_rejects_unusable_database_location(monkeypatch, tmp_path):
    _set_production(monkeypatch, tmp_path)
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "missing" / "soc.db"))

    with pytest.raises(RuntimeError, match="usable database location"):
        RuntimeConfig.from_environment().validate()


def test_configuration_errors_do_not_expose_secret(monkeypatch, tmp_path):
    secret = "production-secret-that-must-not-appear"
    _set_production(monkeypatch, tmp_path, secret=secret)
    monkeypatch.setenv("SENTINEL_DNA_SECURE_COOKIES", "0")

    with pytest.raises(RuntimeError) as error:
        RuntimeConfig.from_environment().validate()

    assert secret not in str(error.value)
