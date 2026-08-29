from pathlib import Path

import yaml

from deployment.scripts.release_metadata import derive_release_metadata, format_metadata
from deployment.scripts.validate_deployment_config import validate_configuration
from tests.credential_helpers import random_password, random_secret


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "deployment-contract.yml"
TEST_SECRET = random_secret()
TEST_POSTGRES_PASSWORD = random_password()


def _workflow() -> dict:
    parsed = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def _trigger(workflow: dict) -> dict:
    # PyYAML YAML 1.1 resolves the GitHub Actions `on` key as True.
    trigger = workflow.get("on", workflow.get(True))
    assert isinstance(trigger, dict)
    return trigger


def _steps(workflow: dict) -> list[dict]:
    steps = workflow["jobs"]["validate-release-contract"]["steps"]
    assert isinstance(steps, list)
    assert all(isinstance(step, dict) and isinstance(step.get("name"), str) for step in steps)
    return steps


def _step(workflow: dict, name: str) -> dict:
    matches = [step for step in _steps(workflow) if step["name"] == name]
    assert len(matches) == 1, f"expected exactly one workflow step named {name!r}"
    return matches[0]


def _step_text(step: dict) -> str:
    return str(step.get("run", ""))


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
        "SENTINEL_DNA_SECRET_KEY": TEST_SECRET,
        "POSTGRES_PASSWORD": TEST_POSTGRES_PASSWORD,
        "SENTINEL_DNA_IMAGE_DIGEST": digest,
        "SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE": str(manifest),
    }
    assert validate_configuration(environ=environment, repository_root=ROOT) == []


def test_controlled_production_validation_requires_postgresql_url():
    metadata = derive_release_metadata(repository_root=ROOT, source_date_epoch="0")
    environment = {
        **metadata,
        "SENTINEL_DNA_ENV": "production",
        "SENTINEL_DNA_SECURE_COOKIES": "1",
        "SENTINEL_DNA_SECRET_KEY": TEST_SECRET,
        "POSTGRES_PASSWORD": TEST_POSTGRES_PASSWORD,
    }

    errors = validate_configuration(
        environ=environment,
        repository_root=ROOT,
        require_postgresql=True,
    )

    assert "DATABASE_URL:missing" in errors


def test_deployment_validation_rejects_missing_trusted_release_artifact(tmp_path):
    metadata = derive_release_metadata(repository_root=ROOT, source_date_epoch="0")
    environment = {
        **metadata,
        "SENTINEL_DNA_ENV": "production",
        "SENTINEL_DNA_SECURE_COOKIES": "1",
        "SENTINEL_DNA_SECRET_KEY": TEST_SECRET,
        "POSTGRES_PASSWORD": TEST_POSTGRES_PASSWORD,
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


def test_compose_build_contract_uses_full_candidate_revision():
    compose = (ROOT / "deployment" / "docker-compose.yml").read_text(encoding="utf-8")
    assert compose.count("VCS_REF: ${SENTINEL_DNA_IMAGE_REVISION_FULL:?set SENTINEL_DNA_IMAGE_REVISION_FULL}") == 2
    assert "VCS_REF: ${SENTINEL_DNA_IMAGE_REVISION:?set SENTINEL_DNA_IMAGE_REVISION}" not in compose


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
    workflow = _workflow()
    assert workflow["name"] == "deployment-contract"
    trigger = _trigger(workflow)
    dispatch = trigger["workflow_dispatch"]
    assert set(dispatch["inputs"]) == {"authorized_ref", "authorized_sha", "authorized_tree"}
    assert all(dispatch["inputs"][name]["required"] for name in dispatch["inputs"])
    assert all(dispatch["inputs"][name]["type"] == "string" for name in dispatch["inputs"])

    assert workflow["permissions"] == {"contents": "read", "packages": "write"}
    assert workflow["concurrency"] == {
        "group": "deployment-contract-${{ inputs.authorized_sha }}",
        "cancel-in-progress": False,
    }
    job = workflow["jobs"]["validate-release-contract"]
    assert job["environment"] == "production"
    assert not {"SENTINEL_DNA_SECRET_KEY", "POSTGRES_PASSWORD"}.intersection(job.get("env", {}))
    assert job["env"]["SENTINEL_DNA_AUTHORIZED_RELEASE_REF"] == "feature/controlled-production-deployment-adapter"
    assert job["env"]["SENTINEL_DNA_AUTHORIZED_RELEASE_SHA"] == "${{ vars.SENTINEL_DNA_AUTHORIZED_RELEASE_SHA }}"
    assert job["env"]["SENTINEL_DNA_AUTHORIZED_RELEASE_TREE"] == "${{ vars.SENTINEL_DNA_AUTHORIZED_RELEASE_TREE }}"

    checkout = _step(workflow, "Checkout authorized workflow commit")
    assert checkout["with"] == {"ref": "${{ inputs.authorized_sha }}", "fetch-depth": 0}
    verify = _step(workflow, "Verify authorized candidate identity")
    assert {"REQUESTED_RELEASE_REF", "REQUESTED_RELEASE_SHA", "REQUESTED_RELEASE_TREE"}.issubset(verify["env"])
    verify_text = _step_text(verify)
    assert 'test "$GITHUB_SHA" = "$SENTINEL_DNA_AUTHORIZED_RELEASE_SHA"' in verify_text
    assert "git rev-parse HEAD" in verify_text
    assert "HEAD^{tree}" in verify_text
    assert "git status --porcelain --untracked-files=all" in verify_text

    names = [step["name"] for step in _steps(workflow)]
    assert names.index("Build immutable application image") < names.index("Publish immutable candidate image to private GHCR")
    assert names.index("Publish immutable candidate image to private GHCR") < names.index("Prepare candidate-bound trusted release metadata")
    assert names.index("Prepare candidate-bound trusted release metadata") < names.index("Validate protected configuration and metadata")
    assert names.index("Validate protected configuration and metadata") < names.index("Generate image-bound release manifest")
    assert names.index("Verify image-bound release manifest") < names.index("Upload non-secret image release evidence")

    login = _step(workflow, "Authenticate to private GHCR")
    assert "github.token" in _step_text(login)
    assert "--password-stdin" in _step_text(login)
    publish = _step(workflow, "Publish immutable candidate image to private GHCR")
    publish_text = _step_text(publish)
    assert "ghcr.io/uwakwechukwuebukapaul-ai/sentinel-dna" in publish_text
    assert 'sha-${SENTINEL_DNA_IMAGE_REVISION_FULL}' in publish_text
    assert "docker push" in publish_text
    assert "REPO_DIGESTS_JSON" in publish_text
    assert "exactly one matching GHCR RepoDigest" in publish_text
    collision = _step(workflow, "Refuse an existing candidate tag")
    collision_text = _step_text(collision)
    assert "docker manifest inspect" in collision_text
    assert "refusing to overwrite" in collision_text

    for step in _steps(workflow):
        text = _step_text(step)
        assert "controlled_deploy.py --execute" not in text
        assert "docker compose up" not in text
        assert ":latest" not in text.lower()
    for name in (
        "Checkout authorized workflow commit",
        "Verify authorized candidate identity",
        "Derive immutable release metadata",
        "Build immutable application image",
        "Verify image provenance and non-root configuration",
        "Verify OCI creation metadata",
        "Run deployment-adjacent regression tests",
        "Authenticate to private GHCR",
        "Publish immutable candidate image to private GHCR",
    ):
        assert not {"SENTINEL_DNA_SECRET_KEY", "POSTGRES_PASSWORD"}.intersection(_step(workflow, name).get("env", {}))

    for name in ("Validate protected configuration and metadata", "Validate deployment Compose contract"):
        assert {"SENTINEL_DNA_SECRET_KEY", "POSTGRES_PASSWORD"}.issubset(_step(workflow, name)["env"])

    metadata = _step(workflow, "Prepare candidate-bound trusted release metadata")
    assert "prepare_trusted_release_metadata.py" in _step_text(metadata)
    assert "PUBLISHED_IMAGE_DIGEST" in _step_text(metadata)
    assert "SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE" in _step_text(metadata)
    manifest = _step(workflow, "Generate image-bound release manifest")
    assert "PUBLISHED_IMAGE_DIGEST" in _step_text(manifest)
    assert "PUBLISHED_IMAGE_ID" in _step_text(manifest)
    assert "SENTINEL_DNA_IMAGE_CREATED" in _step_text(manifest)
    verify_manifest = _step(workflow, "Verify image-bound release manifest")
    assert "--require-image" in _step_text(verify_manifest)
    upload = _step(workflow, "Upload non-secret image release evidence")
    assert "sentinel-dna-image-provenance.json" in upload["with"]["path"]
    assert "sentinel-dna-release-manifest-image-bound.json" in upload["with"]["path"]


def test_workflow_is_valid_yaml_and_has_unique_named_steps():
    workflow = _workflow()
    assert isinstance(workflow["jobs"], dict)
    names = [step["name"] for step in _steps(workflow)]
    assert len(names) == len(set(names))


def test_workflow_does_not_expose_production_secrets_to_build_or_test_steps():
    workflow = _workflow()
    secret_names = {"SENTINEL_DNA_SECRET_KEY", "POSTGRES_PASSWORD"}
    for step in _steps(workflow):
        if step["name"] not in {"Validate protected configuration and metadata", "Validate deployment Compose contract"}:
            assert not secret_names.intersection(step.get("env", {}))
