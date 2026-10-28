import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from deployment.scripts.release_metadata import derive_release_metadata, format_metadata
from deployment.scripts.validate_deployment_config import main, validate_configuration
from tests.credential_helpers import random_password, random_secret


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "deployment-contract.yml"
TEST_SECRET = random_secret()
TEST_POSTGRES_PASSWORD = random_password()
HEX40 = re.compile(r"^[0-9a-f]{40}$")
REF_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


class _UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        seen = set()
        seen_merge_key = False
        for key_node, _value_node in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                if seen_merge_key:
                    raise yaml.constructor.ConstructorError(
                        "while constructing a mapping",
                        node.start_mark,
                        "found duplicate key '<<'",
                        key_node.start_mark,
                    )
                seen_merge_key = True
                continue

            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in seen
                seen.add(key)
            except TypeError as error:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found an unhashable mapping key",
                    key_node.start_mark,
                ) from error
            if duplicate:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )

        return super().construct_mapping(node, deep=deep)


def _strict_yaml_load(source: str):
    return yaml.load(source, Loader=_UniqueKeyLoader)


def _workflow() -> dict:
    parsed = _strict_yaml_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def test_workflow_yaml_loader_rejects_duplicate_top_level_keys():
    with pytest.raises(yaml.constructor.ConstructorError, match="duplicate key"):
        _strict_yaml_load("name: first\nname: second\n")


def test_workflow_yaml_loader_rejects_duplicate_nested_keys():
    with pytest.raises(yaml.constructor.ConstructorError, match="duplicate key"):
        _strict_yaml_load("jobs:\n  blocked:\n    runs-on: ubuntu-latest\n    runs-on: windows-latest\n")


def _trigger(workflow: dict) -> dict:
    # PyYAML YAML 1.1 resolves the GitHub Actions `on` key as True.
    trigger = workflow.get("on", workflow.get(True))
    assert isinstance(trigger, dict)
    return trigger


def _assert_blocked_workflow_structure(workflow: dict) -> None:
    assert set(workflow) == {"name", True, "permissions", "jobs"}
    assert workflow["name"] == "deployment-contract-blocked"
    assert _trigger(workflow) == {"workflow_dispatch": None}
    assert workflow["permissions"] == {}
    assert "env" not in workflow
    assert set(workflow["jobs"]) == {"blocked"}

    job = workflow["jobs"]["blocked"]
    assert set(job) == {"name", "runs-on", "steps"}
    assert job["name"] == "Fail closed — independent release trust root unavailable"
    assert job["runs-on"] == "ubuntu-latest"
    assert "env" not in job
    assert len(job["steps"]) == 1

    step = job["steps"][0]
    assert set(step) == {"name", "shell", "run"}
    assert step["name"] == "Refuse all release and publication activity"
    assert step["shell"] == "bash"
    assert "env" not in step
    assert step["run"] == (
        'echo "::error title=Release blocked::This repository workflow has no '
        "independent trust root or release authorization.\"\n"
        "exit 1\n"
    )

    def assert_no_secret_references(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                assert_no_secret_references(key)
                assert_no_secret_references(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                assert_no_secret_references(item)
        elif isinstance(value, str):
            assert not re.search(r"\$\{\{\s*secrets(?:\.|\[|\s)", value, re.IGNORECASE)

    assert_no_secret_references(workflow)


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
    github_workflow_ref: str,
    github_workflow_sha: str,
    executed_workflow_blob: str,
    authorized_workflow_blob: str,
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
    if not HEX40.fullmatch(github_workflow_sha):
        raise ReleaseContractViolation("workflow definition SHA malformed")
    expected_workflow_ref = (
        f"sentinel/example/.github/workflows/deployment-contract.yml@"
        f"refs/heads/{protected['workflow_ref']}"
    )
    if github_workflow_ref != expected_workflow_ref:
        raise ReleaseContractViolation("workflow definition ref mismatch")
    if not HEX40.fullmatch(executed_workflow_blob):
        raise ReleaseContractViolation("executed workflow blob malformed")
    if not HEX40.fullmatch(authorized_workflow_blob):
        raise ReleaseContractViolation("authorized workflow blob malformed")
    if executed_workflow_blob != authorized_workflow_blob:
        raise ReleaseContractViolation("workflow file identity mismatch")
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


def _evaluate_valid_contract(
    *, protected: dict[str, str] | None = None, **overrides: object
) -> str:
    protected = protected or _valid_protected_identity()
    assertions = _valid_assertions(protected)
    values = {
        "github_ref": f"refs/heads/{protected['workflow_ref']}",
        "github_sha": "e" * 40,
        "github_workflow_ref": (
            "sentinel/example/.github/workflows/deployment-contract.yml@"
            f"refs/heads/{protected['workflow_ref']}"
        ),
        "github_workflow_sha": "f" * 40,
        "executed_workflow_blob": "1" * 40,
        "authorized_workflow_blob": "1" * 40,
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
        github_sha="e" * 40,
        github_workflow_ref=(
            "sentinel/example/.github/workflows/deployment-contract.yml@"
            f"refs/heads/{protected['workflow_ref']}"
        ),
        github_workflow_sha="f" * 40,
        executed_workflow_blob="1" * 40,
        authorized_workflow_blob="1" * 40,
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
            github_sha="e" * 40,
            github_workflow_ref=(
                "sentinel/example/.github/workflows/deployment-contract.yml@"
                f"refs/heads/{protected['workflow_ref']}"
            ),
            github_workflow_sha="f" * 40,
            executed_workflow_blob="1" * 40,
            authorized_workflow_blob="1" * 40,
            checkout_sha=protected["release_sha"],
            checkout_tree=protected["release_tree"],
            baseline_is_ancestor=True,
        )


@pytest.mark.parametrize(
    ("github_ref", "github_workflow_ref"),
    (
        ("refs/heads/other-workflow", "unused"),
        ("unused", "sentinel/example/.github/workflows/deployment-contract.yml@refs/heads/other-workflow"),
    ),
)
def test_workflow_identity_mismatch_fails_closed(github_ref: str, github_workflow_ref: str):
    with pytest.raises(ReleaseContractViolation):
        _evaluate_valid_contract(github_ref=github_ref, github_workflow_ref=github_workflow_ref)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("github_workflow_sha", ""),
        ("github_workflow_sha", "G" * 40),
        ("executed_workflow_blob", "not-a-blob"),
        ("authorized_workflow_blob", "2" * 39),
    ),
)
def test_workflow_definition_identity_missing_or_malformed_fails_closed(field: str, value: str):
    with pytest.raises(ReleaseContractViolation):
        _evaluate_valid_contract(**{field: value})


def test_unauthorized_workflow_definition_fails_closed():
    with pytest.raises(ReleaseContractViolation):
        _evaluate_valid_contract(executed_workflow_blob="2" * 40)


def test_newer_release_commit_does_not_change_trusted_workflow_identity():
    assert _evaluate_valid_contract(github_sha="9" * 40) == "b" * 40


def test_release_sha_cannot_satisfy_workflow_definition_identity():
    protected = _valid_protected_identity()
    protected["release_sha"] = protected["workflow_sha"]
    with pytest.raises(ReleaseContractViolation):
        _evaluate_valid_contract(
            protected=protected,
            executed_workflow_blob="2" * 40,
            authorized_workflow_blob="1" * 40,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("checkout_sha", "9" * 40),
        ("checkout_tree", "8" * 40),
    ),
)
def test_release_checkout_identity_remains_independent_and_fail_closed(field: str, value: str):
    with pytest.raises(ReleaseContractViolation):
        _evaluate_valid_contract(**{field: value})


def test_candidate_assertion_mismatch_fails_closed():
    protected = _valid_protected_identity()
    assertions = _valid_assertions(protected)
    assertions["authorized_tree"] = "e" * 40

    with pytest.raises(ReleaseContractViolation):
        _evaluate_identity_contract(
            protected,
            assertions,
            github_ref=f"refs/heads/{protected['workflow_ref']}",
            github_sha="e" * 40,
            github_workflow_ref=(
                "sentinel/example/.github/workflows/deployment-contract.yml@"
                f"refs/heads/{protected['workflow_ref']}"
            ),
            github_workflow_sha="f" * 40,
            executed_workflow_blob="1" * 40,
            authorized_workflow_blob="1" * 40,
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
            github_sha="e" * 40,
            github_workflow_ref=(
                "sentinel/example/.github/workflows/deployment-contract.yml@"
                f"refs/heads/{protected['workflow_ref']}"
            ),
            github_workflow_sha="f" * 40,
            executed_workflow_blob="1" * 40,
            authorized_workflow_blob="1" * 40,
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
        "SENTINEL_DNA_DB_PATH": "/tmp/sentinel.sqlite",
    }

    errors = validate_configuration(
        environ=environment,
        repository_root=ROOT,
        require_postgresql=True,
    )

    assert "DATABASE_URL:missing" in errors


@pytest.mark.parametrize("database_url", ["sqlite:///tmp/sentinel.sqlite", "not-a-url", "postgresql://[invalid"])
def test_controlled_production_validation_rejects_invalid_database_urls(database_url):
    metadata = derive_release_metadata(repository_root=ROOT, source_date_epoch="0")
    environment = {
        **metadata,
        "SENTINEL_DNA_ENV": "production",
        "SENTINEL_DNA_SECURE_COOKIES": "1",
        "SENTINEL_DNA_SECRET_KEY": TEST_SECRET,
        "POSTGRES_PASSWORD": TEST_POSTGRES_PASSWORD,
        "SENTINEL_DNA_DB_PATH": "/tmp/sentinel.sqlite",
        "DATABASE_URL": database_url,
    }

    errors = validate_configuration(environ=environment, repository_root=ROOT, require_postgresql=True)

    assert "DATABASE_URL:invalid-postgresql-url" in errors


def test_controlled_production_validation_accepts_postgresql_url(tmp_path):
    metadata = derive_release_metadata(repository_root=ROOT, source_date_epoch="0")
    digest = "sha256:" + "b" * 64
    trusted = tmp_path / "trusted-metadata.json"
    trusted.write_text(
        '{"release_sha":"' + metadata["SENTINEL_DNA_IMAGE_REVISION_FULL"] + '","image_digest":"' + digest + '"}\n',
        encoding="utf-8",
    )
    trusted.chmod(0o444)
    environment = {
        **metadata,
        "SENTINEL_DNA_ENV": "production",
        "SENTINEL_DNA_SECURE_COOKIES": "1",
        "SENTINEL_DNA_SECRET_KEY": TEST_SECRET,
        "POSTGRES_PASSWORD": TEST_POSTGRES_PASSWORD,
        "DATABASE_URL": "postgresql://sentinel@postgres:5432/sentinel_dna",
        "SENTINEL_DNA_IMAGE_DIGEST": digest,
        "SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE": str(trusted),
    }

    assert validate_configuration(environ=environment, repository_root=ROOT, require_postgresql=True) == []


def test_normal_validator_cli_requires_postgresql_url(monkeypatch, tmp_path, capsys):
    metadata = derive_release_metadata(repository_root=ROOT, source_date_epoch="0")
    digest = "sha256:" + "a" * 64
    trusted = tmp_path / "trusted-metadata.json"
    trusted.write_text(
        '{"release_sha":"' + metadata["SENTINEL_DNA_IMAGE_REVISION_FULL"] + '","image_digest":"' + digest + '"}\n',
        encoding="utf-8",
    )
    trusted.chmod(0o444)
    environment = {
        **metadata,
        "SENTINEL_DNA_ENV": "production",
        "SENTINEL_DNA_SECURE_COOKIES": "1",
        "SENTINEL_DNA_SECRET_KEY": TEST_SECRET,
        "POSTGRES_PASSWORD": TEST_POSTGRES_PASSWORD,
        "SENTINEL_DNA_DB_PATH": str(tmp_path / "soc.db"),
        "SENTINEL_DNA_IMAGE_DIGEST": digest,
        "SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE": str(trusted),
    }
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(sys, "argv", ["validate_deployment_config.py"])

    assert main() == 1
    assert "DATABASE_URL:missing" in capsys.readouterr().out


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
    nginx_service = yaml.safe_load(compose)["services"]["nginx"]
    tls_mount = next(
        volume
        for volume in nginx_service["volumes"]
        if isinstance(volume, dict) and volume.get("target") == "/etc/nginx/tls"
    )

    assert "env_file:" not in compose
    assert "5000:5000" not in compose
    assert 'ports: ["80:80", "443:443"]' in compose
    assert "SENTINEL_DNA_TLS_DIR:?set SENTINEL_DNA_TLS_DIR" in compose
    assert "target: /etc/nginx/tls" in compose
    assert tls_mount == {
        "type": "bind",
        "source": "${SENTINEL_DNA_TLS_DIR:?set SENTINEL_DNA_TLS_DIR}",
        "target": "/etc/nginx/tls",
        "read_only": True,
    }
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


def test_blocked_workflow_does_not_reference_compose_tls_override_or_publication():
    workflow = _workflow()
    _assert_blocked_workflow_structure(workflow)
    assert workflow["permissions"] == {}
    assert set(workflow["jobs"]) == {"blocked"}
    text = repr(workflow).lower()
    assert "docker compose up" not in text
    assert "docker push" not in text
    assert "sentinel-dna-compose-validation.override.yml" not in text

def test_blocked_workflow_cannot_publish_ghcr_artifacts():
    workflow = _workflow()
    _assert_blocked_workflow_structure(workflow)
    assert workflow["name"] == "deployment-contract-blocked"
    assert workflow["permissions"] == {}
    assert set(workflow["jobs"]) == {"blocked"}
    job = workflow["jobs"]["blocked"]
    assert job.get("environment") is None
    assert job.get("services") is None
    assert job.get("env") is None
    steps = job["steps"]
    assert len(steps) == 1
    assert steps[0]["name"] == "Refuse all release and publication activity"
    run = steps[0]["run"]
    assert "Release blocked" in run
    assert "exit 1" in run
    assert "uses" not in steps[0]

def test_workflow_is_valid_yaml_and_has_unique_named_steps():
    workflow = _workflow()
    assert workflow["name"] == "deployment-contract-blocked"
    assert isinstance(workflow["jobs"], dict)
    assert set(workflow["jobs"]) == {"blocked"}
    for job in workflow["jobs"].values():
        names = [step["name"] for step in job.get("steps", [])]
        assert len(names) == len(set(names))

def test_blocked_workflow_does_not_expose_production_secrets():
    workflow = _workflow()
    _assert_blocked_workflow_structure(workflow)
    secret_names = {"SENTINEL_DNA_SECRET_KEY", "POSTGRES_PASSWORD"}
    assert workflow["permissions"] == {}
    for job in workflow["jobs"].values():
        assert not secret_names.intersection(job.get("env", {}))
        for step in job.get("steps", []):
            assert not secret_names.intersection(step.get("env", {}))
            assert "uses" not in step

def test_blocked_workflow_has_no_test_job_or_database_service():
    workflow = _workflow()
    _assert_blocked_workflow_structure(workflow)
    assert set(workflow["jobs"]) == {"blocked"}
    job = workflow["jobs"]["blocked"]
    assert "services" not in job
    assert all(
        "pytest" not in str(step.get("run", "")).lower()
        for step in job.get("steps", [])
    )
    # The blocker must not launch services or run candidate tests.
    assert len(job["steps"]) == 1
    assert "exit 1" in job["steps"][0]["run"]

def test_blocked_workflow_dispatch_cannot_select_release_artifacts():
    workflow = _workflow()
    _assert_blocked_workflow_structure(workflow)
    trigger = _trigger(workflow)
    assert set(trigger) == {"workflow_dispatch"}
    assert trigger["workflow_dispatch"] is None
    assert workflow["permissions"] == {}
    assert set(workflow["jobs"]) == {"blocked"}
    text = repr(workflow)
    assert "authorized_sha" not in text
    assert "authorized_ref" not in text
    assert "authorized_tree" not in text

def test_deployment_validator_direct_cli_resolves_repository_packages():
    result = subprocess.run(
        [sys.executable, str(ROOT / "deployment" / "scripts" / "validate_deployment_config.py"), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()
    assert "ModuleNotFoundError" not in result.stderr
