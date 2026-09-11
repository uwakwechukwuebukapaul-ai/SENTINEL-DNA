import hashlib

import pytest

from database.migrations.registry import (
    CONTROLLED_ANALYST_PILOT_MIGRATIONS,
    MIGRATIONS,
    NAMESPACE_MIGRATIONS,
    STAGING_MIGRATIONS,
    MigrationRef,
    NamespaceMigration,
    validate_namespace_registry,
)
from database.migration_runner import MigrationRunner


def _migration(namespace, key, prerequisites=(), body=None, *, display_version=None):
    source = f"{namespace}:{key}".encode()
    return NamespaceMigration(
        namespace=namespace,
        migration_key=key,
        name=key,
        upgrade=body or (lambda _connection: None),
        prerequisites=tuple(prerequisites),
        source_digest=hashlib.sha256(source).hexdigest(),
        display_version=display_version,
        source_bytes=source,
    )


def test_namespace_registry_contains_only_approved_users_authority():
    assert [(migration.namespace, migration.migration_key) for migration in NAMESPACE_MIGRATIONS] == [
        ("foundation", "users_authority"),
        ("future", "entra_identity_bindings"),
        ("future", "approval_workflow"),
    ]


def test_legacy_registry_remains_exactly_numeric_and_contiguous():
    assert [migration.version for migration in MIGRATIONS] == list(range(1, 9))


def test_existing_selected_chains_remain_unchanged():
    assert [migration.version for migration in MIGRATIONS] == list(range(1, 9))
    assert [migration.version for migration in STAGING_MIGRATIONS] == list(range(1, 10))
    assert [migration.version for migration in CONTROLLED_ANALYST_PILOT_MIGRATIONS] == list(range(1, 11))
    assert [(migration.namespace, migration.migration_key) for migration in NAMESPACE_MIGRATIONS] == [
        ("foundation", "users_authority"),
        ("future", "entra_identity_bindings"),
        ("future", "approval_workflow"),
    ]


def test_namespace_dependencies_are_topologically_sorted_deterministically():
    a = _migration("foundation", "a")
    b = _migration("foundation", "b", (a.ref,))
    c = _migration("foundation", "c", (b.ref,))

    assert [migration.migration_key for migration in validate_namespace_registry((c, b, a))] == [
        "a",
        "b",
        "c",
    ]


def test_duplicate_identity_is_rejected():
    migration = _migration("foundation", "users")
    with pytest.raises(ValueError, match="duplicate_migration_identity"):
        validate_namespace_registry((migration, migration))


@pytest.mark.parametrize("namespace", ["", "Foundation", "../foundation", "foundation/users"])
def test_invalid_namespace_is_rejected(namespace):
    with pytest.raises(ValueError, match="invalid_namespace"):
        _migration(namespace, "users")


@pytest.mark.parametrize("key", ["", "Users", "../users", "foundation/users"])
def test_invalid_migration_key_is_rejected(key):
    with pytest.raises(ValueError, match="invalid_migration_key"):
        _migration("foundation", key)


def test_unknown_dependency_is_rejected():
    missing = MigrationRef("foundation", "missing")
    with pytest.raises(ValueError, match="unknown_migration_prerequisite"):
        validate_namespace_registry((_migration("foundation", "users", (missing,)),))


def test_dependency_cycle_is_rejected():
    a_ref = MigrationRef("foundation", "a")
    b_ref = MigrationRef("foundation", "b")
    a = _migration("foundation", "a", (b_ref,))
    b = _migration("foundation", "b", (a_ref,))
    with pytest.raises(ValueError, match="migration_dependency_cycle"):
        validate_namespace_registry((a, b))


def test_duplicate_dependency_is_rejected():
    a = _migration("foundation", "a")
    with pytest.raises(ValueError, match="duplicate_prerequisite"):
        _migration("foundation", "b", (a.ref, a.ref))


def test_ambiguous_display_version_is_rejected():
    a = _migration("foundation", "a", display_version=1)
    b = _migration("foundation", "b", display_version=1)
    with pytest.raises(ValueError, match="ambiguous_display_version"):
        validate_namespace_registry((a, b))


def test_digest_drift_is_rejected_at_descriptor_construction():
    with pytest.raises(ValueError, match="source_digest_mismatch"):
        NamespaceMigration(
            namespace="foundation",
            migration_key="users",
            name="users",
            upgrade=lambda _connection: None,
            source_digest="0" * 64,
            source_bytes=b"trusted source",
        )


def test_unallowlisted_module_path_is_rejected():
    source = b"source"
    with pytest.raises(ValueError, match="migration_module_path_not_allowlisted"):
        NamespaceMigration(
            namespace="foundation",
            migration_key="users",
            name="users",
            upgrade=lambda _connection: None,
            source_digest=hashlib.sha256(source).hexdigest(),
            source_bytes=source,
            module_path="evil.module",
        )


def test_runner_rejects_runtime_constructed_namespace_descriptor():
    with pytest.raises(ValueError, match="namespace_registry_not_trusted"):
        MigrationRunner(
            object(),
            migrations=(),
            namespace_migrations=(_migration("foundation", "runtime"),),
        )
