"""Canonical registry for the authoritative Sentinel DNA schema migrations."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, Callable


Upgrade = Callable[[Any], None]
StatementFactory = Callable[[str], tuple[str, ...]]


@dataclass(frozen=True)
class Migration:
    """One ordered migration, with compatibility for legacy statement factories."""

    version: int
    name: str
    statements: StatementFactory | None = None
    upgrade: Upgrade | None = None

    def apply(self, connection: Any, backend_name: str) -> None:
        if self.upgrade is not None:
            self.upgrade(connection)
            return
        if self.statements is not None:
            for statement in self.statements(backend_name):
                connection.execute(statement)
            return
        raise ValueError(f"migration_{self.version}_has_no_execution_handler")


MIGRATION_MODULES = (
    "database.migrations.001_baseline",
    "database.migrations.002_canonical_authority",
    "database.migrations.003_identity_bindings",
    "database.migrations.004_provider_tenant_trust",
    "database.migrations.005_billing",
    "database.migrations.006_crypto_intents",
    "database.migrations.007_investigation_memory",
    "database.migrations.008_organizational_cyber_memory",
)

STAGING_FIRST_PRIVILEGED_IDENTITY_NAMESPACE = "staging-first-privileged-identity"
STAGING_FIRST_PRIVILEGED_IDENTITY_MIGRATION_MODULE = (
    "database.migrations.011_staging_first_privileged_identity"
)


def _load_migrations(module_names: tuple[str, ...]) -> tuple[Migration, ...]:
    migrations: list[Migration] = []
    for module_name in module_names:
        module = import_module(module_name)
        version = getattr(module, "VERSION", None)
        upgrade = getattr(module, "upgrade", None)
        if not isinstance(version, int) or not callable(upgrade):
            raise ValueError(f"invalid_migration_module:{module_name}")
        name = str(getattr(module, "DESCRIPTION", module_name.rsplit(".", 1)[-1]))
        migrations.append(Migration(version=version, name=name, upgrade=upgrade))
    return tuple(migrations)


def _validate_contiguous(migrations: tuple[Migration, ...]) -> tuple[Migration, ...]:
    ordered = tuple(sorted(migrations, key=lambda item: item.version))
    versions = [migration.version for migration in ordered]
    if len(set(versions)) != len(versions) or versions != list(range(1, len(versions) + 1)):
        raise ValueError("migration_versions_must_be_contiguous")
    return ordered


def migration_registry() -> tuple[Migration, ...]:
    """Load and validate only the authoritative default migration chain."""

    return _validate_contiguous(_load_migrations(MIGRATION_MODULES))


def staging_first_privileged_identity_namespace_registry(
    environment: str,
    *,
    enabled: bool,
) -> tuple[Migration, ...]:
    """Load migration 011 only for an explicitly selected staging overlay."""

    if str(environment).strip().lower() != "staging":
        raise RuntimeError("staging_first_privileged_identity_namespace_requires_staging")
    if not enabled:
        raise RuntimeError("staging_first_privileged_identity_namespace_requires_explicit_opt_in")
    migrations = _load_migrations((STAGING_FIRST_PRIVILEGED_IDENTITY_MIGRATION_MODULE,))
    if len(migrations) != 1 or migrations[0].version != 11:
        raise ValueError("invalid_staging_first_privileged_identity_migration")
    return migrations


def apply_staging_first_privileged_identity_namespace(
    backend: Any,
    *,
    environment: str,
    enabled: bool,
) -> tuple[int, ...]:
    """Apply the selected staging overlay without changing default history."""

    migrations = staging_first_privileged_identity_namespace_registry(
        environment,
        enabled=enabled,
    )
    applied_now: list[int] = []
    with backend.session() as connection:
        if getattr(backend, "backend_name", "sqlite") == "sqlite":
            connection.execute("BEGIN")
        connection.execute(
            """CREATE TABLE IF NOT EXISTS namespace_migrations (
                namespace TEXT NOT NULL,
                version INTEGER NOT NULL,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL,
                PRIMARY KEY(namespace, version)
            )"""
        )
        applied = {
            int(row["version"])
            for row in connection.execute(
                "SELECT version FROM namespace_migrations WHERE namespace=?",
                (STAGING_FIRST_PRIVILEGED_IDENTITY_NAMESPACE,),
            ).fetchall()
        }
        for migration in migrations:
            if migration.version in applied:
                continue
            migration.apply(connection, backend.backend_name)
            connection.execute(
                """INSERT INTO namespace_migrations(namespace, version, name, applied_at)
                   VALUES(?,?,?,CURRENT_TIMESTAMP)
                   ON CONFLICT(namespace, version) DO NOTHING""",
                (
                    STAGING_FIRST_PRIVILEGED_IDENTITY_NAMESPACE,
                    migration.version,
                    migration.name,
                ),
            )
            applied_now.append(migration.version)
    return tuple(applied_now)


MIGRATIONS = migration_registry()

__all__ = [
    "MIGRATIONS",
    "MIGRATION_MODULES",
    "Migration",
    "STAGING_FIRST_PRIVILEGED_IDENTITY_MIGRATION_MODULE",
    "STAGING_FIRST_PRIVILEGED_IDENTITY_NAMESPACE",
    "migration_registry",
    "apply_staging_first_privileged_identity_namespace",
    "staging_first_privileged_identity_namespace_registry",
]
