"""Exercise the explicit staging-only PostgreSQL migration overlays."""

from __future__ import annotations

from contextlib import contextmanager
import os
from typing import Any, Iterator

from database.migrations.registry import (
    STAGING_AUTHORITY_ENROLLMENT_NAMESPACE,
    STAGING_FIRST_PRIVILEGED_IDENTITY_NAMESPACE,
    apply_staging_authority_enrollment_namespace,
    apply_staging_first_privileged_identity_namespace,
)


@contextmanager
def _disposable_staging_environment() -> Iterator[None]:
    names = (
        "SENTINEL_DNA_ENV",
        "SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION",
    )
    previous = {name: os.environ.get(name) for name in names}
    os.environ["SENTINEL_DNA_ENV"] = "staging"
    os.environ["SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION"] = "disposable_rehearsal"
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _table_columns(backend: Any, table_name: str) -> tuple[str, ...]:
    with backend.session() as connection:
        rows = connection.execute(
            """SELECT column_name FROM information_schema.columns
               WHERE table_schema = current_schema() AND table_name = ?
               ORDER BY ordinal_position""",
            (table_name,),
        ).fetchall()
    return tuple(str(row["column_name"]) for row in rows)


def run_staging_overlays(backend: Any) -> dict[str, Any]:
    """Apply 011 and 012 only to the authorized disposable rehearsal target."""

    with _disposable_staging_environment():
        first_011 = apply_staging_first_privileged_identity_namespace(
            backend, environment="staging", enabled=True
        )
        second_011 = apply_staging_first_privileged_identity_namespace(
            backend, environment="staging", enabled=True
        )
        first_012 = apply_staging_authority_enrollment_namespace(
            backend, environment="staging", enabled=True
        )
        second_012 = apply_staging_authority_enrollment_namespace(
            backend, environment="staging", enabled=True
        )

    with backend.session() as connection:
        authoritative = [
            int(row["version"])
            for row in connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
        ]
        namespace_rows = [
            (str(row["namespace"]), int(row["version"]))
            for row in connection.execute(
                "SELECT namespace, version FROM namespace_migrations "
                "WHERE namespace IN (?, ?) ORDER BY namespace, version",
                (
                    STAGING_FIRST_PRIVILEGED_IDENTITY_NAMESPACE,
                    STAGING_AUTHORITY_ENROLLMENT_NAMESPACE,
                ),
            ).fetchall()
        ]

    expected_authoritative = list(range(1, 10))
    expected_namespace_rows = [
        (STAGING_AUTHORITY_ENROLLMENT_NAMESPACE, 12),
        (STAGING_FIRST_PRIVILEGED_IDENTITY_NAMESPACE, 11),
    ]
    table_columns = {
        table: _table_columns(backend, table)
        for table in (
            "staging_bootstrap_authorizations",
            "staging_bootstrap_consumptions",
            "staging_authority_enrollments",
            "users",
        )
    }
    expected_columns = {
        "staging_bootstrap_authorizations": {
            "authorization_id", "control_tenant_id", "requester_actor_id",
            "reviewer_actor_id", "status", "created_at",
        },
        "staging_bootstrap_consumptions": {
            "bootstrap_key", "authorization_id", "reviewer_actor_id",
            "created_user_id", "outcome", "consumed_at",
        },
        "staging_authority_enrollments": {
            "enrollment_id", "authority_id", "nonce", "reviewer_fingerprint",
            "environment", "status", "created_at",
        },
        "users": {"password_hash", "password_authentication_enabled"},
    }
    tables_queryable = all(
        expected_columns[table] <= set(columns)
        for table, columns in table_columns.items()
    )
    return {
        "migration_011_first_run": list(first_011),
        "migration_011_second_run": list(second_011),
        "migration_012_first_run": list(first_012),
        "migration_012_second_run": list(second_012),
        "namespace_bookkeeping_isolated": namespace_rows == expected_namespace_rows,
        "authoritative_history_intact": authoritative == expected_authoritative,
        "tables_queryable": tables_queryable,
        "table_columns": {table: list(columns) for table, columns in table_columns.items()},
    }
