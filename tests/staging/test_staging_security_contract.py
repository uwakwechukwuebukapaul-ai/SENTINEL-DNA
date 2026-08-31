from datetime import datetime, timezone
import json
from pathlib import Path
import os
import subprocess
import sys

import pytest
import yaml
from cryptography import x509
from cryptography.hazmat.primitives import serialization

from config.runtime import RuntimeConfig
from services.core.pilot_boundary import pilot_path_allowed
from tests.credential_helpers import random_secret


ROOT = Path(__file__).resolve().parents[2]
STAGING_COMPOSE = ROOT / "deployment" / "staging" / "docker-compose.yml"
STAGING_OVERRIDE = ROOT / "deployment" / "staging" / "docker-compose.pilot.override.yml"


def staging_secret() -> str:
    """Return a random secret that satisfies the staging secret contract."""
    # token_urlsafe() may contain patterns that staging correctly rejects,
    # such as "__" or placeholder-like hyphenated sequences.
    return random_secret().replace("-", "a").replace("_", "a")


def staging_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "staging")
    monkeypatch.setenv("SENTINEL_DNA_PILOT_ACCESS_REQUIRED", "1")
    monkeypatch.setenv("SENTINEL_DNA_SECURE_COOKIES", "1")
    monkeypatch.setenv("FLASK_DEBUG", "0")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", staging_secret())
    monkeypatch.setenv(
        "SENTINEL_DNA_CONFIG_SOURCE_CLASSIFICATION", "external_non_production"
    )
    monkeypatch.setenv(
        "SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION", "disposable_staging"
    )
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://staging-user:staging-password@postgres:5432/sentinel"
    )
    monkeypatch.setenv("SENTINEL_DNA_DB_PATH", str(tmp_path / "unused.sqlite"))


def test_staging_runtime_requires_external_secret_and_postgresql(monkeypatch, tmp_path):
    staging_environment(tmp_path, monkeypatch)
    config = RuntimeConfig.from_environment()
    config.validate()
    assert config.pilot_access_required is True
    assert config.database_url.startswith("postgresql://")

    monkeypatch.delenv("SENTINEL_DNA_SECRET_KEY")
    with pytest.raises(RuntimeError, match="SENTINEL_DNA_SECRET_KEY"):
        RuntimeConfig.from_environment().validate()

    staging_environment(tmp_path, monkeypatch)
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", staging_secret())
    monkeypatch.setenv("DATABASE_URL", "sqlite:///production.sqlite")
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        RuntimeConfig.from_environment().validate()


def test_staging_runtime_consumes_secret_key_from_docker_secret_file(monkeypatch, tmp_path):
    staging_environment(tmp_path, monkeypatch)
    secret = staging_secret()
    secret_file = tmp_path / "sentinel-dna-secret-key"
    secret_file.write_text(secret + "\n", encoding="utf-8")
    monkeypatch.delenv("SENTINEL_DNA_SECRET_KEY")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY_FILE", str(secret_file))

    config = RuntimeConfig.from_environment()
    config.validate()

    assert config.secret_key == secret
    assert config.secret_was_configured is True


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("SENTINEL_DNA_PILOT_ACCESS_REQUIRED", "0", "PILOT_ACCESS_REQUIRED"),
        ("SENTINEL_DNA_SECURE_COOKIES", "true", "SECURE_COOKIES"),
        ("FLASK_DEBUG", "1", "FLASK_DEBUG"),
        (
            "SENTINEL_DNA_CONFIG_SOURCE_CLASSIFICATION",
            "production",
            "CONFIG_SOURCE_CLASSIFICATION",
        ),
        (
            "SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION",
            "production",
            "DATABASE_TARGET_CLASSIFICATION",
        ),
    ],
)
def test_staging_runtime_rejects_missing_or_insecure_controls(
    monkeypatch, tmp_path, name, value, message
):
    staging_environment(tmp_path, monkeypatch)
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match=message):
        RuntimeConfig.from_environment().validate()


def test_pilot_boundary_is_allowlist_and_denies_non_pilot_surfaces():
    assert pilot_path_allowed("/workspace/investigation/CASE-1", "GET")
    assert pilot_path_allowed("/api/investigations/CASE-1/feedback", "POST")
    assert pilot_path_allowed("/api/auth/logout", "POST")

    for path in (
        "/api/automation/history",
        "/api/automation/execute",
        "/api/soc/dashboard",
        "/api/incidents",
        "/api/organizations/users",
        "/api/auth/sessions",
        "/workspace/live",
        "/workspace/analyst/CASE-1/start",
    ):
        assert not pilot_path_allowed(path, "GET")


def test_staging_compose_and_deploy_contract_are_explicit():
    compose = STAGING_COMPOSE.read_text()
    root_compose = (ROOT / "docker-compose.yml").read_text()
    deploy = (ROOT / "deployment" / "scripts" / "deploy.sh").read_text()
    override = STAGING_OVERRIDE.read_text()

    assert "SENTINEL_DNA_ENV: staging" in compose
    assert 'SENTINEL_DNA_PILOT_ACCESS_REQUIRED: "1"' in compose
    assert 'SENTINEL_DNA_SECURE_COOKIES: "1"' in compose
    assert "FLASK_DEBUG: \"0\"" in compose
    assert "DATABASE_URL: postgresql://sentinel@postgres:5432/sentinel_dna" in compose
    assert "PGPASSWORD" not in compose
    assert "SENTINEL_DNA_SECRET_KEY: ${" not in compose
    assert "SENTINEL_DNA_POSTGRES_PASSWORD: ${" not in compose
    assert "SENTINEL_DNA_SECRET_KEY_FILE: /run/secrets/sentinel_dna_secret_key" in compose
    assert "SENTINEL_DNA_POSTGRES_PASSWORD_FILE: /run/secrets/sentinel_dna_postgres_password" in compose
    assert "POSTGRES_PASSWORD_FILE: /run/secrets/sentinel_dna_postgres_password" in compose
    assert "file: ${SENTINEL_DNA_STAGING_APP_SECRET_FILE:?set external application secret file}" in compose
    assert "file: ${SENTINEL_DNA_STAGING_POSTGRES_PASSWORD_FILE:?set external database secret file}" in compose
    assert 'command: ["python", "-m", "database.run_migrations"]' in compose
    assert "  migration:" in compose
    assert "condition: service_healthy" in compose
    assert 'test: ["CMD", "redis-cli", "ping"]' in compose
    assert "staging_internal:" in compose
    assert "internal: true" in compose
    rendered = yaml.safe_load(compose)
    assert rendered["services"]["edge"]["ports"] == ["0.0.0.0:8443:443"]
    assert "ports" not in rendered["services"]["app"]
    assert rendered["services"]["app"]["expose"] == ["5000"]
    assert "ports" not in rendered["services"]["postgres"]
    assert "ports" not in rendered["services"]["redis"]
    assert set(rendered["services"]["edge"]["networks"]) == {"staging_edge"}
    assert set(rendered["services"]["app"]["networks"]) == {"staging_edge", "staging_internal"}
    assert set(rendered["services"]["postgres"]["networks"]) == {"staging_internal"}
    assert set(rendered["services"]["redis"]["networks"]) == {"staging_internal"}
    assert rendered["networks"]["staging_internal"]["internal"] is True
    override_rendered = yaml.safe_load(override)
    assert override_rendered["services"]["edge"]["ports"] == ["127.0.0.1:8443:443"]
    assert override_rendered["services"]["app"]["image"] == "${SENTINEL_DNA_PILOT_IMAGE_REFERENCE:?set inspected pilot image reference}"
    assert override_rendered["services"]["migration"]["image"] == "${SENTINEL_DNA_PILOT_IMAGE_REFERENCE:?set inspected pilot image reference}"
    assert override_rendered["services"]["app"]["build"] is None
    assert override_rendered["services"]["migration"]["build"] is None
    assert "loopback" in override.lower()
    assert "--file \"$STAGING_COMPOSE\"" in deploy
    assert "--file \"$STAGING_OVERRIDE\"" in deploy
    assert "--env-file \"$STAGING_ENV_FILE\"" in deploy
    assert "Pilot staging Compose override was not found" in deploy
    assert "SENTINEL_DNA_BASE_URL must use HTTPS" in deploy
    assert "SENTINEL_DNA_IMAGE_TAG" in deploy
    assert "SENTINEL_DNA_IMAGE_REVISION_FULL" in deploy
    assert "git -C \"$REPOSITORY_ROOT\" rev-parse HEAD" in deploy
    assert "git -C \"$REPOSITORY_ROOT\" status --porcelain --untracked-files=all" in deploy
    assert "up -d --build postgres redis" in deploy
    assert "run --rm --build migration" in deploy
    assert "docker compose up -d --build" not in deploy
    assert "Missing .env" not in deploy
    root_rendered = yaml.safe_load(root_compose)
    assert root_rendered["services"]["migration"]["command"] == ["python", "-m", "database.run_migrations"]
    assert "migration" in root_rendered["services"]


def test_staging_compose_config_uses_secret_sources_without_rendering_values(tmp_path):
    secret = random_secret()
    postgres_password = random_secret()
    env_file = tmp_path / "staging.env"
    env_file.write_text(
        "\n".join(
            (
                "SENTINEL_DNA_SECRET_KEY=" + secret,
                "SENTINEL_DNA_POSTGRES_PASSWORD=" + postgres_password,
                "SENTINEL_DNA_STAGING_EDGE_IMAGE=nginx:1.27-alpine",
                "SENTINEL_DNA_STAGING_EDGE_CONFIG_FILE=/tmp/staging-nginx.conf",
                "SENTINEL_DNA_STAGING_TLS_DIR=/tmp/staging-tls",
                "SENTINEL_DNA_STAGING_APP_SECRET_FILE=" + str(tmp_path / "app.secret"),
                "SENTINEL_DNA_STAGING_POSTGRES_PASSWORD_FILE=" + str(tmp_path / "postgres.secret"),
                "SENTINEL_DNA_IMAGE_TAG=f44ec8747ad1bd8e6ee5c76be039e2826cb3c0fc",
                "SENTINEL_DNA_IMAGE_REVISION_FULL=f44ec8747ad1bd8e6ee5c76be039e2826cb3c0fc",
                "SENTINEL_DNA_IMAGE_CREATED=2026-08-29T00:00:00Z",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--project-name",
            "sentinel-dna-gate2-secret-test",
            "--env-file",
            str(env_file),
            "--file",
            str(ROOT / "deployment" / "staging" / "docker-compose.yml"),
            "config",
            "--format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert secret not in result.stdout
    assert postgres_password not in result.stdout
    assert "PGPASSWORD" not in result.stdout
    rendered = json.loads(result.stdout)
    app_environment = rendered["services"]["app"]["environment"]
    migration_environment = rendered["services"]["migration"]["environment"]
    postgres_environment = rendered["services"]["postgres"]["environment"]
    assert "SENTINEL_DNA_SECRET_KEY" not in app_environment
    assert "SENTINEL_DNA_POSTGRES_PASSWORD" not in app_environment
    assert app_environment["SENTINEL_DNA_SECRET_KEY_FILE"] == "/run/secrets/sentinel_dna_secret_key"
    assert app_environment["SENTINEL_DNA_POSTGRES_PASSWORD_FILE"] == "/run/secrets/sentinel_dna_postgres_password"
    assert migration_environment["SENTINEL_DNA_SECRET_KEY_FILE"] == "/run/secrets/sentinel_dna_secret_key"
    assert migration_environment["SENTINEL_DNA_POSTGRES_PASSWORD_FILE"] == "/run/secrets/sentinel_dna_postgres_password"
    assert postgres_environment["POSTGRES_PASSWORD_FILE"] == "/run/secrets/sentinel_dna_postgres_password"
    assert rendered["secrets"]["staging_app_secret_key"]["file"] == str(tmp_path / "app.secret")
    assert rendered["secrets"]["staging_postgres_password"]["file"] == str(tmp_path / "postgres.secret")


def test_staging_environment_declares_stable_tls_identity_and_configured_lan_ip():
    env_example = (ROOT / "deployment" / "staging" / ".env.example").read_text()
    assert "SENTINEL_DNA_BASE_URL=https://sentinel-dna-staging:8443" in env_example
    assert "SENTINEL_DNA_STAGING_TLS_IP=192.168.1.115" in env_example
    assert "SENTINEL_DNA_SECRET_KEY=__INJECT_NON_PRODUCTION_SECRET__" in env_example
    assert "SENTINEL_DNA_POSTGRES_PASSWORD=__INJECT_DISPOSABLE_STAGING_PASSWORD__" in env_example


def test_staging_nginx_contract_terminates_tls_and_keeps_gunicorn_private():
    nginx = (ROOT / "deployment" / "staging" / "nginx.conf").read_text()
    assert "listen 443 ssl;" in nginx
    assert "ssl_certificate /etc/nginx/tls/staging.crt;" in nginx
    assert "ssl_certificate_key /etc/nginx/tls/staging.key;" in nginx
    assert "ssl_protocols TLSv1.2 TLSv1.3;" in nginx
    assert "proxy_pass http://app:5000;" in nginx
    assert "proxy_set_header X-Forwarded-Proto https;" in nginx
    assert "5000:5000" not in nginx
    assert "sentinel-dna-staging" in nginx


def _run_staging_certificate_generator(tmp_path: Path, ip: str = "192.168.1.115", *args: str):
    environment = os.environ.copy()
    environment["SENTINEL_DNA_STAGING_TLS_DIR"] = str(tmp_path)
    environment["SENTINEL_DNA_STAGING_TLS_IP"] = ip
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "deployment" / "staging" / "scripts" / "generate_staging_cert.py"),
            *args,
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _certificate_from(tmp_path: Path) -> tuple[x509.Certificate, object]:
    certificate = x509.load_pem_x509_certificate((tmp_path / "staging.crt").read_bytes())
    key = serialization.load_pem_private_key((tmp_path / "staging.key").read_bytes(), password=None)
    return certificate, key


def test_staging_certificate_generator_emits_required_sans_and_valid_key_pair(tmp_path):
    result = _run_staging_certificate_generator(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "PRIVATE KEY" not in result.stdout + result.stderr

    certificate, key = _certificate_from(tmp_path)
    sans = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert sans.get_values_for_type(x509.DNSName) == ["sentinel-dna-staging"]
    assert {str(value) for value in sans.get_values_for_type(x509.IPAddress)} == {
        "192.168.1.115",
        "127.0.0.1",
    }
    assert certificate.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value == "sentinel-dna-staging"
    assert certificate.public_key().public_numbers() == key.public_key().public_numbers()
    now = datetime.now(timezone.utc)
    assert certificate.not_valid_before_utc <= now <= certificate.not_valid_after_utc
    assert certificate.signature_hash_algorithm.name == "sha256"
    if os.name != "nt":
        assert (tmp_path / "staging.key").stat().st_mode & 0o777 == 0o600


def test_staging_certificate_generator_is_safe_to_rerun_and_requires_explicit_rotation(tmp_path):
    first = _run_staging_certificate_generator(tmp_path)
    assert first.returncode == 0, first.stderr
    original = (tmp_path / "staging.crt").read_bytes()
    rerun = _run_staging_certificate_generator(tmp_path)
    assert rerun.returncode == 0, rerun.stderr
    assert (tmp_path / "staging.crt").read_bytes() == original

    mismatch = _run_staging_certificate_generator(tmp_path, "192.168.1.116")
    assert mismatch.returncode == 2
    assert "--rotate" in mismatch.stderr
    rotated = _run_staging_certificate_generator(tmp_path, "192.168.1.116", "--rotate")
    assert rotated.returncode == 0, rotated.stderr
    certificate, _ = _certificate_from(tmp_path)
    ips = {str(value) for value in certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.IPAddress)}
    assert ips == {"192.168.1.116", "127.0.0.1"}


def test_staging_certificate_generator_fails_closed_for_missing_or_invalid_configuration(tmp_path):
    environment = os.environ.copy()
    environment.pop("SENTINEL_DNA_STAGING_TLS_DIR", None)
    environment["SENTINEL_DNA_STAGING_TLS_IP"] = "192.168.1.115"
    result = subprocess.run(
        [sys.executable, str(ROOT / "deployment" / "staging" / "scripts" / "generate_staging_cert.py")],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "SENTINEL_DNA_STAGING_TLS_DIR" in result.stderr
    invalid = _run_staging_certificate_generator(tmp_path, "not-an-ip")
    assert invalid.returncode == 2
    assert "must contain an IP address" in invalid.stderr


def test_staging_secret_hygiene_contract_has_no_tracked_runtime_tls_or_secret_files():
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert not any(
        Path(path).name.lower().endswith((".key", ".crt", ".pem", ".p12", ".pfx"))
        or Path(path).name.lower() in {"staging.env", "staging.env.backup"}
        for path in tracked
    )
    gitignore = (ROOT / ".gitignore").read_text()
    for rule in ("*.key", "*.crt", "*.pem", "*.p12", "*.pfx", "staging.env"):
        assert rule in gitignore


def test_staging_certificate_configuration_is_explicit_and_non_secret():
    config = json.loads((ROOT / "deployment" / "staging" / "staging-cert-config.json").read_text())
    assert config["dns_sans"] == ["sentinel-dna-staging"]
    assert config["fixed_ip_sans"] == ["127.0.0.1"]
    assert config["lan_ip_environment_variable"] == "SENTINEL_DNA_STAGING_TLS_IP"
    assert config["certificate_filename"] == "staging.crt"
    assert config["private_key_filename"] == "staging.key"
    assert config["key_algorithm"] == "RSA"
    assert config["key_size"] >= 2048
    assert config["signature_hash"] == "SHA-256"
