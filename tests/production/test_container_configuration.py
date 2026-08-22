from pathlib import Path

from config.runtime import RuntimeConfig


ROOT = Path(__file__).resolve().parents[2]


def test_env_example_documents_all_production_runtime_values():
    example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "SENTINEL_DNA_ENV=production" in example
    assert "SENTINEL_DNA_SECRET_KEY=" in example
    assert "SENTINEL_DNA_SECURE_COOKIES=1" in example
    assert "SENTINEL_DNA_DB_PATH=/var/lib/sentinel/soc.db" in example
    assert "replace-with" in example


def test_documented_placeholder_cannot_start_production(monkeypatch, tmp_path):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", "replace-with-a-cryptographically-random-32-plus-character-secret")
    monkeypatch.setenv("SENTINEL_DNA_SECURE_COOKIES", "1")
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "soc.db"))

    try:
        RuntimeConfig.from_environment().validate()
    except RuntimeError as error:
        assert "SENTINEL_DNA_SECRET_KEY" in str(error)
    else:
        raise AssertionError("placeholder secret must fail closed")


def test_dockerignore_excludes_local_secrets_and_databases():
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert ".env" in dockerignore
    assert "*.db" in dockerignore
    assert "*.sqlite" in dockerignore


def test_deployment_compose_requires_external_secrets_and_exposes_canonical_services():
    compose = (ROOT / "deployment" / "docker-compose.yml").read_text(encoding="utf-8")

    assert "SENTINEL_DNA_SECRET_KEY: ${SENTINEL_DNA_SECRET_KEY:?" in compose
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?" in compose
    assert all(f"{service}:" in compose for service in ("postgres", "redis", "app", "nginx"))
    assert "127.0.0.1:5000/ready" not in compose
    assert 'expose: ["5000"]' in compose
    assert 'ports: ["5000:5000"]' not in compose
    assert "app: {condition: service_healthy}" in compose
