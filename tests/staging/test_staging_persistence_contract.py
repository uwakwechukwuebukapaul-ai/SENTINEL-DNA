from pathlib import Path

import yaml

from database.backend import DatabaseSettings, SQLiteBackend


ROOT = Path(__file__).resolve().parents[2]
STAGING_COMPOSE = ROOT / "deployment" / "staging" / "docker-compose.yml"
STAGING_ENV_EXAMPLE = ROOT / "deployment" / "staging" / ".env.example"
CANONICAL_SQLITE_PATH = "/var/lib/sentinel/soc.db"


def _staging_compose() -> dict:
    return yaml.safe_load(STAGING_COMPOSE.read_text(encoding="utf-8"))


def test_staging_sqlite_path_matches_the_named_volume_contract():
    compose = _staging_compose()
    app = compose["services"]["app"]
    migration = compose["services"]["migration"]

    assert app["environment"]["SENTINEL_DNA_DB_PATH"] == CANONICAL_SQLITE_PATH
    assert migration["environment"]["SENTINEL_DNA_DB_PATH"] == CANONICAL_SQLITE_PATH
    assert "staging_app_data:/var/lib/sentinel" in app["volumes"]
    assert "/var/lib/sentinel/staging/soc.db" not in STAGING_COMPOSE.read_text()
    env_example = STAGING_ENV_EXAMPLE.read_text()
    assert f"SENTINEL_DNA_DB_PATH={CANONICAL_SQLITE_PATH}" in env_example
    assert "/var/lib/sentinel/staging/soc.db" not in env_example


def test_staging_database_url_is_authoritative_over_sqlite_compatibility_path():
    compose = _staging_compose()
    app_environment = compose["services"]["app"]["environment"]
    migration_environment = compose["services"]["migration"]["environment"]

    assert app_environment["DATABASE_URL"] == migration_environment["DATABASE_URL"]
    settings = DatabaseSettings.from_environment(
        {
            "DATABASE_URL": app_environment["DATABASE_URL"],
            "SENTINEL_DNA_DB_PATH": "/unexpected/fallback.sqlite",
        }
    )
    assert settings.backend == "postgresql"
    assert settings.database_path is None
    assert "staging_postgres_data:/var/lib/postgresql/data" in compose["services"]["postgres"]["volumes"]


def test_configured_sqlite_path_opens_and_writes_without_fallback(tmp_path, monkeypatch):
    mounted_root = tmp_path / "mounted-volume"
    mounted_root.mkdir()
    configured_path = mounted_root / "soc.db"
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(configured_path))

    backend = SQLiteBackend()
    assert Path(backend.database_path) == configured_path.resolve()
    assert Path(backend.database_path).parent.is_dir()

    with backend.session() as connection:
        connection.execute("CREATE TABLE persistence_probe (value TEXT NOT NULL)")
        connection.execute("INSERT INTO persistence_probe VALUES (?)", ("ok",))

    assert configured_path.is_file()
    with backend.session() as connection:
        assert connection.execute(
            "SELECT value FROM persistence_probe"
        ).fetchone()[0] == "ok"


def test_staging_runtime_user_can_write_the_mounted_database_root():
    dockerfile = (ROOT / "Dockerfile").read_text()
    compose = _staging_compose()

    assert "useradd --create-home --uid 10001 sentinel" in dockerfile
    assert "chown -R sentinel:sentinel /app /var/lib/sentinel" in dockerfile
    assert "USER sentinel" in dockerfile
    assert "staging_app_data:/var/lib/sentinel" in compose["services"]["app"]["volumes"]
    assert compose["services"]["app"]["read_only"] is True


def test_staging_migration_and_application_share_the_authoritative_persistence_contract():
    compose = _staging_compose()
    app = compose["services"]["app"]
    migration = compose["services"]["migration"]

    assert migration["command"] == ["python", "-m", "database.run_migrations"]
    assert migration["depends_on"]["postgres"]["condition"] == "service_healthy"
    assert app["depends_on"]["postgres"]["condition"] == "service_healthy"
    assert app["environment"]["DATABASE_URL"] == migration["environment"]["DATABASE_URL"]
    assert "staging_postgres_data:/var/lib/postgresql/data" in compose["services"]["postgres"]["volumes"]


def test_staging_build_requires_candidate_derived_immutable_image_metadata():
    compose = _staging_compose()
    for service in (compose["services"]["app"], compose["services"]["migration"]):
        assert service["image"] == "staging-app:${SENTINEL_DNA_IMAGE_TAG:?set SENTINEL_DNA_IMAGE_TAG}"
        args = service["build"]["args"]
        assert args["VCS_REF"] == "${SENTINEL_DNA_IMAGE_REVISION_FULL:?set SENTINEL_DNA_IMAGE_REVISION_FULL}"
        assert args["VCS_REF_FULL"] == "${SENTINEL_DNA_IMAGE_REVISION_FULL:?set SENTINEL_DNA_IMAGE_REVISION_FULL}"
        assert args["IMAGE_VERSION"] == "${SENTINEL_DNA_IMAGE_TAG:?set SENTINEL_DNA_IMAGE_TAG}"
        assert args["IMAGE_CREATED"] == "${SENTINEL_DNA_IMAGE_CREATED:?set SENTINEL_DNA_IMAGE_CREATED}"
        assert args["IMAGE_SOURCE"] == "https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA"
