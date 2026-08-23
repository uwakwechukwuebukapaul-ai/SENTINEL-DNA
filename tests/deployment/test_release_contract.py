from pathlib import Path

from deployment.scripts.release_metadata import derive_release_metadata, format_metadata
from deployment.scripts.validate_deployment_config import validate_configuration


ROOT = Path(__file__).resolve().parents[2]


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


def test_compose_preserves_internal_application_port_and_no_generated_env_mount():
    compose = (ROOT / "deployment" / "docker-compose.yml").read_text(encoding="utf-8")

    assert "env_file:" not in compose
    assert "5000:5000" not in compose
    assert 'ports: ["80:80"]' in compose
    assert "SENTINEL_DNA_SECRET_KEY:?set SENTINEL_DNA_SECRET_KEY" in compose
    assert "POSTGRES_PASSWORD:?set POSTGRES_PASSWORD" in compose
