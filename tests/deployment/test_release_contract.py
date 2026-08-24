from pathlib import Path

from deployment.scripts.release_metadata import derive_release_metadata, format_metadata
from deployment.scripts.validate_deployment_config import validate_configuration


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "deployment-contract.yml"


def test_release_metadata_is_derived_from_current_head():
    metadata = derive_release_metadata(repository_root=ROOT, source_date_epoch="0")

    assert len(metadata["SENTINEL_DNA_IMAGE_TAG"]) == 40
    assert metadata["SENTINEL_DNA_IMAGE_REVISION_FULL"] == metadata["SENTINEL_DNA_IMAGE_TAG"]
    assert metadata["SENTINEL_DNA_IMAGE_TAG"].startswith(metadata["SENTINEL_DNA_IMAGE_REVISION"])
    assert metadata["SENTINEL_DNA_IMAGE_CREATED"] == "1970-01-01T00:00:00Z"


def test_release_metadata_output_contains_no_secret_values():
    metadata = derive_release_metadata(repository_root=ROOT, source_date_epoch="0")
    output = format_metadata(metadata, "github-env")

    assert "SENTINEL_DNA_SECRET_KEY" not in output
    assert "POSTGRES_PASSWORD" not in output
    assert metadata["SENTINEL_DNA_IMAGE_REVISION_FULL"] in output


def test_missing_protected_values_fail_closed_without_echoing_values():
    metadata = derive_release_metadata(repository_root=ROOT, source_date_epoch="0")
    environment = {
        **metadata,
        "SENTINEL_DNA_ENV": "production",
        "SENTINEL_DNA_SECURE_COOKIES": "1",
    }
    errors = validate_configuration(environ=environment, repository_root=ROOT)

    assert "SENTINEL_DNA_SECRET_KEY:missing" in errors
    assert "POSTGRES_PASSWORD:missing" in errors
    assert all("replace-with" not in error for error in errors)


def test_placeholder_secret_is_rejected_without_echoing_value():
    metadata = derive_release_metadata(repository_root=ROOT, source_date_epoch="0")
    secret = "replace-with-a-random-secret-before-startup"
    environment = {
        **metadata,
        "SENTINEL_DNA_ENV": "production",
        "SENTINEL_DNA_SECURE_COOKIES": "1",
        "SENTINEL_DNA_SECRET_KEY": secret,
        "POSTGRES_PASSWORD": "replace-with-a-random-postgres-password-before-startup",
    }
    errors = validate_configuration(environ=environment, repository_root=ROOT)

    assert "SENTINEL_DNA_SECRET_KEY:invalid" in errors
    assert secret not in " ".join(errors)


def test_deployment_validation_requires_exact_trusted_release_artifact(tmp_path):
    metadata = derive_release_metadata(repository_root=ROOT, source_date_epoch="0")
    digest = "sha256:" + "a" * 64
    manifest = tmp_path / "metadata.json"
    manifest.write_text(
        '{"image_digest":"' + digest + '","release_sha":"' + metadata["SENTINEL_DNA_IMAGE_REVISION_FULL"] + '"}\n',
        encoding="utf-8",
    )
    manifest.chmod(0o444)
    environment = {
        **metadata,
        "SENTINEL_DNA_ENV": "production",
        "SENTINEL_DNA_SECURE_COOKIES": "1",
        "SENTINEL_DNA_SECRET_KEY": "test-only-secret-value-0123456789-abcdef",
        "POSTGRES_PASSWORD": "test-only-postgres-value-0123456789",
        "SENTINEL_DNA_IMAGE_DIGEST": digest,
        "SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE": str(manifest),
    }
    assert validate_configuration(environ=environment, repository_root=ROOT) == []


def test_deployment_validation_rejects_missing_trusted_release_artifact(tmp_path):
    metadata = derive_release_metadata(repository_root=ROOT, source_date_epoch="0")
    environment = {
        **metadata,
        "SENTINEL_DNA_ENV": "production",
        "SENTINEL_DNA_SECURE_COOKIES": "1",
        "SENTINEL_DNA_SECRET_KEY": "test-only-secret-value-0123456789-abcdef",
        "POSTGRES_PASSWORD": "test-only-postgres-value-0123456789",
        "SENTINEL_DNA_IMAGE_DIGEST": "sha256:" + "a" * 64,
        "SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE": str(tmp_path / "missing.json"),
    }
    errors = validate_configuration(environ=environment, repository_root=ROOT)
    assert "SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE:unavailable" in errors


def test_compose_preserves_internal_application_port_and_no_generated_env_mount():
    compose = (ROOT / "deployment" / "docker-compose.yml").read_text(encoding="utf-8")

    assert "env_file:" not in compose
    assert "5000:5000" not in compose
    assert 'ports: ["80:80", "443:443"]' in compose
    assert "SENTINEL_DNA_TLS_DIR:?set SENTINEL_DNA_TLS_DIR" in compose
    assert "target: /etc/nginx/tls" in compose
    assert "SENTINEL_DNA_SECRET_KEY:?set SENTINEL_DNA_SECRET_KEY" in compose
    assert "POSTGRES_PASSWORD:?set POSTGRES_PASSWORD" in compose
    assert "SENTINEL_DNA_IMAGE_DIGEST:?set SENTINEL_DNA_IMAGE_DIGEST" in compose
    assert "SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE:?set SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE" in compose
    assert "SENTINEL_DNA_GATE1_TRUSTED_METADATA_PATH: /run/sentinel/release/metadata.json" in compose
    assert "target: /run/sentinel/release/metadata.json" in compose
    assert "read_only: true" in compose


def test_nginx_contract_preserves_internal_app_and_secure_tls_forwarding():
    nginx = (ROOT / "deployment" / "nginx.conf").read_text(encoding="utf-8")

    assert "listen 80;" in nginx
    assert "return 308 https://$host$request_uri;" in nginx
    assert "listen 443 ssl;" in nginx
    assert "ssl_certificate /etc/nginx/tls/localhost.crt;" in nginx
    assert "ssl_certificate_key /etc/nginx/tls/localhost.key;" in nginx
    assert "proxy_pass http://app:5000;" in nginx
    assert "proxy_set_header X-Forwarded-Proto https;" in nginx


def test_ghcr_publication_contract_is_private_candidate_bound_and_non_deploying():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "contents: read" in workflow
    assert "packages: write" in workflow
    assert "ghcr.io/uwakwechukwuebukpaul-ai/sentinel-dna" in workflow
    assert "sha-${SENTINEL_DNA_IMAGE_REVISION_FULL}" in workflow
    assert "github.token" in workflow
    assert "--password-stdin" in workflow
    assert "docker push" in workflow
    assert ":latest" not in workflow.lower()
    assert "controlled_deploy.py --execute" not in workflow
    assert "docker compose up" not in workflow
    assert "org.opencontainers.image.revision" in workflow
    assert "SENTINEL_DNA_IMAGE_REVISION_FULL" in workflow
