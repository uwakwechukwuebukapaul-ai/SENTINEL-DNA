from pathlib import Path

import pytest

from config.runtime import RuntimeConfig
from services.core.pilot_boundary import pilot_path_allowed
from tests.credential_helpers import random_secret


ROOT = Path(__file__).resolve().parents[2]


def staging_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "staging")
    monkeypatch.setenv("SENTINEL_DNA_PILOT_ACCESS_REQUIRED", "1")
    monkeypatch.setenv("SENTINEL_DNA_SECURE_COOKIES", "1")
    monkeypatch.setenv("FLASK_DEBUG", "0")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", random_secret())
    monkeypatch.setenv(
        "SENTINEL_DNA_CONFIG_SOURCE_CLASSIFICATION", "external_non_production"
    )
    monkeypatch.setenv(
        "SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION", "disposable_staging"
    )
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://staging-user:staging-password@postgres:5432/sentinel"
    )
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "unused.sqlite"))


def test_staging_runtime_requires_external_secret_and_postgresql(monkeypatch, tmp_path):
    staging_environment(tmp_path, monkeypatch)
    config = RuntimeConfig.from_environment()
    config.validate()
    assert config.pilot_access_required is True
    assert config.database_url.startswith("postgresql://")

    monkeypatch.delenv("SENTINEL_DNA_SECRET_KEY")
    with pytest.raises(RuntimeError, match="SENTINEL_DNA_SECRET_KEY"):
        RuntimeConfig.from_environment().validate()

    staging_environment(tmp_path, monkeypatch)
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", random_secret())
    monkeypatch.setenv("DATABASE_URL", "sqlite:///production.sqlite")
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        RuntimeConfig.from_environment().validate()


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("SENTINEL_DNA_PILOT_ACCESS_REQUIRED", "0", "PILOT_ACCESS_REQUIRED"),
        ("SENTINEL_DNA_SECURE_COOKIES", "true", "SECURE_COOKIES"),
        ("FLASK_DEBUG", "1", "FLASK_DEBUG"),
        (
            "SENTINEL_DNA_CONFIG_SOURCE_CLASSIFICATION",
            "production",
            "CONFIG_SOURCE_CLASSIFICATION",
        ),
        (
            "SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION",
            "production",
            "DATABASE_TARGET_CLASSIFICATION",
        ),
    ],
)
def test_staging_runtime_rejects_missing_or_insecure_controls(
    monkeypatch, tmp_path, name, value, message
):
    staging_environment(tmp_path, monkeypatch)
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match=message):
        RuntimeConfig.from_environment().validate()


def test_pilot_boundary_is_allowlist_and_denies_non_pilot_surfaces():
    assert pilot_path_allowed("/workspace/investigation/CASE-1", "GET")
    assert pilot_path_allowed("/api/investigations/CASE-1/feedback", "POST")
    assert pilot_path_allowed("/api/auth/logout", "POST")

    for path in (
        "/api/automation/history",
        "/api/automation/execute",
        "/api/soc/dashboard",
        "/api/incidents",
        "/api/organizations/users",
        "/api/auth/sessions",
        "/workspace/live",
        "/workspace/analyst/CASE-1/start",
    ):
        assert not pilot_path_allowed(path, "GET")


def test_staging_compose_and_deploy_contract_are_explicit():
    compose = (ROOT / "deployment" / "staging" / "docker-compose.yml").read_text()
    deploy = (ROOT / "deployment" / "scripts" / "deploy.sh").read_text()

    assert "SENTINEL_DNA_ENV: staging" in compose
    assert 'SENTINEL_DNA_PILOT_ACCESS_REQUIRED: "1"' in compose
    assert 'SENTINEL_DNA_SECURE_COOKIES: "1"' in compose
    assert "FLASK_DEBUG: \"0\"" in compose
    assert "DATABASE_URL: postgresql://" in compose
    assert "staging_internal:" in compose
    assert "internal: true" in compose
    assert 'ports:\n      - "${SENTINEL_DNA_STAGING_EDGE_BIND' in compose
    assert "--file \"$STAGING_COMPOSE\"" in deploy
    assert "--env-file \"$STAGING_ENV_FILE\"" in deploy
    assert "docker compose up -d --build" not in deploy
    assert "Missing .env" not in deploy
