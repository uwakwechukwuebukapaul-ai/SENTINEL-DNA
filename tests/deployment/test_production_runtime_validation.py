import json
from pathlib import Path
import re

import yaml

from deployment.scripts.release_metadata import derive_release_metadata
from deployment.scripts.validate_deployment_config import validate_configuration
from deployment.scripts.validate_production_runtime import (
    ROOT,
    _external_file,
    _external_output,
    validate_runtime,
)


TEST_SECRET = "runtime-validation-secret-" + "x" * 48
TEST_POSTGRES_PASSWORD = "runtime-validation-postgres-" + "y" * 32


def test_production_compose_uses_file_backed_secrets_and_private_app_port():
    compose_path = ROOT / "deployment" / "docker-compose.yml"
    compose_text = compose_path.read_text(encoding="utf-8")
    compose = yaml.safe_load(compose_text)

    assert "PGPASSWORD" not in compose_text
    assert compose["services"]["app"]["environment"]["SENTINEL_DNA_SECRET_KEY_FILE"] == "/run/secrets/sentinel_dna_secret_key"
    assert compose["services"]["app"]["environment"]["SENTINEL_DNA_POSTGRES_PASSWORD_FILE"] == "/run/secrets/sentinel_dna_postgres_password"
    assert compose["services"]["postgres"]["environment"]["POSTGRES_PASSWORD_FILE"] == "/run/secrets/sentinel_dna_postgres_password"
    assert compose["services"]["app"]["environment"]["DATABASE_URL"] == "${DATABASE_URL:?set DATABASE_URL}"
    assert "ports" not in compose["services"]["app"]
    assert compose["secrets"]["production_app_secret_key"]["environment"] == "SENTINEL_DNA_SECRET_KEY"
    assert compose["secrets"]["production_postgres_password"]["environment"] == "POSTGRES_PASSWORD"

    root_compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "PGPASSWORD" not in root_compose_text
    assert "SENTINEL_DNA_SECRET_KEY_FILE: /run/secrets/sentinel_dna_secret_key" in root_compose_text
    assert "SENTINEL_DNA_POSTGRES_PASSWORD_FILE: /run/secrets/sentinel_dna_postgres_password" in root_compose_text


def test_validation_inputs_must_remain_external(tmp_path):
    env_file = tmp_path / "production.env"
    env_file.write_text("SENTINEL_DNA_SECRET_KEY=not-a-secret\n", encoding="utf-8")
    assert _external_file(env_file, label="env_file") == env_file.resolve()

    try:
        _external_file(Path("relative.env"), label="env_file")
    except ValueError as error:
        assert str(error) == "env_file_must_be_absolute"
    else:
        raise AssertionError("relative environment files must be rejected")

    try:
        _external_output(ROOT / "deployment-evidence" / "runtime.json")
    except ValueError as error:
        assert str(error) == "evidence_output_must_be_outside_repository"
    else:
        raise AssertionError("repository-local evidence must be rejected")


def test_generated_release_metadata_and_trusted_file_are_valid_runtime_inputs(tmp_path):
    metadata = derive_release_metadata(repository_root=ROOT, source_date_epoch="0")
    trusted_metadata = tmp_path / "release" / "metadata.json"
    trusted_metadata.parent.mkdir()
    trusted_metadata.write_text(
        json.dumps(
            {
                "release_sha": metadata["SENTINEL_DNA_IMAGE_REVISION_FULL"],
                "image_digest": "sha256:" + "a" * 64,
            },
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    trusted_metadata.chmod(0o444)

    assert re.fullmatch(r"[0-9a-f]{40}", metadata["SENTINEL_DNA_IMAGE_TAG"])
    assert re.fullmatch(r"[0-9a-f]{9}", metadata["SENTINEL_DNA_IMAGE_REVISION"])
    assert metadata["SENTINEL_DNA_IMAGE_REVISION_FULL"] == metadata["SENTINEL_DNA_IMAGE_TAG"]
    assert metadata["SENTINEL_DNA_IMAGE_REVISION_FULL"].startswith(metadata["SENTINEL_DNA_IMAGE_REVISION"])

    environment = {
        **metadata,
        "SENTINEL_DNA_ENV": "production",
        "SENTINEL_DNA_SECURE_COOKIES": "1",
        "SENTINEL_DNA_SECRET_KEY": TEST_SECRET,
        "POSTGRES_PASSWORD": TEST_POSTGRES_PASSWORD,
        "DATABASE_URL": "postgresql://sentinel:password@postgres:5432/sentinel_dna",
        "SENTINEL_DNA_IMAGE_DIGEST": "sha256:" + "a" * 64,
        "SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE": str(trusted_metadata),
    }

    assert validate_configuration(
        environ=environment,
        repository_root=ROOT,
        require_postgresql=True,
    ) == []


def test_runtime_validator_uses_protected_file_revision_over_inherited_value(tmp_path, monkeypatch):
    metadata = derive_release_metadata(repository_root=ROOT, source_date_epoch="0")
    trusted_metadata = tmp_path / "metadata.json"
    trusted_metadata.write_text(
        json.dumps(
            {
                "release_sha": metadata["SENTINEL_DNA_IMAGE_REVISION_FULL"],
                "image_digest": "sha256:" + "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    trusted_metadata.chmod(0o444)
    env_file = tmp_path / "production.env"
    env_file.write_text(
        "\n".join(
            [
                *(
                    f"{name}={value}"
                    for name, value in metadata.items()
                ),
                "SENTINEL_DNA_ENV=production",
                f"SENTINEL_DNA_SECRET_KEY={TEST_SECRET}",
                f"POSTGRES_PASSWORD={TEST_POSTGRES_PASSWORD}",
                "DATABASE_URL=postgresql://sentinel:password@postgres:5432/sentinel_dna",
                "SENTINEL_DNA_IMAGE_DIGEST=sha256:" + "a" * 64,
                f"SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE={trusted_metadata}",
                "SENTINEL_DNA_SECURE_COOKIES=1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SENTINEL_DNA_IMAGE_REVISION_FULL", "626eed8ecc83b67b90d8baf04112d1e05a685196")
    monkeypatch.setattr(
        "deployment.scripts.validate_production_runtime._run",
        lambda *args, **kwargs: (False, "synthetic_command_failure"),
    )

    report = validate_runtime(
        env_file=env_file,
        project_name="sentinel-dna-test",
        wait_seconds=1,
    )

    assert report["evidence"]["config_error_codes"] == []
    assert report["failures"] == ["compose_config"]


def test_registry_sha_tag_is_not_accepted_as_the_local_compose_tag(tmp_path):
    metadata = derive_release_metadata(repository_root=ROOT, source_date_epoch="0")
    trusted_metadata = tmp_path / "metadata.json"
    trusted_metadata.write_text(
        json.dumps(
            {
                "release_sha": metadata["SENTINEL_DNA_IMAGE_REVISION_FULL"],
                "image_digest": "sha256:" + "b" * 64,
            }
        ),
        encoding="utf-8",
    )
    trusted_metadata.chmod(0o444)
    environment = {
        **metadata,
        "SENTINEL_DNA_IMAGE_TAG": "sha-" + metadata["SENTINEL_DNA_IMAGE_REVISION_FULL"],
        "SENTINEL_DNA_ENV": "production",
        "SENTINEL_DNA_SECURE_COOKIES": "1",
        "SENTINEL_DNA_SECRET_KEY": TEST_SECRET,
        "POSTGRES_PASSWORD": TEST_POSTGRES_PASSWORD,
        "DATABASE_URL": "postgresql://sentinel:password@postgres:5432/sentinel_dna",
        "SENTINEL_DNA_IMAGE_DIGEST": "sha256:" + "b" * 64,
        "SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE": str(trusted_metadata),
    }

    errors = validate_configuration(
        environ=environment,
        repository_root=ROOT,
        require_postgresql=True,
    )

    assert "SENTINEL_DNA_IMAGE_TAG:does-not-match-HEAD" in errors
