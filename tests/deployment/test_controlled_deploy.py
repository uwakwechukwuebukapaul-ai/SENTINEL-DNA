import runpy
import json
import os
from pathlib import Path
import subprocess
import sys
import types

import pytest
from tests.credential_helpers import random_password, random_secret

import deployment.scripts.controlled_deploy as controlled_deploy
from deployment.scripts.controlled_deploy import (
    AclEntry,
    CommandResult,
    ControlledDeploymentAdapter,
    ControlledDeploymentError,
    ReleaseEvidence,
    build_parser,
    parse_icacls_output,
    validate_acl,
    validate_compose_file,
    validate_protected_file,
)
from deployment.scripts.release_metadata import derive_release_metadata
from deployment.scripts.release_manifest import build_manifest, write_manifest


RELEASE_METADATA = derive_release_metadata(
    repository_root=Path(__file__).resolve().parents[2],
    source_date_epoch="0",
)
RELEASE_SHA = RELEASE_METADATA["SENTINEL_DNA_IMAGE_REVISION_FULL"]
RELEASE_REVISION = RELEASE_METADATA["SENTINEL_DNA_IMAGE_REVISION"]
RELEASE_CREATED = RELEASE_METADATA["SENTINEL_DNA_IMAGE_CREATED"]
RELEASE_DIGEST = "sha256:9a212a06eed455a43675c75cf1324827b33bc44070c6f0ccd7d5f9df0be4b91d"
SOURCE = "https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA"


SAFE_ENTRIES = (
    AclEntry("BUILTIN\\Users", "ALLOW", "RX"),
    AclEntry("BUILTIN\\Administrators", "ALLOW", "F"),
    AclEntry("NT AUTHORITY\\SYSTEM", "ALLOW", "F"),
)


class FakeAclInspector:
    def __init__(self, entries=SAFE_ENTRIES):
        self.entries = entries

    def inspect(self, path):
        return self.entries


class FakeRunner:
    def __init__(self, image_info, compose_info, *, docker_error=False):
        self.image_info = image_info
        self.compose_info = compose_info
        self.docker_error = docker_error
        self.calls = []

    def run(self, args, *, cwd=None, env=None):
        self.calls.append(tuple(args))
        self.last_env = env
        if self.docker_error:
            return CommandResult(1, "", "production-secret-must-not-escape")
        args = tuple(args)
        if "image" in args and "inspect" in args:
            return CommandResult(0, json.dumps([self.image_info]), "")
        if "compose" in args and "config" in args:
            return CommandResult(0, json.dumps(self.compose_info), "")
        if "compose" in args and "up" in args:
            compose_files = [index + 1 for index, value in enumerate(args) if value == "-f"]
            self.pin_contents = Path(args[compose_files[-1]]).read_text(encoding="utf-8")
            return CommandResult(0, "", "")
        return CommandResult(1, "", "unexpected-command")


def _fixture(tmp_path, *, metadata=None, digest=RELEASE_DIGEST, acl=None, runner=None):
    env_file = tmp_path / "protected" / ".env"
    env_file.parent.mkdir()
    metadata_file = tmp_path / "trusted" / "metadata.json"
    metadata_file.parent.mkdir()
    metadata_file.write_text(
        json.dumps(metadata or {"release_sha": RELEASE_SHA, "image_digest": RELEASE_DIGEST}),
        encoding="utf-8",
    )
    if os.name != "nt":
        metadata_file.chmod(0o444)
    release_manifest_file = tmp_path / "trusted" / "release-manifest.json"
    write_manifest(
        build_manifest(
            repository_root=Path(__file__).resolve().parents[2],
            release_sha=RELEASE_SHA,
            image_reference=f"deployment-app:{RELEASE_SHA}",
            image_digest=RELEASE_DIGEST,
            image_revision=RELEASE_SHA,
            image_source=SOURCE,
        ),
        output=release_manifest_file,
        repository_root=Path(__file__).resolve().parents[2],
    )
    tls_dir = tmp_path / "tls"
    tls_dir.mkdir()
    env_file.write_text(
        "\n".join(
            (
                "SENTINEL_DNA_ENV=production",
                "SENTINEL_DNA_SECRET_KEY=" + random_secret(),
                "POSTGRES_PASSWORD=" + random_password(),
                f"SENTINEL_DNA_IMAGE_TAG={RELEASE_SHA}",
                f"SENTINEL_DNA_IMAGE_REVISION={RELEASE_REVISION}",
                f"SENTINEL_DNA_IMAGE_REVISION_FULL={RELEASE_SHA}",
                f"SENTINEL_DNA_IMAGE_CREATED={RELEASE_CREATED}",
                f"SENTINEL_DNA_IMAGE_DIGEST={digest}",
                f"SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE={metadata_file}",
                f"SENTINEL_DNA_TLS_DIR={tls_dir}",
                "SENTINEL_DNA_SECURE_COOKIES=1",
                "DATABASE_URL=postgresql://sentinel:test@postgres.example:5432/sentinel_dna",
            )
        ),
        encoding="utf-8",
    )
    image_info = {
        "Id": "sha256:image-id",
        "RepoDigests": [f"deployment-app@{RELEASE_DIGEST}"],
        "Config": {
            "Labels": {
                "com.sentinel-dna.git.revision.full": RELEASE_SHA,
                "org.opencontainers.image.source": SOURCE,
            },
            "User": "sentinel",
            "Entrypoint": [],
            "Cmd": ["gunicorn", "wsgi:application", "--bind", "0.0.0.0:5000"],
            "ExposedPorts": {"5000/tcp": {}},
        },
    }
    compose_info = {
        "services": {
            "app": {
                "image": f"deployment-app:{RELEASE_SHA}",
                "ports": [],
                "volumes": [{"target": "/run/sentinel/release/metadata.json", "read_only": True}],
            },
            "postgres": {"ports": []},
            "redis": {"ports": []},
            "nginx": {
                "ports": [
                    {"published": 80, "target": 80},
                    {"published": 443, "target": 443},
                ],
                "volumes": [{"target": "/etc/nginx/tls", "read_only": True}],
            },
        }
    }
    adapter = ControlledDeploymentAdapter(
        reviewed_sha=RELEASE_SHA,
        expected_digest=RELEASE_DIGEST,
        env_file=env_file,
        metadata_file=metadata_file,
        release_manifest_file=release_manifest_file,
        compose_file=Path("deployment/docker-compose.yml").resolve(),
        runner=runner or FakeRunner(image_info, compose_info),
        acl_inspector=FakeAclInspector(acl or SAFE_ENTRIES),
    )
    return adapter, env_file, metadata_file


def test_parse_icacls_safe_acl_without_secret_material():
    output = """C:\\ProgramData\\Sentinel-DNA\\release\\metadata.json
BUILTIN\\Users:(I)(RX)
BUILTIN\\Administrators:(I)(F)
NT AUTHORITY\\SYSTEM:(I)(F)
Successfully processed 1 files; Failed processing 0 files
"""
    entries = parse_icacls_output(output)
    assert {entry.rights for entry in entries} == {"RX", "F"}


def test_parse_icacls_preserves_deny_entries():
    entries = parse_icacls_output("BUILTIN\\Users:(DENY)(W)\n")
    assert entries == (AclEntry("BUILTIN\\Users", "DENY", "W"),)


@pytest.mark.skipif(os.name != "nt", reason="Windows ACL semantics are tested on Windows")
def test_acl_rejects_untrusted_write_access(tmp_path):
    config = tmp_path / "config"
    config.write_text("placeholder", encoding="utf-8")
    with pytest.raises(ControlledDeploymentError, match="untrusted_write"):
        validate_acl(
            config,
            FakeAclInspector(
                (
                    AclEntry("BUILTIN\\Users", "ALLOW", "M"),
                    AclEntry("BUILTIN\\Administrators", "ALLOW", "F"),
                    AclEntry("NT AUTHORITY\\SYSTEM", "ALLOW", "F"),
                )
            ),
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows ACL semantics are tested on Windows")
def test_acl_rejects_privileged_deny_access(tmp_path):
    config = tmp_path / "config"
    config.write_text("placeholder", encoding="utf-8")
    with pytest.raises(ControlledDeploymentError, match="privileged_deny"):
        validate_acl(
            config,
            FakeAclInspector(
                (
                    AclEntry("BUILTIN\\Users", "ALLOW", "RX"),
                    AclEntry("BUILTIN\\Administrators", "ALLOW", "F"),
                    AclEntry("BUILTIN\\Administrators", "DENY", "F"),
                    AclEntry("NT AUTHORITY\\SYSTEM", "ALLOW", "F"),
                )
            ),
        )


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode semantics are tested on POSIX")
def test_posix_acl_rejects_group_or_other_write_access(tmp_path):
    config = tmp_path / "config"
    config.write_text("placeholder", encoding="utf-8")
    config.chmod(0o664)
    with pytest.raises(ControlledDeploymentError, match="protected_path_writable_by_group_or_other"):
        validate_acl(config, FakeAclInspector())


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode semantics are tested on POSIX")
def test_posix_acl_rejects_writable_parent_directory(tmp_path):
    protected = tmp_path / "protected"
    protected.mkdir()
    protected.chmod(0o733)
    config = protected / "config"
    config.write_text("placeholder", encoding="utf-8")
    config.chmod(0o600)
    with pytest.raises(ControlledDeploymentError, match="protected_path_writable_by_group_or_other"):
        validate_acl(config, FakeAclInspector())


def test_acl_rejects_unknown_format():
    with pytest.raises(ControlledDeploymentError, match="acl_format"):
        parse_icacls_output("unexpected acl output")


def test_protected_configuration_must_be_outside_repository(tmp_path):
    repository_root = Path(__file__).resolve().parents[2]
    with pytest.raises(ControlledDeploymentError, match="inside_repository"):
        validate_protected_file(Path(__file__), repository_root, FakeAclInspector())


def test_protected_configuration_rejects_reparse_points(tmp_path, monkeypatch):
    config = tmp_path / "config"
    config.write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(controlled_deploy, "_is_reparse_point", lambda _: True)
    with pytest.raises(ControlledDeploymentError, match="protected_file_invalid"):
        validate_protected_file(config, Path(__file__).resolve().parents[2], FakeAclInspector())


def test_missing_protected_configuration_fails_closed(tmp_path):
    adapter, env_file, _ = _fixture(tmp_path)
    env_file.unlink()
    with pytest.raises(ControlledDeploymentError, match="protected_path_unavailable"):
        adapter.validate()


def test_direct_file_entrypoint_bootstraps_repository_import_for_configuration_validation(tmp_path, monkeypatch, capsys):
    repository_root = Path(__file__).resolve().parents[2]
    script = repository_root / "deployment" / "scripts" / "controlled_deploy.py"
    env_file = tmp_path / "protected" / "production.env"
    env_file.parent.mkdir()
    env_file.write_text("SENTINEL_DNA_ENV=production\n", encoding="utf-8")
    release_manifest_file = tmp_path / "release" / "release-manifest.json"
    release_manifest_file.parent.mkdir()
    write_manifest(
        build_manifest(
            repository_root=repository_root,
            release_sha=RELEASE_SHA,
            image_reference=f"deployment-app:{RELEASE_SHA}",
            image_digest=RELEASE_DIGEST,
            image_revision=RELEASE_SHA,
            image_source=SOURCE,
        ),
        output=release_manifest_file,
        repository_root=repository_root,
    )

    validator = types.ModuleType("deployment.scripts.validate_deployment_config")
    validator.merged_environment = lambda **_: {}
    validator.validate_configuration = lambda **_: ["synthetic:configuration-rejected"]

    original_deployment_modules = {
        name: module
        for name, module in sys.modules.items()
        if name == "deployment" or name.startswith("deployment.")
    }
    try:
        for name in tuple(original_deployment_modules):
            sys.modules.pop(name, None)
        sys.modules[validator.__name__] = validator
        acl_output = (
            f"{env_file}\n"
            "BUILTIN\\Users:(I)(RX)\n"
            "BUILTIN\\Administrators:(I)(F)\n"
            "NT AUTHORITY\\SYSTEM:(I)(F)\n"
        )

        real_subprocess_run = subprocess.run

        def fake_subprocess_run(args, **kwargs):
            if args[0] == "icacls":
                return subprocess.CompletedProcess(args, 0, stdout=acl_output, stderr="")
            return real_subprocess_run(args, **kwargs)

        monkeypatch.setattr(subprocess, "run", fake_subprocess_run)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys,
            "path",
            [entry for entry in sys.path if Path(entry or ".").resolve() != repository_root],
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [
                str(script),
                "--reviewed-sha",
                RELEASE_SHA,
                "--expected-digest",
                RELEASE_DIGEST,
                "--env-file",
                str(env_file),
                "--metadata-file",
                str(tmp_path / "trusted" / "metadata.json"),
                "--release-manifest",
                str(release_manifest_file),
                "--validate-only",
            ],
        )

        with pytest.raises(SystemExit) as raised:
            runpy.run_path(str(script), run_name="__main__")

        assert raised.value.code == 2
        assert str(repository_root) in sys.path
        output = capsys.readouterr()
        assert "Controlled deployment blocked: configuration_invalid" in output.out
        assert "ModuleNotFoundError" not in output.err
    finally:
        for name in tuple(sys.modules):
            if name == "deployment" or name.startswith("deployment."):
                sys.modules.pop(name, None)
        sys.modules.update(original_deployment_modules)


def test_missing_required_configuration_fails_without_secret_output(tmp_path):
    adapter, env_file, _ = _fixture(tmp_path)
    env_file.write_text("SENTINEL_DNA_ENV=production\n", encoding="utf-8")
    with pytest.raises(ControlledDeploymentError) as failure:
        adapter.validate()
    assert "S" * 48 not in str(failure.value)
    assert "P" * 32 not in str(failure.value)


def test_only_checked_in_production_compose_file_is_approved(tmp_path):
    repository_root = Path(__file__).resolve().parents[2]
    alternate = tmp_path / "compose.yml"
    alternate.write_text("services: {}\n", encoding="utf-8")
    with pytest.raises(ControlledDeploymentError, match="compose_file_not_approved"):
        validate_compose_file(alternate, repository_root)


def test_adapter_validates_release_metadata_and_compose_without_deploying(tmp_path):
    adapter, _, _ = _fixture(tmp_path)
    evidence = adapter.validate()
    assert evidence.release_sha == RELEASE_SHA
    assert evidence.image_digest == RELEASE_DIGEST
    assert not any("up" in call for call in adapter.runner.calls)
    compose_call = next(call for call in adapter.runner.calls if "compose" in call and "config" in call)
    assert compose_call[compose_call.index("--project-name") + 1] == "deployment"
    assert compose_call[compose_call.index("--env-file") + 1].endswith(".env")
    assert "SENTINEL_DNA_SECRET_KEY" not in adapter.runner.last_env
    assert "COMPOSE_PROJECT_NAME" not in adapter.runner.last_env


@pytest.mark.parametrize(
    ("metadata", "error"),
    (
        ({"release_sha": "wrong", "image_digest": RELEASE_DIGEST}, "revision_mismatch"),
        ({"release_sha": RELEASE_SHA, "image_digest": "sha256:" + "0" * 64}, "digest_mismatch"),
        ({"release_sha": RELEASE_SHA, "image_digest": RELEASE_DIGEST, "unexpected": "field"}, "fields_invalid"),
    ),
)
def test_adapter_rejects_invalid_trusted_metadata(tmp_path, metadata, error):
    adapter, _, _ = _fixture(tmp_path, metadata=metadata)
    with pytest.raises(ControlledDeploymentError, match=error):
        adapter._validate_metadata()


def test_adapter_rejects_wrong_image_digest(tmp_path):
    adapter, _, _ = _fixture(tmp_path)
    adapter.expected_digest = "sha256:" + "1" * 64
    with pytest.raises(ControlledDeploymentError, match="image_digest_mismatch"):
        adapter._validate_release()


def test_adapter_rejects_wrong_image_revision(tmp_path):
    adapter, _, _ = _fixture(tmp_path)
    adapter.reviewed_sha = "c" * 40
    with pytest.raises(ControlledDeploymentError, match="git_revision_mismatch"):
        adapter._validate_release()


def test_adapter_rejects_compose_public_internal_ports(tmp_path):
    adapter, _, _ = _fixture(tmp_path)
    adapter.runner.compose_info["services"]["app"]["ports"] = [{"published": 5000, "target": 5000}]
    with pytest.raises(ControlledDeploymentError, match="compose_app_boundary"):
        adapter.validate()


@pytest.mark.parametrize("service", ["postgres", "redis"])
def test_adapter_rejects_internal_service_host_ports(tmp_path, service):
    adapter, _, _ = _fixture(tmp_path)
    adapter.runner.compose_info["services"][service]["ports"] = [{"published": 5432, "target": 5432}]
    with pytest.raises(ControlledDeploymentError, match="compose_internal_port"):
        adapter.validate()


def test_adapter_rejects_wrong_nginx_public_boundary(tmp_path):
    adapter, _, _ = _fixture(tmp_path)
    adapter.runner.compose_info["services"]["nginx"]["ports"] = [{"published": 8443, "target": 443}]
    with pytest.raises(ControlledDeploymentError, match="compose_nginx_boundary"):
        adapter.validate()


def test_adapter_rejects_wrong_image_source(tmp_path):
    adapter, _, _ = _fixture(tmp_path)
    adapter.runner.image_info["Config"]["Labels"]["org.opencontainers.image.source"] = "https://untrusted.example"
    with pytest.raises(ControlledDeploymentError, match="image_source_mismatch"):
        adapter.validate()


def test_adapter_rejects_wrong_runtime_user(tmp_path):
    adapter, _, _ = _fixture(tmp_path)
    adapter.runner.image_info["Config"]["User"] = "root"
    with pytest.raises(ControlledDeploymentError, match="runtime_user_mismatch"):
        adapter.validate()


def test_adapter_rejects_writable_metadata_mount(tmp_path):
    adapter, _, _ = _fixture(tmp_path)
    adapter.runner.compose_info["services"]["app"]["volumes"][0]["read_only"] = False
    with pytest.raises(ControlledDeploymentError, match="metadata_mount"):
        adapter.validate()


def test_adapter_never_propagates_command_stderr_or_secret_values(tmp_path):
    adapter, _, _ = _fixture(tmp_path, runner=FakeRunner({}, {}, docker_error=True))
    with pytest.raises(ControlledDeploymentError) as failure:
        adapter.validate()
    assert "production-secret-must-not-escape" not in str(failure.value)


def test_execute_requires_all_validation_gates_before_up(tmp_path):
    adapter, _, _ = _fixture(tmp_path, metadata={"release_sha": "wrong", "image_digest": RELEASE_DIGEST})
    with pytest.raises(ControlledDeploymentError):
        adapter.execute()
    assert not any("up" in call for call in adapter.runner.calls)


def test_execute_pins_compose_to_verified_digest_and_only_checks_app(tmp_path):
    adapter, _, _ = _fixture(tmp_path)
    adapter.verify_runtime = lambda: None
    evidence = adapter.execute()
    assert f"deployment-app@{RELEASE_DIGEST}" in adapter.runner.pin_contents
    up_call = next(call for call in adapter.runner.calls if "up" in call)
    assert "--no-build" in up_call
    assert "--no-deps" in up_call
    assert up_call[-1] == "app"
    assert evidence.image_digest == RELEASE_DIGEST


def test_cli_requires_an_explicit_non_deploying_or_execute_mode():
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            [
                "--reviewed-sha",
                RELEASE_SHA,
                "--expected-digest",
                RELEASE_DIGEST,
                "--env-file",
                "C:\\ProgramData\\Sentinel-DNA\\deployment\\.env",
                "--metadata-file",
                "C:\\ProgramData\\Sentinel-DNA\\release\\metadata.json",
            ]
        )


def test_safe_evidence_contains_no_secret_values(tmp_path):
    adapter, _, _ = _fixture(tmp_path)
    evidence = adapter.validate()
    serialized = json.dumps(evidence.__dict__, sort_keys=True)
    assert "S" * 48 not in serialized
    assert "P" * 32 not in serialized
