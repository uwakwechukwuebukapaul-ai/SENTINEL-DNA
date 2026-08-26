"""Opt-in PostgreSQL integration coverage for the Phase 2 boundary.

The test suite never infers credentials from production configuration. Set
SENTINEL_DNA_TEST_POSTGRES_URL explicitly to run these tests against a
disposable PostgreSQL database.
"""

import os

import pytest

from database.backend import PostgreSQLBackend


@pytest.fixture
def postgres_backend():
    url = os.getenv("SENTINEL_DNA_TEST_POSTGRES_URL", "").strip()
    if not url:
        pytest.skip("SENTINEL_DNA_TEST_POSTGRES_URL is not configured")
    backend = PostgreSQLBackend(url, connect_timeout=5)
    if not backend.health_check():
        pytest.fail("configured disposable PostgreSQL test database is unavailable")
    return backend


@pytest.mark.postgresql
def test_postgresql_health_and_transaction_lifecycle_are_isolated(postgres_backend):
    with postgres_backend.session() as connection:
        connection.execute(
            "CREATE TEMP TABLE phase2_probe (value TEXT NOT NULL) ON COMMIT DROP"
        )
        connection.execute("INSERT INTO phase2_probe VALUES (%s)", ("phase2",))
        row = connection.execute("SELECT value FROM phase2_probe").fetchone()
        assert row["value"] == "phase2"

    assert postgres_backend.health_check() is True

