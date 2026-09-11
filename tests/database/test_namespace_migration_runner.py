import hashlib
import threading
import time

import pytest

from database.backend import SQLiteBackend
from database.migration_runner import MigrationRunner
from database.migrations.registry import NamespaceMigration, _REGISTRY_TOKEN


def _namespace_migration(key="users", body=None):
    source = f"foundation:{key}".encode()
    return NamespaceMigration(
        namespace="foundation",
        migration_key=key,
        name=key,
        upgrade=body or (lambda connection: connection.execute("CREATE TABLE namespace_probe (value TEXT)")),
        source_digest=hashlib.sha256(source).hexdigest(),
        source_bytes=source,
        _registry_token=_REGISTRY_TOKEN,
    )


def test_namespace_metadata_is_created_and_execution_is_idempotent(tmp_path):
    backend = SQLiteBackend(tmp_path / "namespace.sqlite")
    migration = _namespace_migration()
    runner = MigrationRunner(backend, migrations=(), namespace_migrations=(migration,))

    assert runner.run() == ()
    assert runner.run() == ()

    with backend.session() as connection:
        record = connection.execute(
            "SELECT namespace, migration_key, status, applied_at FROM migration_records"
        ).fetchone()
        assert tuple(record)[:3] == ("foundation", "users", "applied")
        assert record[3]
        assert connection.execute("SELECT COUNT(*) FROM namespace_probe").fetchone()[0] == 0


def test_legacy_and_namespace_metadata_are_independent(tmp_path):
    backend = SQLiteBackend(tmp_path / "separate.sqlite")
    with backend.session() as connection:
        connection.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
        connection.execute("INSERT INTO schema_migrations VALUES (9, 'historic')")

    MigrationRunner(
        backend,
        migrations=(),
        namespace_migrations=(_namespace_migration(),),
    ).run()

    with backend.session() as connection:
        assert tuple(connection.execute("SELECT version, applied_at FROM schema_migrations").fetchone()) == (9, "historic")
        assert tuple(connection.execute("SELECT namespace, migration_key FROM migration_records").fetchone()) == ("foundation", "users")


def test_namespace_failure_rolls_back_schema_and_applying_record(tmp_path):
    backend = SQLiteBackend(tmp_path / "failure.sqlite")

    def fail(connection):
        connection.execute("CREATE TABLE namespace_probe (value TEXT)")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        MigrationRunner(
            backend,
            migrations=(),
            namespace_migrations=(_namespace_migration(body=fail),),
        ).run()

    with backend.session() as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='migration_records'").fetchone() is None
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='namespace_probe'").fetchone() is None


def test_applied_metadata_digest_drift_fails_closed(tmp_path):
    backend = SQLiteBackend(tmp_path / "drift.sqlite")
    migration = _namespace_migration()
    MigrationRunner(backend, migrations=(), namespace_migrations=(migration,)).run()

    with backend.session() as connection:
        connection.execute(
            "UPDATE migration_records SET source_digest=? WHERE namespace=? AND migration_key=?",
            ("0" * 64, "foundation", "users"),
        )

    with pytest.raises(ValueError, match="migration_metadata_mismatch"):
        MigrationRunner(backend, migrations=(), namespace_migrations=(migration,)).run()


def test_graph_is_validated_before_any_namespace_migration_executes(tmp_path):
    backend = SQLiteBackend(tmp_path / "preflight.sqlite")
    executed = []

    def body(connection):
        executed.append("ran")
        connection.execute("CREATE TABLE namespace_probe (value TEXT)")

    valid = _namespace_migration(body=body)
    invalid = NamespaceMigration(
        namespace="foundation",
        migration_key="dependent",
        name="dependent",
        upgrade=body,
        prerequisites=(
            __import__("database.migrations.registry", fromlist=["MigrationRef"]).MigrationRef(
                "foundation", "missing"
            ),
        ),
        source_digest=hashlib.sha256(b"foundation:dependent").hexdigest(),
        source_bytes=b"foundation:dependent",
        _registry_token=_REGISTRY_TOKEN,
    )

    with pytest.raises(ValueError, match="unknown_migration_prerequisite"):
        MigrationRunner(backend, migrations=(), namespace_migrations=(valid, invalid))
    assert executed == []


def test_two_sqlite_runners_serialize_and_apply_once(tmp_path):
    backend_path = tmp_path / "concurrent.sqlite"
    calls = []

    def body(connection):
        calls.append("start")
        time.sleep(0.05)
        connection.execute("CREATE TABLE namespace_probe (value TEXT)")

    migration = _namespace_migration(body=body)
    results = []

    def run():
        results.append(MigrationRunner(
            SQLiteBackend(backend_path),
            migrations=(),
            namespace_migrations=(migration,),
        ).run())

    first = threading.Thread(target=run)
    second = threading.Thread(target=run)
    first.start()
    second.start()
    first.join()
    second.join()

    assert len(results) == 2
    assert results == [(), ()]
    assert calls == ["start"]
