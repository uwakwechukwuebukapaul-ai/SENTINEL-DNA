"""Regression coverage for host/container database test topology."""

import os
from pathlib import Path

import pytest

from tests.database_test_topology import (
    TEST_POSTGRES_PASSWORD_FILE_ENV,
    TEST_POSTGRES_URL_ENV,
    TEST_TOPOLOGY_ENV,
    configured_test_postgres,
    isolate_host_database_environment,
    resolve_test_topology,
)


def test_host_topology_does_not_assume_docker_internal_postgres(monkeypatch):
    monkeypatch.delenv(TEST_TOPOLOGY_ENV, raising=False)
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://sentinel@postgres:5432/sentinel_dna"
    )
    monkeypatch.setenv(
        "SENTINEL_DNA_POSTGRES_PASSWORD_FILE",
        "/run/secrets/sentinel_dna_postgres_password",
    )

    assert resolve_test_topology() == "host"
    isolate_host_database_environment(monkeypatch)

    assert "DATABASE_URL" not in os.environ
    assert "SENTINEL_DNA_POSTGRES_PASSWORD_FILE" not in os.environ
    assert "SENTINEL_DNA_PILOT_ACCESS_REQUIRED" not in os.environ


def test_container_topology_is_explicit_and_preserves_internal_endpoint(monkeypatch):
    monkeypatch.setenv(TEST_TOPOLOGY_ENV, "container")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://sentinel@postgres:5432/sentinel_dna"
    )

    assert resolve_test_topology() == "container"
    isolate_host_database_environment(monkeypatch)
    assert os.environ["DATABASE_URL"].endswith("@postgres:5432/sentinel_dna")


def test_postgres_integration_requires_password_free_url_and_secret_file(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setenv(
        TEST_POSTGRES_URL_ENV, "postgresql://sentinel@127.0.0.1:5432/test_db"
    )
    monkeypatch.delenv(TEST_POSTGRES_PASSWORD_FILE_ENV, raising=False)
    with pytest.raises(ValueError, match=TEST_POSTGRES_PASSWORD_FILE_ENV):
        configured_test_postgres()

    password_file = tmp_path / "test-postgres-password"
    password_file.write_text("disposable-test-secret\n", encoding="utf-8")
    monkeypatch.setenv(TEST_POSTGRES_PASSWORD_FILE_ENV, str(password_file))
    assert configured_test_postgres() == (
        "postgresql://sentinel@127.0.0.1:5432/test_db",
        password_file,
    )


def test_staging_postgres_remains_private_and_uses_secret_file():
    compose = (
        Path(__file__).resolve().parents[2]
        / "deployment"
        / "staging"
        / "docker-compose.yml"
    ).read_text(encoding="utf-8")
    postgres_block = compose.split("  postgres:", 1)[1].split("  redis:", 1)[0]

    assert "ports:" not in postgres_block
    assert "internal: true" in compose
    assert (
        "SENTINEL_DNA_POSTGRES_PASSWORD_FILE: "
        "/run/secrets/sentinel_dna_postgres_password"
    ) in compose
    assert "POSTGRES_PASSWORD_FILE: /run/secrets/sentinel_dna_postgres_password" in compose
