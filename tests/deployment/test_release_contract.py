import re
import subprocess
from pathlib import Path

import pytest
import yaml

from deployment.scripts.release_metadata import derive_release_metadata, format_metadata
from deployment.scripts.validate_deployment_config import validate_configuration
from tests.credential_helpers import random_password, random_secret


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "deployment-contract.yml"
TEST_SECRET = random_secret()
TEST_POSTGRES_PASSWORD = random_password()
HEX40 = re.compile(r"^[0-9a-f]{40}$")
REF_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


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


class ReleaseContractViolation(ValueError):
    pass


def _valid_protected_identity() -> dict[str, str]:
    return {
        "workflow_ref": "release-gate/trust-premium-af00b71",
        "workflow_sha": "a" * 40,
        "release_ref": "feature/sentinel-dna-premium-product-expansion",
        "release_sha": "b" * 40,
        "release_tree": "c" * 40,
        "baseline_sha": "d" * 40,
    }


def _valid_assertions(protected: dict[str, str]) -> dict[str, str]:
    return {
        "authorized_ref": protected["release_ref"],
        "authorized_sha": protected["release_sha"],
        "authorized_tree": protected["release_tree"],
    }


def _valid_ref(value: str) -> bool:
    if not REF_PATTERN.fullmatch(value):
        return False
    return subprocess.run(
        ["git", "check-ref-format", "--branch", value],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).returncode == 0


def _evaluate_identity_contract(
    protected: dict[str, str],
    assertions: dict[str, str],
    *,
    github_ref: str,
    github_sha: str,
    checkout_sha: str,
    checkout_tree: str,
    baseline_is_ancestor: bool,
) -> str:
    """Executable fixture mirroring the workflow's fail-closed assertions."""
    for field in ("workflow_sha", "release_sha", "release_tree", "baseline_sha"):
        if not HEX40.fullmatch(protected[field]):
            raise ReleaseContractViolation(f"invalid protected {field}")
    for field in ("workflow_ref", "release_ref"):
        if not _valid_ref(protected[field]):
            raise ReleaseContractViolation(f"invalid protected {field}")
    if github_ref != f"refs/heads/{protected['workflow_ref']}":
        raise ReleaseContractViolation("workflow ref mismatch")
    if github_sha != protected["workflow_sha"]:
        raise ReleaseContractViolation("workflow SHA mismatch")
    if assertions != _valid_assertions(protected):
        raise ReleaseContractViolation("candidate assertion mismatch")
    if checkout_sha != protected["release_sha"]:
        raise ReleaseContractViolation("checkout SHA mismatch")
    if checkout_tree != protected["release_tree"]:
        raise ReleaseContractViolation("checkout tree mismatch")
    if not baseline_is_ancestor:
        raise ReleaseContractViolation("baseline ancestry mismatch")
    return protected["release_sha"]


def _checkout_authority(protected: dict[str, str], _assertions: dict[str, str]) -> str:
    """The checkout target is protected identity, never a dispatch assertion."""
    return protected["release_sha"]


def _evaluate_valid_contract(**overrides: object) -> str:
    protected = _valid_protected_identity()
    assertions = _valid_assertions(protected)
    values = {
        "github_ref": f"refs/heads/{protected['workflow_ref']}",
        "github_sha": protected["workflow_sha"],
        "checkout_sha": protected["release_sha"],
        "checkout_tree": protected["release_tree"],
        "baseline_is_ancestor": True,
    }
    values.update(overrides)
    return _evaluate_identity_contract(protected, assertions, **values)


def test_executable_identity_fixture_accepts_protected_candidate():
    protected = _valid_protected_identity()
    assertions = _valid_assertions(protected)

    assert _evaluate_identity_contract(
        protected,
        assertions,
        github_ref=f"refs/heads/{protected['workflow_ref']}",
        github_sha=protected["workflow_sha"],
        checkout_sha=protected["release_sha"],
        checkout_tree=protected["release_tree"],
        baseline_is_ancestor=True,
    ) == protected["release_sha"]


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("release_sha", "not-a-sha"),
        ("release_tree", "f" * 39),
        ("baseline_sha", ""),
        ("release_ref", ""),
        ("release_ref", "feature/invalid ref"),
        ("workflow_sha", "G" * 40),
        ("workflow_ref", "release gate"),
    ),
)
def test_invalid_protected_identity_fails_closed(field: str, value: str):
    protected = _valid_protected_identity()
    protected[field] = value

    with pytest.raises(ReleaseContractViolation):
        _evaluate_identity_contract(
            protected,
            _valid_assertions(protected),
            github_ref=f"refs/heads/{protected['workflow_ref']}",
            github_sha=protected["workflow_sha"],
            checkout_sha=protected["release_sha"],
            checkout_tree=protected["release_tree"],
            baseline_is_ancestor=True,
        )


@pytest.mark.parametrize(
    ("github_ref", "github_sha"),
    (
        ("refs/heads/other-workflow", "a" * 40),
        ("refs/heads/release-gate/trust-premium-af00b71", "b" * 40),
    ),
)
def test_workflow_identity_mismatch_fails_closed(github_ref: str, github_sha: str):
    with pytest.raises(ReleaseContractViolation):
        _evaluate_valid_contract(github_ref=github_ref, github_sha=github_sha)


def test_candidate_assertion_mismatch_fails_closed():
    protected = _valid_protected_identity()
    assertions = _valid_assertions(protected)
    assertions["authorized_tree"] = "e" * 40

    with pytest.raises(ReleaseContractViolation):
        _evaluate_identity_contract(
            protected,
            assertions,
            github_ref=f"refs/heads/{protected['workflow_ref']}",
            github_sha=protected["workflow_sha"],
            checkout_sha=protected["release_sha"],
            checkout_tree=protected["release_tree"],
            baseline_is_ancestor=True,
        )


def test_baseline_ancestry_failure_fails_closed():
    with pytest.raises(ReleaseContractViolation):
        _evaluate_valid_contract(baseline_is_ancestor=False)


def test_alternate_dispatch_sha_cannot_become_checkout_authority():
    protected = _valid_protected_identity()
    assertions = _valid_assertions(protected)
    assertions["authorized_sha"] = "e" * 40

    assert _checkout_authority(protected, assertions) == protected["release_sha"]
    with pytest.raises(ReleaseContractViolation):
        _evaluate_identity_contract(
            protected,
            assertions,
            github_ref=f"refs/heads/{protected['workflow_ref']}",
            github_sha=protected["workflow_sha"],
            checkout_sha=protected["release_sha"],
            checkout_tree=protected["release_tree"],
            baseline_is_ancestor=True,
        )


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
        "group": "deployment-contract-${{ vars.SENTINEL_DNA_AUTHORIZED_RELEASE_SHA }}",
        "cancel-in-progress": False,
    }
    job = workflow["jobs"]["validate-release-contract"]
    assert job["environment"] == "production"
    assert not {"SENTINEL_DNA_SECRET_KEY", "POSTGRES_PASSWORD"}.intersection(job.get("env", {}))
    assert job["env"]["SENTINEL_DNA_AUTHORIZED_WORKFLOW_REF"] == "${{ vars.SENTINEL_DNA_AUTHORIZED_WORKFLOW_REF }}"
    assert job["env"]["SENTINEL_DNA_AUTHORIZED_WORKFLOW_SHA"] == "${{ vars.SENTINEL_DNA_AUTHORIZED_WORKFLOW_SHA }}"
    assert job["env"]["SENTINEL_DNA_AUTHORIZED_RELEASE_REF"] == "${{ vars.SENTINEL_DNA_AUTHORIZED_RELEASE_REF }}"
    assert job["env"]["SENTINEL_DNA_AUTHORIZED_RELEASE_SHA"] == "${{ vars.SENTINEL_DNA_AUTHORIZED_RELEASE_SHA }}"
    assert job["env"]["SENTINEL_DNA_AUTHORIZED_RELEASE_TREE"] == "${{ vars.SENTINEL_DNA_AUTHORIZED_RELEASE_TREE }}"
    assert job["env"]["SENTINEL_DNA_AUTHORIZED_BASELINE_SHA"] == "${{ vars.SENTINEL_DNA_AUTHORIZED_BASELINE_SHA }}"

    workflow_identity = _step(workflow, "Verify protected workflow identity")
    workflow_identity_text = _step_text(workflow_identity)
    assert 'test "$GITHUB_REF" = "refs/heads/$SENTINEL_DNA_AUTHORIZED_WORKFLOW_REF"' in workflow_identity_text
    assert 'test "$GITHUB_SHA" = "$SENTINEL_DNA_AUTHORIZED_WORKFLOW_SHA"' in workflow_identity_text

    precheck = _step(workflow, "Validate protected release identity before checkout")
    precheck_text = _step_text(precheck)
    names = [step["name"] for step in _steps(workflow)]
    assert names.index(precheck["name"]) < names.index("Checkout protected candidate commit")
    assert "git check-ref-format --branch" in precheck_text
    for variable in (
        "SENTINEL_DNA_AUTHORIZED_WORKFLOW_SHA",
        "SENTINEL_DNA_AUTHORIZED_RELEASE_SHA",
        "SENTINEL_DNA_AUTHORIZED_RELEASE_TREE",
        "SENTINEL_DNA_AUTHORIZED_BASELINE_SHA",
    ):
        assert f"[[ \"${variable}\" =~ ^[0-9a-f]{{40}}$ ]]" in precheck_text

    checkout = _step(workflow, "Checkout protected candidate commit")
    assert checkout["with"] == {
        "ref": "${{ vars.SENTINEL_DNA_AUTHORIZED_RELEASE_SHA }}",
        "fetch-depth": 0,
    }
    verify = _step(workflow, "Verify protected candidate identity")
    assert {"REQUESTED_RELEASE_REF", "REQUESTED_RELEASE_SHA", "REQUESTED_RELEASE_TREE"}.issubset(verify["env"])
    verify_text = _step_text(verify)
    assert 'test "$REQUESTED_RELEASE_REF" = "$SENTINEL_DNA_AUTHORIZED_RELEASE_REF"' in verify_text
    assert 'test "$REQUESTED_RELEASE_SHA" = "$SENTINEL_DNA_AUTHORIZED_RELEASE_SHA"' in verify_text
    assert 'test "$REQUESTED_RELEASE_TREE" = "$SENTINEL_DNA_AUTHORIZED_RELEASE_TREE"' in verify_text
    assert "git rev-parse HEAD" in verify_text
    assert "HEAD^{tree}" in verify_text
    assert 'git cat-file -e "${SENTINEL_DNA_AUTHORIZED_BASELINE_SHA}^{commit}"' in verify_text
    assert "git merge-base --is-ancestor" in verify_text
    assert "git status --porcelain --untracked-files=all" in verify_text
    assert 'test "$GITHUB_SHA" = "$SENTINEL_DNA_AUTHORIZED_RELEASE_SHA"' not in verify_text

    assert "${{ inputs.authorized_sha }}" not in checkout["with"]["ref"]
    assert "${{ inputs.authorized_sha }}" not in workflow["concurrency"]["group"]

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
        "Verify protected workflow identity",
        "Checkout protected candidate commit",
        "Verify protected candidate identity",
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


def test_dispatch_values_are_assertions_and_cannot_select_release_artifacts():
    workflow = _workflow()
    trigger = _trigger(workflow)
    dispatch = trigger["workflow_dispatch"]
    assert set(dispatch["inputs"]) == {"authorized_ref", "authorized_sha", "authorized_tree"}

    job = workflow["jobs"]["validate-release-contract"]
    checkout = _step(workflow, "Checkout protected candidate commit")
    verify = _step(workflow, "Verify protected candidate identity")

    assert checkout["with"]["ref"] == "${{ vars.SENTINEL_DNA_AUTHORIZED_RELEASE_SHA }}"
    assert "inputs." not in checkout["with"]["ref"]
    assert "inputs." not in workflow["concurrency"]["group"]
    assert "inputs." not in _step(workflow, "Upload non-secret image release evidence")["with"]["name"]
    assert set(verify["env"]) == {
        "REQUESTED_RELEASE_REF",
        "REQUESTED_RELEASE_SHA",
        "REQUESTED_RELEASE_TREE",
    }

    verify_text = _step_text(verify)
    for assertion in (
        'test "$REQUESTED_RELEASE_REF" = "$SENTINEL_DNA_AUTHORIZED_RELEASE_REF"',
        'test "$REQUESTED_RELEASE_SHA" = "$SENTINEL_DNA_AUTHORIZED_RELEASE_SHA"',
        'test "$REQUESTED_RELEASE_TREE" = "$SENTINEL_DNA_AUTHORIZED_RELEASE_TREE"',
    ):
        assert assertion in verify_text

    assert job["env"]["SENTINEL_DNA_AUTHORIZED_RELEASE_SHA"] != "${{ inputs.authorized_sha }}"
