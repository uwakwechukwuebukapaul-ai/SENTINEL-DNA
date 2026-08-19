import importlib
import importlib.util
from pathlib import Path

from database.connection import DatabaseConnection, resolve_database_path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MIGRATION_PATH = (
    REPOSITORY_ROOT
    / "database"
    / "migrations"
    / "migrate_ioc_contract.py"
)


def load_migration_module():
    spec = importlib.util.spec_from_file_location(
        "ioc_path_contract_migration",
        MIGRATION_PATH,
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_default_database_path_is_repository_soc_db(monkeypatch):
    monkeypatch.delenv("SENTINEL_DNA_DB_PATH", raising=False)

    expected = (REPOSITORY_ROOT / "soc.db").resolve()

    assert resolve_database_path() == expected
    assert Path(DatabaseConnection().database_path) == expected


def test_configured_database_path_is_shared_by_consumers(monkeypatch, tmp_path):
    configured = (tmp_path / "configured.db").resolve()
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(configured))

    import dashboard.app as dashboard_app

    dashboard_app = importlib.reload(dashboard_app)
    migration = load_migration_module()

    assert dashboard_app.DB_PATH == configured
    assert Path(DatabaseConnection().database_path) == configured
    assert migration.DATABASE_PATH == configured
