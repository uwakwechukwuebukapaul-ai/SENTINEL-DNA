"""Shared pytest topology and test-only fixtures."""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest

from database.backend import PostgreSQLBackend
from database.connection import database
from tests.database_test_topology import (
    configured_test_postgres,
    isolate_host_database_environment,
    resolve_test_topology,
    sanitize_host_database_environment,
)


def pytest_configure(config):
    """Sanitize host deployment variables before import-time test setup."""
    try:
        if resolve_test_topology() == "host":
            sanitize_host_database_environment(os.environ)
    except ValueError as exc:
        raise pytest.UsageError(str(exc)) from exc


@pytest.fixture(autouse=True)
def test_database_topology(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[str, None, None]:
    """Keep host tests isolated while allowing explicit container tests."""
    try:
        topology = resolve_test_topology()
        isolate_host_database_environment(monkeypatch)
        # The application backend is deliberately lazy and process-scoped.
        # Reset it between tests so one test's explicit environment cannot
        # leak into the next test's topology.
        database._backend = None
    except ValueError as exc:
        pytest.fail(str(exc), pytrace=False)
    try:
        yield topology
    finally:
        database._backend = None


@pytest.fixture
def postgres_backend() -> PostgreSQLBackend:
    """Provide an explicitly configured disposable PostgreSQL test backend."""
    try:
        configuration = configured_test_postgres()
    except ValueError as exc:
        pytest.fail(str(exc), pytrace=False)
    if configuration is None:
        pytest.skip(
            "SENTINEL_DNA_TEST_POSTGRES_URL is not configured; PostgreSQL "
            "integration requires an explicit disposable test endpoint"
        )

    url, password_file = configuration
    backend = PostgreSQLBackend(url, connect_timeout=5, password_file=password_file)
    if not backend.health_check():
        pytest.fail(
            "configured disposable PostgreSQL test endpoint is unavailable; "
            "run this test in the Docker network or configure a reachable endpoint",
            pytrace=False,
        )
    return backend


@pytest.fixture
def authenticated_session():
    return {"user_id": 1, "role": "analyst"}
