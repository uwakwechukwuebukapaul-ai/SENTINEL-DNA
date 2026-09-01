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

# FAVP is a staging-only surface. Keep its migration out of the authoritative
# production chain; the staging migration runner composes this tuple with the
# disposable FAVP migration explicitly.
STAGING_MIGRATION_MODULES = MIGRATION_MODULES + (
    "database.migrations.009_favp_staging",
)


def migration_registry() -> tuple[Migration, ...]:
    """Load and validate the checked-in migration chain deterministically."""

    migrations: list[Migration] = []
    for module_name in MIGRATION_MODULES:
        module = import_module(module_name)
        version = getattr(module, "VERSION", None)
        upgrade = getattr(module, "upgrade", None)
        if not isinstance(version, int) or not callable(upgrade):
            raise ValueError(f"invalid_migration_module:{module_name}")
        name = str(getattr(module, "DESCRIPTION", module_name.rsplit(".", 1)[-1]))
        migrations.append(Migration(version=version, name=name, upgrade=upgrade))

    ordered = tuple(sorted(migrations, key=lambda item: item.version))
    versions = [migration.version for migration in ordered]
    if len(set(versions)) != len(versions) or versions != list(range(1, len(versions) + 1)):
        raise ValueError("migration_versions_must_be_contiguous")
    return ordered


def staging_migration_registry() -> tuple[Migration, ...]:
    """Load the core chain plus staging-only FAVP schema migrations."""

    migrations: list[Migration] = []
    for module_name in STAGING_MIGRATION_MODULES:
        module = import_module(module_name)
        version = getattr(module, "VERSION", None)
        upgrade = getattr(module, "upgrade", None)
        if not isinstance(version, int) or not callable(upgrade):
            raise ValueError(f"invalid_migration_module:{module_name}")
        name = str(getattr(module, "DESCRIPTION", module_name.rsplit(".", 1)[-1]))
        migrations.append(Migration(version=version, name=name, upgrade=upgrade))

    ordered = tuple(sorted(migrations, key=lambda item: item.version))
    versions = [migration.version for migration in ordered]
    if len(set(versions)) != len(versions) or versions != list(range(1, len(versions) + 1)):
        raise ValueError("migration_versions_must_be_contiguous")
    return ordered


MIGRATIONS = migration_registry()
STAGING_MIGRATIONS = staging_migration_registry()

__all__ = [
    "MIGRATIONS",
    "MIGRATION_MODULES",
    "STAGING_MIGRATIONS",
    "STAGING_MIGRATION_MODULES",
    "Migration",
    "migration_registry",
    "staging_migration_registry",
]
