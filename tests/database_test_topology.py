"""Reusable test-only database topology helpers.

This module is intentionally outside the application package. It prevents
host pytest from consuming deployment configuration while keeping PostgreSQL
integration explicit and compatible with Docker secret mounts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping, MutableMapping
from urllib.parse import urlparse


TEST_TOPOLOGY_ENV = "SENTINEL_DNA_TEST_TOPOLOGY"
TEST_POSTGRES_URL_ENV = "SENTINEL_DNA_TEST_POSTGRES_URL"
TEST_POSTGRES_PASSWORD_FILE_ENV = "SENTINEL_DNA_TEST_POSTGRES_PASSWORD_FILE"

HOST_DEPLOYMENT_ENVIRONMENT_NAMES = (
    "DATABASE_URL",
    "SENTINEL_DNA_POSTGRES_PASSWORD_FILE",
    "SENTINEL_DNA_DB_PATH",
    "SENTINEL_DNA_ENV",
    "FLASK_ENV",
    "FLASK_DEBUG",
    "SENTINEL_DNA_SECRET_KEY",
    "SENTINEL_DNA_SECRET_KEY_FILE",
    "SENTINEL_DNA_SECURE_COOKIES",
    "SENTINEL_DNA_PILOT_ACCESS_REQUIRED",
    "SENTINEL_DNA_CONFIG_SOURCE_CLASSIFICATION",
    "SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION",
    "SENTINEL_DNA_TENANT_ISOLATION_ENABLED",
    "SENTINEL_DNA_AUDIT_LOGGING_ENABLED",
    "SENTINEL_DNA_FAVP_OPERATIONS_ENABLED",
    "SENTINEL_DNA_FAVP_SYNTHETIC_ONLY",
    "SENTINEL_DNA_FAVP_PRODUCTION_ACCESS",
)


def resolve_test_topology(environ: Mapping[str, str] | None = None) -> str:
    """Return the explicitly selected test topology.

    Host execution is the safe default. Container execution must be selected
    explicitly so Docker-internal names are never assumed to work on a host.
    """
    values = os.environ if environ is None else environ
    topology = values.get(TEST_TOPOLOGY_ENV, "host").strip().lower()
    if topology not in {"host", "container"}:
        raise ValueError(
            f"{TEST_TOPOLOGY_ENV} must be either 'host' or 'container'"
        )
    return topology


def sanitize_host_database_environment(environ: MutableMapping[str, str]) -> None:
    """Remove application deployment settings before host test collection."""
    for name in HOST_DEPLOYMENT_ENVIRONMENT_NAMES:
        environ.pop(name, None)


def isolate_host_database_environment(monkeypatch) -> None:
    """Remove application deployment settings from an individual host test."""
    if resolve_test_topology() != "host":
        return
    for name in HOST_DEPLOYMENT_ENVIRONMENT_NAMES:
        monkeypatch.delenv(name, raising=False)


def configured_test_postgres() -> tuple[str, Path] | None:
    """Resolve an opt-in disposable PostgreSQL endpoint without exposing it."""
    url = os.getenv(TEST_POSTGRES_URL_ENV, "").strip()
    if not url:
        return None
    try:
        parsed = urlparse(url)
        has_password = parsed.password is not None
    except ValueError as exc:
        raise ValueError(
            f"{TEST_POSTGRES_URL_ENV} must be a valid password-free PostgreSQL URL"
        ) from exc
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.netloc:
        raise ValueError(f"{TEST_POSTGRES_URL_ENV} must be a valid PostgreSQL URL")
    if has_password:
        raise ValueError(
            f"{TEST_POSTGRES_URL_ENV} must omit the password; configure "
            f"{TEST_POSTGRES_PASSWORD_FILE_ENV} instead"
        )

    password_file = os.getenv(TEST_POSTGRES_PASSWORD_FILE_ENV, "").strip()
    if not password_file:
        raise ValueError(
            f"{TEST_POSTGRES_PASSWORD_FILE_ENV} is required when "
            f"{TEST_POSTGRES_URL_ENV} is configured"
        )
    password_path = Path(password_file)
    if not password_path.is_file():
        raise ValueError(
            f"{TEST_POSTGRES_PASSWORD_FILE_ENV} must point to a readable test secret file"
        )
    return url, password_path
