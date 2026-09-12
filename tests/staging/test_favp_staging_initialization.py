import json
from types import SimpleNamespace

from database.backend import SQLiteBackend
from database.migration_runner import MigrationRunner, STAGING_MIGRATIONS
from database.migrations.registry import (
    MIGRATIONS,
    MIGRATION_MODULES,
    STAGING_MIGRATION_MODULES,
)


def test_staging_migrations_leave_opt_in_favp_disabled_deployment_bootable(monkeypatch, capsys):
    import database.run_migrations as run_migrations

    selected = []
    initialized = []

    class Runner:
        def __init__(self, _backend, *, migrations):
            selected.append(migrations)

        def run(self):
            return ()

    monkeypatch.delenv("SENTINEL_DNA_FAVP_OPERATIONS_ENABLED", raising=False)
    monkeypatch.setattr(
        run_migrations.RuntimeConfig,
        "from_environment",
        lambda: SimpleNamespace(environment="staging", validate=lambda: None),
    )
    monkeypatch.setattr(run_migrations, "database_for_environment", lambda **_kwargs: object())
    monkeypatch.setattr(run_migrations, "MigrationRunner", Runner)
    monkeypatch.setattr(
        "database.staging_favp_bootstrap.initialize_staging_artifacts",
        lambda *_args, **_kwargs: initialized.append(True),
    )

    assert run_migrations.main() == 0
    assert selected == [MIGRATIONS]
    assert initialized == []
    assert "database migrations applied: none" in capsys.readouterr().out


def test_enabled_favp_staging_selects_staging_chain_and_bootstraps_custody(monkeypatch, capsys):
    import database.run_migrations as run_migrations

    selected = []
    initialized = []

    class Runner:
        def __init__(self, _backend, *, migrations):
            selected.append(migrations)

        def run(self):
            return (9,)

    monkeypatch.setenv("SENTINEL_DNA_FAVP_OPERATIONS_ENABLED", "1")
    monkeypatch.setenv("SENTINEL_DNA_FAVP_SYNTHETIC_ONLY", "1")
    monkeypatch.setenv("SENTINEL_DNA_FAVP_PRODUCTION_ACCESS", "0")
    monkeypatch.setattr(
        run_migrations.RuntimeConfig,
        "from_environment",
        lambda: SimpleNamespace(environment="staging", validate=lambda: None),
    )
    monkeypatch.setattr(run_migrations, "database_for_environment", lambda **_kwargs: object())
    monkeypatch.setattr(run_migrations, "MigrationRunner", Runner)
    monkeypatch.setattr(
        "database.staging_favp_bootstrap.initialize_staging_artifacts",
        lambda *_args, **_kwargs: initialized.append(True),
    )

    assert run_migrations.main() == 0
    assert selected == [STAGING_MIGRATIONS]
    assert initialized == [True]
    assert "database migrations applied: 9" in capsys.readouterr().out


def test_staging_registry_discovers_favp_migration_009():
    assert STAGING_MIGRATION_MODULES[-1] == "database.migrations.009_favp_staging"
    assert [migration.version for migration in STAGING_MIGRATIONS] == list(range(1, 10))
    assert STAGING_MIGRATIONS[-1].name == "Disposable staging FAVP operations and execution schema"
    assert callable(STAGING_MIGRATIONS[-1].upgrade)


def test_staging_migration_initializes_favp_schema_audit_guards_and_catalog(tmp_path):
    backend = SQLiteBackend(tmp_path / "favp-staging.sqlite")

    assert MigrationRunner(backend, migrations=STAGING_MIGRATIONS).run() == tuple(range(1, 10))
    assert MigrationRunner(backend, migrations=STAGING_MIGRATIONS).run() == ()

    with backend.session() as connection:
        versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        guards = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name LIKE 'audit_events_append_only_%'"
        ).fetchone()[0]
        scenarios = connection.execute(
            "SELECT scenario_id,scenario_json,synthetic FROM favp_execution_scenarios ORDER BY scenario_id"
        ).fetchall()

    assert versions == list(range(1, 10))
    assert {"audit_events", "favp_execution_profiles", "favp_execution_scenarios", "favp_evidence_validations"} <= tables
    assert guards == 2
    assert len(scenarios) == 8
    assert all(row[2] == 1 and json.loads(row[1])["synthetic"] is True for row in scenarios)


def test_staging_migration_is_not_in_the_default_production_chain():
    assert [migration.version for migration in MIGRATIONS] == list(range(1, 9))
    assert "database.migrations.009_favp_staging" not in MIGRATION_MODULES
    assert [migration.version for migration in STAGING_MIGRATIONS] == list(range(1, 10))
