"""Canonical registry for the authoritative Sentinel DNA schema migrations."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from importlib import import_module
import json
from pathlib import Path
import re
from typing import Any, Callable


Upgrade = Callable[[Any], None]
StatementFactory = Callable[[str], tuple[str, ...]]

_IDENTITY_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_ALLOWED_MODULE_PREFIX = "database.migrations."
_REGISTRY_TOKEN = object()


@dataclass(frozen=True, order=True)
class MigrationRef:
    """Fully qualified reference to a namespace migration."""

    namespace: str
    migration_key: str

    def __post_init__(self) -> None:
        _validate_identity_part("namespace", self.namespace)
        _validate_identity_part("migration_key", self.migration_key)

    def as_key(self) -> tuple[str, str]:
        return self.namespace, self.migration_key

    def serialized(self) -> dict[str, str]:
        return {"namespace": self.namespace, "migration_key": self.migration_key}


@dataclass(frozen=True)
class NamespaceMigration:
    """Immutable descriptor for a future namespace migration.

    Namespace migrations are intentionally separate from the legacy numeric
    ``Migration`` descriptor.  ``source_bytes`` is retained by trusted
    registry construction so the runner can verify the expected digest at
    execution time without importing arbitrary runtime paths.
    """

    namespace: str
    migration_key: str
    name: str
    upgrade: Upgrade
    prerequisites: tuple[MigrationRef, ...] = ()
    source_digest: str = ""
    display_version: int | None = None
    module_path: str | None = None
    source_bytes: bytes | None = None
    _registry_token: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        _validate_identity_part("namespace", self.namespace)
        _validate_identity_part("migration_key", self.migration_key)
        if not self.name.strip():
            raise ValueError("migration_name_required")
        if not callable(self.upgrade):
            raise ValueError("migration_handler_required")
        if self.display_version is not None and (
            not isinstance(self.display_version, int) or self.display_version < 1
        ):
            raise ValueError("invalid_display_version")
        if not re.fullmatch(r"[0-9a-f]{64}", self.source_digest):
            raise ValueError("invalid_source_digest")
        if self.module_path is not None:
            _validate_module_path(self.module_path)
        if self.source_bytes is not None and hashlib.sha256(self.source_bytes).hexdigest() != self.source_digest:
            raise ValueError("source_digest_mismatch")
        prerequisites = tuple(self.prerequisites)
        if len(set(prerequisites)) != len(prerequisites):
            raise ValueError("duplicate_prerequisite")
        if any(not isinstance(item, MigrationRef) for item in prerequisites):
            raise ValueError("invalid_prerequisite")

    @property
    def ref(self) -> MigrationRef:
        return MigrationRef(self.namespace, self.migration_key)

    def prerequisites_json(self) -> str:
        return json.dumps(
            [item.serialized() for item in self.prerequisites],
            sort_keys=True,
            separators=(",", ":"),
        )


def _validate_identity_part(label: str, value: str) -> None:
    if not isinstance(value, str) or not _IDENTITY_PATTERN.fullmatch(value):
        raise ValueError(f"invalid_{label}")


def _validate_module_path(module_path: str) -> None:
    if (
        not isinstance(module_path, str)
        or not module_path.startswith(_ALLOWED_MODULE_PREFIX)
        or ".." in module_path
        or "/" in module_path
        or "\\" in module_path
    ):
        raise ValueError("migration_module_path_not_allowlisted")


def source_digest_for_module(module: Any) -> tuple[str, bytes]:
    """Return the SHA-256 digest and canonical source bytes for a module."""

    module_path = getattr(module, "__name__", "")
    _validate_module_path(module_path)
    filename = getattr(module, "__file__", None)
    if not filename:
        raise ValueError("migration_module_source_unavailable")
    source_bytes = Path(filename).read_bytes()
    return hashlib.sha256(source_bytes).hexdigest(), source_bytes


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

# The controlled analyst pilot is a separately selected overlay.  Keeping it
# out of both default chains preserves the existing Gate 4/FAVP migration
# contract and prevents a production process from silently enabling pilot
# state.  Deployment tooling may compose this tuple explicitly.
CONTROLLED_ANALYST_PILOT_MIGRATION_MODULES = STAGING_MIGRATION_MODULES + (
    "database.migrations.010_controlled_analyst_pilot",
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


# Namespace migration specifications are intentionally explicit and digest
# pinned.  Entra and later migrations remain unregistered until separately
# approved.
NAMESPACE_MIGRATION_SPECS: tuple[tuple[str, str], ...] = (
    (
        "database.migrations.foundation.users_authority",
        "69da1a2addb2c3bad15b66532a1334a228741a57961c0c7d14a630c37563cf3f",
    ),
    (
        "database.migrations.future.entra_identity_bindings",
        "b8c132f4125290e39bef65259fa42040b3272571f24a4dc3d6363663b92e86c1",
    ),
    (
        "database.migrations.future.approval_workflow",
        "c89be40354d3df0f928153daf2ac59bd87b0c6931a8a891e17e153ebeb37d8da",
    ),
)


def namespace_migration_registry() -> tuple[NamespaceMigration, ...]:
    """Load only statically allowlisted namespace migration modules."""

    migrations: list[NamespaceMigration] = []
    module_paths: set[str] = set()
    for module_path, expected_digest in NAMESPACE_MIGRATION_SPECS:
        _validate_module_path(module_path)
        if module_path in module_paths:
            raise ValueError("duplicate_migration_module_path")
        module_paths.add(module_path)
        module = import_module(module_path)
        actual_digest, source_bytes = source_digest_for_module(module)
        if actual_digest != expected_digest:
            raise ValueError(f"migration_source_digest_mismatch:{module_path}")
        namespace = getattr(module, "NAMESPACE", None)
        migration_key = getattr(module, "MIGRATION_KEY", None)
        name = str(getattr(module, "DESCRIPTION", module_path.rsplit(".", 1)[-1]))
        upgrade = getattr(module, "upgrade", None)
        prerequisites = tuple(getattr(module, "PREREQUISITES", ()))
        display_version = getattr(module, "DISPLAY_VERSION", None)
        migrations.append(
            NamespaceMigration(
                namespace=namespace,
                migration_key=migration_key,
                name=name,
                upgrade=upgrade,
                prerequisites=prerequisites,
                source_digest=expected_digest,
                display_version=display_version,
                module_path=module_path,
                source_bytes=source_bytes,
                _registry_token=_REGISTRY_TOKEN,
            )
        )
    validate_namespace_registry(tuple(migrations))
    return tuple(migrations)


def validate_namespace_registry(
    migrations: tuple[NamespaceMigration, ...],
) -> tuple[NamespaceMigration, ...]:
    """Validate identities and dependencies before any database work."""

    by_ref: dict[MigrationRef, NamespaceMigration] = {}
    module_paths: set[str] = set()
    display_versions: set[tuple[str, int]] = set()
    for migration in migrations:
        if migration.ref in by_ref:
            raise ValueError("duplicate_migration_identity")
        if migration.module_path is not None:
            _validate_module_path(migration.module_path)
            if migration.module_path in module_paths:
                raise ValueError("duplicate_migration_module_path")
            module_paths.add(migration.module_path)
        if migration.display_version is not None:
            display_key = (migration.namespace, migration.display_version)
            if display_key in display_versions:
                raise ValueError("ambiguous_display_version")
            display_versions.add(display_key)
        by_ref[migration.ref] = migration

    for migration in migrations:
        for prerequisite in migration.prerequisites:
            if prerequisite not in by_ref:
                raise ValueError(
                    f"unknown_migration_prerequisite:{prerequisite.namespace}.{prerequisite.migration_key}"
                )

    ordered: list[NamespaceMigration] = []
    visiting: set[MigrationRef] = set()
    visited: set[MigrationRef] = set()

    def visit(ref: MigrationRef) -> None:
        if ref in visiting:
            raise ValueError("migration_dependency_cycle")
        if ref in visited:
            return
        visiting.add(ref)
        migration = by_ref[ref]
        for prerequisite in sorted(migration.prerequisites):
            visit(prerequisite)
        visiting.remove(ref)
        visited.add(ref)
        ordered.append(migration)

    for ref in sorted(by_ref):
        visit(ref)
    return tuple(ordered)


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


def controlled_analyst_pilot_migration_registry() -> tuple[Migration, ...]:
    """Load the optional staging/FAVP chain plus the pilot overlay."""
    migrations: list[Migration] = []
    for module_name in CONTROLLED_ANALYST_PILOT_MIGRATION_MODULES:
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
CONTROLLED_ANALYST_PILOT_MIGRATIONS = controlled_analyst_pilot_migration_registry()
NAMESPACE_MIGRATIONS = namespace_migration_registry()

__all__ = [
    "MIGRATIONS",
    "MIGRATION_MODULES",
    "STAGING_MIGRATIONS",
    "CONTROLLED_ANALYST_PILOT_MIGRATIONS",
    "STAGING_MIGRATION_MODULES",
    "CONTROLLED_ANALYST_PILOT_MIGRATION_MODULES",
    "Migration",
    "MigrationRef",
    "NamespaceMigration",
    "NAMESPACE_MIGRATIONS",
    "NAMESPACE_MIGRATION_SPECS",
    "migration_registry",
    "namespace_migration_registry",
    "source_digest_for_module",
    "validate_namespace_registry",
    "staging_migration_registry",
    "controlled_analyst_pilot_migration_registry",
]
