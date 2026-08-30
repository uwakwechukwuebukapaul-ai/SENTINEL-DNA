#!/usr/bin/env python3
"""Fail-closed controlled deployment adapter for the production Compose lane.

The adapter is deliberately an operator/deployment boundary. It accepts an
already materialized protected environment file; it does not fetch, generate,
print, or rotate secrets. Validation reads configuration in memory, independently
verifies the image and trusted metadata, and inspects the rendered Compose
topology without exposing Compose output. Deployment requires an explicit
``--execute`` flag and recreates only the application service.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Protocol, Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if __name__ == "__main__" and str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from deployment.scripts.release_manifest import ReleaseManifestError, verify_manifest

EXPECTED_IMAGE_SOURCE = "https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA"
EXPECTED_METADATA_FIELDS = frozenset(("release_sha", "image_digest"))
EXPECTED_DOCKER_CONTEXT = "desktop-linux"
EXPECTED_COMPOSE_PROJECT = "deployment"
IMAGE_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
WRITE_RIGHTS = frozenset(("F", "M", "W", "D", "WD", "AD", "DC", "WA", "WEA"))
PRIVILEGED_PRINCIPALS = frozenset(("NT AUTHORITY\\SYSTEM", "BUILTIN\\ADMINISTRATORS"))
NORMALISED_PRIVILEGED_PRINCIPALS = frozenset(value.upper() for value in PRIVILEGED_PRINCIPALS)
CONTROLLED_ENVIRONMENT_NAMES = frozenset(
    {
        "SENTINEL_DNA_ENV",
        "SENTINEL_DNA_SECRET_KEY",
        "POSTGRES_PASSWORD",
        "SENTINEL_DNA_IMAGE_TAG",
        "SENTINEL_DNA_IMAGE_REVISION",
        "SENTINEL_DNA_IMAGE_REVISION_FULL",
        "SENTINEL_DNA_IMAGE_CREATED",
        "SENTINEL_DNA_IMAGE_DIGEST",
        "SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE",
        "SENTINEL_DNA_GATE1_TRUSTED_METADATA_PATH",
        "SENTINEL_DNA_TLS_DIR",
        "SENTINEL_DNA_SECURE_COOKIES",
        "SENTINEL_DNA_DB_PATH",
        "DATABASE_URL",
        "SENTINEL_DNA_IMAGE_SOURCE",
        "COMPOSE_FILE",
        "COMPOSE_PROJECT_NAME",
        "COMPOSE_PROFILES",
        "COMPOSE_ENV_FILES",
        "DOCKER_CONTEXT",
        "DOCKER_HOST",
    }
)


class ControlledDeploymentError(RuntimeError):
    """Safe, non-secret adapter failure."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> CommandResult:
        ...


class SubprocessRunner:
    """Capture command output in memory and never include it in failures."""

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> CommandResult:
        try:
            completed = subprocess.run(
                list(args),
                cwd=str(cwd) if cwd is not None else None,
                env=dict(env) if env is not None else None,
                capture_output=True,
                text=True,
                check=False,
            )
        except (OSError, ValueError) as exc:
            raise ControlledDeploymentError("command_unavailable") from exc
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)


@dataclass(frozen=True)
class AclEntry:
    principal: str
    access_type: str
    rights: str

    @property
    def writes(self) -> bool:
        return self.rights.upper() in WRITE_RIGHTS


def _is_reparse_point(path: Path) -> bool:
    """Reject symlinks and Windows reparse points at the trust boundary."""

    try:
        if path.is_symlink():
            return True
        attributes = getattr(path.stat(), "st_file_attributes", 0)
    except OSError as exc:
        raise ControlledDeploymentError("protected_path_unavailable") from exc
    return bool(attributes & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT


def parse_icacls_output(output: str) -> tuple[AclEntry, ...]:
    """Parse only principal/access/rights from icacls output.

    Unknown non-empty ACL lines are rejected rather than treated as safe. This
    prevents a changed icacls format from silently weakening the trust check.
    """

    entries: list[AclEntry] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("Successfully processed") or line.startswith("Failed processing"):
            continue
        match = re.match(r"^(?P<principal>.+?):(?P<rights>(?:\([^)]+\))+)$", line)
        if match is None:
            if re.match(r"^[A-Za-z]:\\", line):
                continue
            raise ControlledDeploymentError("acl_format_unrecognized")
        rights_tokens = re.findall(r"\(([^)]+)\)", match.group("rights"))
        if not rights_tokens:
            raise ControlledDeploymentError("acl_rights_unavailable")
        access_type = "DENY" if any(token.upper() == "DENY" for token in rights_tokens) else "ALLOW"
        entries.append(AclEntry(match.group("principal").strip(), access_type, rights_tokens[-1]))
    if not entries:
        raise ControlledDeploymentError("acl_entries_unavailable")
    return tuple(entries)


class AclInspector:
    def __init__(self, runner: CommandRunner):
        self._runner = runner

    def inspect(self, path: Path) -> tuple[AclEntry, ...]:
        result = self._runner.run(("icacls", str(path)))
        if result.returncode != 0:
            raise ControlledDeploymentError("acl_inspection_failed")
        return parse_icacls_output(result.stdout)


def _normalise_principal(principal: str) -> str:
    return principal.strip().upper()


def _is_privileged(principal: str) -> bool:
    return _normalise_principal(principal) in NORMALISED_PRIVILEGED_PRINCIPALS


def validate_acl(path: Path, inspector: AclInspector | None = None) -> None:
    """Require protected file and parent-directory access.

    On Windows, SYSTEM and Administrators must have full control while any
    non-privileged allow entry must not grant write/create/delete/replace
    rights. On POSIX, group/other write bits are rejected as a complementary
    development/CI check.
    """

    parent = path.parent
    if os.name != "nt":
        for candidate in (path, parent):
            if _is_reparse_point(candidate):
                raise ControlledDeploymentError("protected_path_reparse_point")
            if candidate.stat().st_mode & 0o022:
                raise ControlledDeploymentError("protected_path_writable_by_group_or_other")
        return
    if inspector is None:
        raise ControlledDeploymentError("windows_acl_inspector_required")
    for candidate in (path, parent):
        if _is_reparse_point(candidate):
            raise ControlledDeploymentError("protected_path_reparse_point")
        entries = inspector.inspect(candidate)
        for required in NORMALISED_PRIVILEGED_PRINCIPALS:
            if any(_normalise_principal(entry.principal) == required and entry.access_type.upper() == "DENY" for entry in entries):
                raise ControlledDeploymentError("protected_path_privileged_deny_access")
            if not any(
                _normalise_principal(entry.principal) == required
                and entry.access_type.upper() == "ALLOW"
                and entry.rights.upper() == "F"
                for entry in entries
            ):
                raise ControlledDeploymentError("protected_path_privileged_control_missing")
        for entry in entries:
            if entry.access_type.upper() == "ALLOW" and entry.writes and not _is_privileged(entry.principal):
                raise ControlledDeploymentError("protected_path_untrusted_write_access")


def _resolve_outside_repository(path: Path, repository_root: Path) -> Path:
    if not path.is_absolute():
        raise ControlledDeploymentError("protected_path_must_be_absolute")
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(repository_root.resolve())
    except ValueError:
        return path.resolve(strict=True)
    except OSError as exc:
        raise ControlledDeploymentError("protected_path_unavailable") from exc
    raise ControlledDeploymentError("protected_path_inside_repository")


def validate_protected_file(path: Path, repository_root: Path, inspector: AclInspector | None) -> Path:
    resolved = _resolve_outside_repository(path, repository_root)
    if _is_reparse_point(path) or _is_reparse_point(resolved) or not resolved.is_file():
        raise ControlledDeploymentError("protected_file_invalid")
    validate_acl(resolved, inspector)
    return resolved


def validate_protected_directory(path: Path, repository_root: Path, inspector: AclInspector | None) -> Path:
    resolved = _resolve_outside_repository(path, repository_root)
    if _is_reparse_point(path) or _is_reparse_point(resolved) or not resolved.is_dir():
        raise ControlledDeploymentError("protected_directory_invalid")
    validate_acl(resolved, inspector)
    return resolved


def validate_compose_file(path: Path, repository_root: Path) -> Path:
    """Allow only the checked-in production Compose contract."""

    expected = (repository_root / "deployment" / "docker-compose.yml").resolve()
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ControlledDeploymentError("compose_file_unavailable") from exc
    if resolved != expected or _is_reparse_point(path) or _is_reparse_point(resolved) or not resolved.is_file():
        raise ControlledDeploymentError("compose_file_not_approved")
    return resolved


def _load_json(result: CommandResult, error_code: str) -> Any:
    if result.returncode != 0:
        raise ControlledDeploymentError(error_code)
    try:
        return json.loads(result.stdout)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ControlledDeploymentError(error_code) from exc


def _safe_path_equal(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve()))


def _sanitized_process_environment() -> dict[str, str]:
    """Prevent inherited shell values from overriding the protected env file."""

    environment = dict(os.environ)
    for name in CONTROLLED_ENVIRONMENT_NAMES:
        environment.pop(name, None)
    return environment


def _published_ports(service: Mapping[str, Any]) -> set[int]:
    ports = service.get("ports") or []
    published: set[int] = set()
    for port in ports:
        if isinstance(port, Mapping):
            value = port.get("published")
        elif isinstance(port, str):
            value = port.split(":", 1)[0]
        else:
            raise ControlledDeploymentError("compose_port_format_invalid")
        try:
            published.add(int(value))
        except (TypeError, ValueError) as exc:
            raise ControlledDeploymentError("compose_port_format_invalid") from exc
    return published


def _volume_for_target(service: Mapping[str, Any], target: str) -> Mapping[str, Any] | None:
    for volume in service.get("volumes") or []:
        if isinstance(volume, Mapping) and volume.get("target") == target:
            return volume
    return None


def _exact_repo_digest(info: Mapping[str, Any], error_code: str) -> str:
    repo_digests = info.get("RepoDigests") or []
    matching = [value.rsplit("@", 1)[-1] for value in repo_digests if isinstance(value, str) and "@" in value]
    if len(matching) != 1 or not IMAGE_DIGEST_PATTERN.fullmatch(matching[0]):
        raise ControlledDeploymentError(error_code)
    return matching[0]


@dataclass(frozen=True)
class ReleaseEvidence:
    release_sha: str
    image: str
    image_id: str
    image_digest: str
    oci_revision: str
    git_revision_full: str
    oci_source: str
    oci_version: str
    oci_created: str
    runtime_user: str
    entrypoint: tuple[str, ...]
    command: tuple[str, ...]


class ControlledDeploymentAdapter:
    def __init__(
        self,
        *,
        reviewed_sha: str,
        expected_digest: str,
        env_file: Path,
        metadata_file: Path,
        release_manifest_file: Path,
        compose_file: Path,
        repository_root: Path = REPOSITORY_ROOT,
        docker_executable: str = "docker",
        runner: CommandRunner | None = None,
        acl_inspector: AclInspector | None = None,
    ):
        self.reviewed_sha = reviewed_sha
        self.expected_digest = expected_digest
        self.env_file = env_file
        self.metadata_file = metadata_file
        self.release_manifest_file = release_manifest_file
        self.compose_file = compose_file
        self.repository_root = repository_root
        self.docker_executable = docker_executable
        self.runner = runner or SubprocessRunner()
        self.acl_inspector = acl_inspector or AclInspector(self.runner)
        self.image = f"deployment-app:{reviewed_sha}"

    def _docker(self, *args: str) -> CommandResult:
        return self.runner.run(
            (self.docker_executable, "--context", EXPECTED_DOCKER_CONTEXT, *args),
            cwd=self.repository_root,
            env=_sanitized_process_environment(),
        )

    def _compose(self, *args: str, compose_files: Sequence[Path] | None = None) -> CommandResult:
        files = tuple(compose_files or (self.compose_file,))
        compose_options: list[str] = ["compose", "--project-name", EXPECTED_COMPOSE_PROJECT, "--env-file", str(self.env_file)]
        for compose_file in files:
            compose_options.extend(("-f", str(compose_file)))
        return self._docker(
            *compose_options,
            *args,
        )

    def _validate_configuration(self) -> Mapping[str, str]:
        from deployment.scripts.validate_deployment_config import merged_environment, validate_configuration

        env_path = validate_protected_file(self.env_file, self.repository_root, self.acl_inspector)
        values = merged_environment(environ={}, env_file=env_path)
        errors = validate_configuration(
            environ={},
            env_file=env_path,
            repository_root=self.repository_root,
            require_postgresql=True,
        )
        if errors:
            raise ControlledDeploymentError("configuration_invalid")
        metadata_binding = Path(values["SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE"])
        if not _safe_path_equal(metadata_binding, self.metadata_file):
            raise ControlledDeploymentError("configuration_metadata_path_mismatch")
        if values["SENTINEL_DNA_IMAGE_DIGEST"] != self.expected_digest:
            raise ControlledDeploymentError("configuration_digest_mismatch")
        tls_dir = Path(values.get("SENTINEL_DNA_TLS_DIR", ""))
        if not tls_dir.is_absolute() or not tls_dir.is_dir():
            raise ControlledDeploymentError("tls_directory_invalid")
        if tls_dir.is_symlink():
            raise ControlledDeploymentError("tls_directory_symlink_forbidden")
        validate_protected_directory(tls_dir, self.repository_root, self.acl_inspector)
        return values

    def _validate_release_manifest(self) -> None:
        try:
            verify_manifest(
                manifest_path=self.release_manifest_file,
                repository_root=self.repository_root,
                require_current_head=True,
                require_image=True,
                expected_release_sha=self.reviewed_sha,
                expected_image_digest=self.expected_digest,
            )
        except ReleaseManifestError as exc:
            raise ControlledDeploymentError("release_manifest_invalid") from exc

    def _validate_release(self, *, expected_created: str) -> ReleaseEvidence:
        from deployment.scripts.release_metadata import derive_release_metadata

        derived = derive_release_metadata(repository_root=self.repository_root, source_date_epoch="0")
        if derived["SENTINEL_DNA_IMAGE_REVISION_FULL"] != self.reviewed_sha:
            raise ControlledDeploymentError("git_revision_mismatch")
        if not IMAGE_DIGEST_PATTERN.fullmatch(self.expected_digest):
            raise ControlledDeploymentError("expected_digest_invalid")
        image_info = _load_json(self._docker("image", "inspect", self.image), "image_inspection_failed")
        if not isinstance(image_info, list) or len(image_info) != 1 or not isinstance(image_info[0], Mapping):
            raise ControlledDeploymentError("image_inspection_invalid")
        info = image_info[0]
        config = info.get("Config") or {}
        labels = config.get("Labels") or {}
        if _exact_repo_digest(info, "image_digest_unavailable") != self.expected_digest:
            raise ControlledDeploymentError("image_digest_mismatch")
        if not str(info.get("Id", "")):
            raise ControlledDeploymentError("image_id_unavailable")
        if labels.get("com.sentinel-dna.git.revision.full") != self.reviewed_sha:
            raise ControlledDeploymentError("image_revision_mismatch")
        if labels.get("org.opencontainers.image.revision") != self.reviewed_sha:
            raise ControlledDeploymentError("oci_revision_mismatch")
        if labels.get("org.opencontainers.image.source") != EXPECTED_IMAGE_SOURCE:
            raise ControlledDeploymentError("image_source_mismatch")
        if labels.get("org.opencontainers.image.version") != self.reviewed_sha:
            raise ControlledDeploymentError("oci_version_mismatch")
        if labels.get("org.opencontainers.image.created") != expected_created:
            raise ControlledDeploymentError("oci_created_mismatch")
        if config.get("User") != "sentinel":
            raise ControlledDeploymentError("image_runtime_user_mismatch")
        command = tuple(config.get("Cmd") or ())
        if "gunicorn" not in command or "wsgi:application" not in command:
            raise ControlledDeploymentError("image_entrypoint_mismatch")
        exposed = config.get("ExposedPorts") or {}
        if set(exposed) != {"5000/tcp"}:
            raise ControlledDeploymentError("image_exposed_port_mismatch")
        return ReleaseEvidence(
            release_sha=self.reviewed_sha,
            image=self.image,
            image_id=str(info.get("Id", "")),
            image_digest=self.expected_digest,
            oci_revision=str(labels.get("org.opencontainers.image.revision", "")),
            git_revision_full=str(labels.get("com.sentinel-dna.git.revision.full", "")),
            oci_source=str(labels.get("org.opencontainers.image.source", "")),
            oci_version=str(labels.get("org.opencontainers.image.version", "")),
            oci_created=str(labels.get("org.opencontainers.image.created", "")),
            runtime_user=str(config.get("User", "")),
            entrypoint=tuple(config.get("Entrypoint") or ()),
            command=command,
        )

    def _validate_metadata(self) -> None:
        metadata_path = validate_protected_file(self.metadata_file, self.repository_root, self.acl_inspector)
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ControlledDeploymentError("trusted_metadata_invalid") from exc
        if not isinstance(metadata, dict) or set(metadata) != EXPECTED_METADATA_FIELDS:
            raise ControlledDeploymentError("trusted_metadata_fields_invalid")
        if metadata.get("release_sha") != self.reviewed_sha:
            raise ControlledDeploymentError("trusted_metadata_revision_mismatch")
        if metadata.get("image_digest") != self.expected_digest:
            raise ControlledDeploymentError("trusted_metadata_digest_mismatch")

    def _validate_compose(self) -> None:
        self.compose_file = validate_compose_file(self.compose_file, self.repository_root)
        rendered = _load_json(self._compose("config", "--format", "json"), "compose_validation_failed")
        services = rendered.get("services") if isinstance(rendered, Mapping) else None
        if not isinstance(services, Mapping):
            raise ControlledDeploymentError("compose_services_invalid")
        required = {"app", "nginx", "postgres", "redis"}
        if not required.issubset(services):
            raise ControlledDeploymentError("compose_services_incomplete")
        app = services["app"]
        if app.get("image") != self.image or _published_ports(app):
            raise ControlledDeploymentError("compose_app_boundary_invalid")
        if _published_ports(services["postgres"]) or _published_ports(services["redis"]):
            raise ControlledDeploymentError("compose_internal_port_exposed")
        if _published_ports(services["nginx"]) != {80, 443}:
            raise ControlledDeploymentError("compose_nginx_boundary_invalid")
        metadata_volume = _volume_for_target(app, "/run/sentinel/release/metadata.json")
        if not metadata_volume or metadata_volume.get("read_only") is not True:
            raise ControlledDeploymentError("compose_metadata_mount_not_read_only")
        tls_volume = _volume_for_target(services["nginx"], "/etc/nginx/tls")
        if not tls_volume or tls_volume.get("read_only") is not True:
            raise ControlledDeploymentError("compose_tls_mount_not_read_only")

    def validate(self) -> ReleaseEvidence:
        self._validate_release_manifest()
        configuration = self._validate_configuration()
        self._validate_metadata()
        evidence = self._validate_release(expected_created=configuration["SENTINEL_DNA_IMAGE_CREATED"])
        self._validate_compose()
        return evidence

    def _container_for_service(self, service: str) -> Mapping[str, Any]:
        result = self._compose("ps", "-q", service)
        if result.returncode != 0:
            raise ControlledDeploymentError("runtime_container_lookup_failed")
        container_ids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if len(container_ids) != 1:
            raise ControlledDeploymentError("runtime_container_count_invalid")
        inspected = _load_json(self._docker("inspect", container_ids[0]), "runtime_inspection_failed")
        if not isinstance(inspected, list) or len(inspected) != 1 or not isinstance(inspected[0], Mapping):
            raise ControlledDeploymentError("runtime_inspection_invalid")
        return inspected[0]

    def verify_runtime(self) -> None:
        containers = {name: self._container_for_service(name) for name in ("app", "nginx", "postgres", "redis")}
        for name, container in containers.items():
            if (container.get("State") or {}).get("Status") != "running":
                raise ControlledDeploymentError("runtime_service_not_running")
            if name == "postgres" and (container.get("State") or {}).get("Health", {}).get("Status") != "healthy":
                raise ControlledDeploymentError("runtime_postgres_not_healthy")
        app_image_id = str(containers["app"].get("Image", ""))
        image = _load_json(self._docker("image", "inspect", app_image_id), "runtime_image_inspection_failed")
        if not isinstance(image, list) or len(image) != 1 or not isinstance(image[0], Mapping):
            raise ControlledDeploymentError("runtime_image_digest_mismatch")
        if _exact_repo_digest(image[0], "runtime_image_digest_mismatch") != self.expected_digest:
            raise ControlledDeploymentError("runtime_image_digest_mismatch")
        app_mounts = containers["app"].get("Mounts") or []
        metadata_mount = next((mount for mount in app_mounts if mount.get("Destination") == "/run/sentinel/release/metadata.json"), None)
        if not metadata_mount or metadata_mount.get("RW") is not False:
            raise ControlledDeploymentError("runtime_metadata_mount_invalid")
        for name in ("app", "postgres", "redis"):
            if (containers[name].get("HostConfig") or {}).get("PortBindings"):
                raise ControlledDeploymentError("runtime_internal_port_exposed")
        nginx_bindings = (containers["nginx"].get("HostConfig") or {}).get("PortBindings") or {}
        nginx_ports = {int(key.split("/", 1)[0]) for key in nginx_bindings}
        if nginx_ports != {80, 443}:
            raise ControlledDeploymentError("runtime_nginx_boundary_invalid")

    def execute(self) -> ReleaseEvidence:
        evidence = self.validate()
        # Revalidate every trust input immediately before execution and pin
        # Compose to the exact digest so a mutable tag cannot be rebound
        # between validation and use. Database migrations run as an explicit
        # one-shot job before the application service is recreated.
        evidence = self.validate()
        try:
            descriptor, temporary_name = tempfile.mkstemp(prefix=".controlled-deploy-pin-", suffix=".yml")
        except OSError as exc:
            raise ControlledDeploymentError("execution_pin_write_failed") from exc
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
                descriptor = -1
                temporary.write(
                    "services:\n"
                    "  migration:\n"
                    "    image: deployment-app@" + evidence.image_digest + "\n"
                    "  app:\n"
                    "    image: deployment-app@" + evidence.image_digest + "\n"
                )
                temporary.flush()
                os.fsync(temporary.fileno())
            migration = self._compose(
                "run",
                "--rm",
                "--no-build",
                "--no-deps",
                "migration",
                compose_files=(self.compose_file, Path(temporary_name)),
            )
            if migration.returncode != 0:
                raise ControlledDeploymentError("database_migration_failed")
            result = self._compose(
                "up",
                "-d",
                "--no-build",
                "--no-deps",
                "app",
                compose_files=(self.compose_file, Path(temporary_name)),
            )
            if result.returncode != 0:
                raise ControlledDeploymentError("application_deployment_failed")
        except OSError as exc:
            raise ControlledDeploymentError("execution_pin_write_failed") from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                Path(temporary_name).unlink(missing_ok=True)
            except OSError:
                pass
        self.verify_runtime()
        return evidence


def _write_evidence(
    path: Path,
    evidence: Mapping[str, Any],
    repository_root: Path = REPOSITORY_ROOT,
    acl_inspector: AclInspector | None = None,
) -> None:
    if not path.is_absolute():
        raise ControlledDeploymentError("evidence_path_must_be_absolute")
    try:
        path.resolve(strict=False).relative_to(repository_root.resolve())
    except ValueError:
        pass
    else:
        raise ControlledDeploymentError("evidence_path_inside_repository")
    if path.is_symlink() or (path.exists() and _is_reparse_point(path)):
        raise ControlledDeploymentError("evidence_path_reparse_point")
    if path.exists():
        raise ControlledDeploymentError("evidence_path_already_exists")
    if not path.parent.is_dir() or _is_reparse_point(path.parent):
        raise ControlledDeploymentError("evidence_parent_invalid")
    validate_acl(path.parent, acl_inspector)
    encoded = (json.dumps(evidence, sort_keys=True, indent=2) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=".controlled-deploy-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as temporary:
            descriptor = -1
            temporary.write(encoded)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, path)
    except OSError as exc:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            Path(temporary_name).unlink(missing_ok=True)
        except OSError:
            pass
        raise ControlledDeploymentError("evidence_write_failed") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewed-sha", required=True)
    parser.add_argument("--expected-digest", required=True)
    parser.add_argument("--env-file", required=True, type=Path)
    parser.add_argument("--metadata-file", required=True, type=Path)
    parser.add_argument("--release-manifest", required=True, type=Path)
    parser.add_argument("--compose-file", default=REPOSITORY_ROOT / "deployment" / "docker-compose.yml", type=Path)
    parser.add_argument("--docker-executable", default="docker")
    parser.add_argument("--evidence-output", type=Path)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--validate-only", action="store_true")
    modes.add_argument("--execute", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    adapter = ControlledDeploymentAdapter(
        reviewed_sha=args.reviewed_sha,
        expected_digest=args.expected_digest,
        env_file=args.env_file,
        metadata_file=args.metadata_file,
        release_manifest_file=args.release_manifest,
        compose_file=args.compose_file,
        docker_executable=args.docker_executable,
    )
    try:
        evidence = adapter.execute() if args.execute else adapter.validate()
        report = {
            "adapter": "controlled-production-deployment-v1",
            "mode": "execute" if args.execute else ("dry-run" if args.dry_run else "validate-only"),
            "release_sha": evidence.release_sha,
            "image": evidence.image,
            "image_id": evidence.image_id,
            "image_digest": evidence.image_digest,
            "oci_revision": evidence.oci_revision,
            "git_revision_full": evidence.git_revision_full,
            "oci_source": evidence.oci_source,
            "oci_version": evidence.oci_version,
            "oci_created": evidence.oci_created,
            "runtime_user": evidence.runtime_user,
            "entrypoint": list(evidence.entrypoint),
            "command": list(evidence.command),
            "configuration_validation": "PASS",
            "trusted_metadata_validation": "PASS",
            "compose_validation": "PASS",
            "deployment_topology": "PASS",
            "deployment_action": "EXECUTED" if args.execute else "NOT EXECUTED",
            "database_mutation": "NONE",
            "credential_mutation": "NONE",
            "container_restart": "EXECUTED" if args.execute else "NONE",
        }
        if args.evidence_output:
            _write_evidence(args.evidence_output, report, adapter.repository_root, adapter.acl_inspector)
        print(json.dumps(report, sort_keys=True))
        return 0
    except ControlledDeploymentError as exc:
        print(f"Controlled deployment blocked: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
