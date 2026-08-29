"""Build and verify a deterministic, non-secret release-boundary manifest.

The manifest is a release evidence artifact.  It is intentionally generated
outside the repository tree, and its own output is excluded from the hashed
file set so there is no circular self-hash.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "sentinel-dna-release-manifest-v2"
EXPECTED_IMAGE_SOURCE = "https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
CREATED_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
MANIFEST_FIELDS = frozenset(
    (
        "schema_version",
        "repository",
        "files",
        "tracked_files",
        "artifact_references",
        "validation_evidence_references",
        "replay_digest_references",
        "image",
        "manifest_policy",
    )
)
REPOSITORY_FIELDS = frozenset(("release_sha", "branch", "tree_id", "tree_id_type"))
FILE_FIELDS = frozenset(("git_blob", "sha256"))
ARTIFACT_FIELDS = frozenset(("reference", "artifact_digest", "replay_digest", "commit_sha", "immutable"))
VALIDATION_EVIDENCE_FIELDS = frozenset(("source", "report_digest", "replay_digest"))
REPLAY_REFERENCE_FIELDS = frozenset(("source", "digest"))
IMAGE_FIELDS = frozenset(("reference", "digest", "id", "oci_revision", "oci_source", "oci_created", "git_revision_full"))
MANIFEST_POLICY_FIELDS = frozenset(("generated_output", "self_hash", "identity_excludes"))

# This is the reviewed release boundary.  The generated manifest is not part
# of this tuple and must be written outside the repository tree.
RELEASE_FILE_SET = (
    ".github/workflows/deployment-contract.yml",
    ".dockerignore",
    "Dockerfile",
    "deployment/docker-compose.yml",
    "deployment/nginx.conf",
    "deployment/scripts/build_context_policy.py",
    "deployment/scripts/controlled_deploy.py",
    "deployment/scripts/prepare_trusted_release_metadata.py",
    "deployment/scripts/release_manifest.py",
    "deployment/scripts/release_metadata.py",
    "deployment/scripts/validate_deployment_config.py",
    "deployment/scripts/deploy.sh",
    "deployment/staging/docker-compose.yml",
    "docs/CONTROLLED_DEPLOYMENT_ADAPTER.md",
    "docs/DEPLOYMENT_GUIDE.md",
    "docs/PRODUCTION_RUNBOOK.md",
    "tests/deployment/test_controlled_deploy.py",
    "tests/deployment/test_build_context_policy.py",
    "tests/deployment/test_release_contract.py",
    "tests/deployment/test_release_manifest.py",
    "tests/deployment/test_trusted_release_metadata.py",
    "tests/security/test_production_entrypoint_reconciliation.py",
)


class ReleaseManifestError(RuntimeError):
    """Raised when release evidence cannot be established safely."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _git(root: Path, *args: str, text: bool = True) -> str | bytes:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=text,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise ReleaseManifestError(f"Git release inspection failed: {detail}") from exc
    return result.stdout


def _git_text(root: Path, *args: str) -> str:
    output = _git(root, *args, text=True)
    assert isinstance(output, str)
    return output.strip()


def repository_branch(root: Path) -> str:
    try:
        branch = _git_text(root, "symbolic-ref", "--short", "-q", "HEAD")
    except ReleaseManifestError:
        branch = ""
    if branch:
        return branch
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return ""
    event = os.environ.get("GITHUB_EVENT_NAME", "").strip()
    ref = os.environ.get("GITHUB_REF", "").strip()
    if event == "pull_request" and ref.startswith("refs/pull/") and ref.endswith("/merge"):
        branch = os.environ.get("GITHUB_HEAD_REF", "").strip()
    elif event in {"push", "workflow_dispatch"} and ref.startswith("refs/heads/"):
        branch = ref.removeprefix("refs/heads/")
    else:
        return ""
    ci_sha = os.environ.get("GITHUB_SHA", "").strip()
    if not branch or not SHA_RE.fullmatch(ci_sha):
        return ""
    if _git_text(root, "rev-parse", "HEAD") != ci_sha:
        return ""
    try:
        subprocess.run(
            ["git", "check-ref-format", "--branch", branch],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return branch


def _git_blob(root: Path, release_sha: str, path: str) -> tuple[str, bytes]:
    object_name = f"{release_sha}:{path}"
    try:
        blob_id = _git_text(root, "rev-parse", object_name)
        content = _git(root, "show", object_name, text=False)
    except ReleaseManifestError as exc:
        raise ReleaseManifestError(f"Required release file is absent: {path}") from exc
    assert isinstance(content, bytes)
    return blob_id, content


def _validate_release_sha(release_sha: str) -> None:
    if not SHA_RE.fullmatch(release_sha):
        raise ReleaseManifestError("release SHA must be a 40-character lowercase Git SHA")


def _validate_digest(digest: str | None) -> None:
    if digest is not None and not DIGEST_RE.fullmatch(digest):
        raise ReleaseManifestError("image digest must be a full lowercase sha256 digest")


def _validate_created(created: str | None) -> None:
    if created is not None and not CREATED_RE.fullmatch(created):
        raise ReleaseManifestError("image creation timestamp must be a UTC second-precision timestamp")
    if created is not None:
        try:
            datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as exc:
            raise ReleaseManifestError("image creation timestamp is not a valid UTC timestamp") from exc


def _require_exact_keys(value: Any, expected: frozenset[str], error_code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ReleaseManifestError(error_code)
    return value


def _assert_outside_repository(path: Path, repository_root: Path) -> None:
    try:
        path.relative_to(repository_root)
    except ValueError:
        return
    raise ReleaseManifestError("release manifest output must be outside the repository")


def _assert_regular_nonreparse(path: Path, label: str) -> None:
    if not path.exists():
        raise ReleaseManifestError(f"{label} does not exist")
    if not path.is_file():
        raise ReleaseManifestError(f"{label} is not a regular file")
    if path.is_symlink():
        raise ReleaseManifestError(f"{label} must not be a symlink or reparse point")


def _assert_clean_worktree(repository_root: Path) -> None:
    # Git's porcelain output is the authoritative status.  stderr is not
    # copied into the manifest or exposed; Windows may warn about an unrelated
    # inaccessible ignored directory while still returning empty porcelain.
    status = _git_text(repository_root, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise ReleaseManifestError("repository worktree is not clean")


def _tracked_file_inventory(root: Path, release_sha: str) -> dict[str, dict[str, str]]:
    tree_lines = _git_text(root, "ls-tree", "-r", "--full-tree", release_sha).splitlines()
    inventory: dict[str, dict[str, str]] = {}
    blob_ids: dict[str, str] = {}
    for line in tree_lines:
        metadata, path = line.split("\t", 1)
        _mode, object_type, blob_id = metadata.split(" ", 2)
        if object_type == "blob":
            blob_ids[path] = blob_id

    archive = _git(root, "archive", "--format=tar", release_sha, text=False)
    assert isinstance(archive, bytes)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as stream:
        for member in stream.getmembers():
            path = member.name
            if path not in blob_ids:
                continue
            if member.isfile():
                handle = stream.extractfile(member)
                content = handle.read() if handle is not None else b""
            else:
                _blob_id, content = _git_blob(root, release_sha, path)
            inventory[path] = {
                "git_blob": blob_ids[path],
                "sha256": hashlib.sha256(content).hexdigest(),
            }
    if set(inventory) != set(blob_ids):
        missing = sorted(set(blob_ids) - set(inventory))
        raise ReleaseManifestError(f"tracked file inventory could not be materialized: {missing[0]}")
    return inventory


def _artifact_reference(path: Path, release_sha: str) -> dict[str, Any]:
    _assert_regular_nonreparse(path, "evidence artifact")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise ReleaseManifestError(f"evidence artifact is not valid JSON: {path.name}") from exc
    if not isinstance(payload, dict):
        raise ReleaseManifestError(f"evidence artifact shape is invalid: {path.name}")
    if payload.get("immutable") is not True:
        raise ReleaseManifestError(f"evidence artifact is not immutable: {path.name}")
    if payload.get("commit_sha") != release_sha:
        raise ReleaseManifestError(f"evidence artifact commit association is invalid: {path.name}")
    artifact_digest = payload.get("artifact_digest")
    replay_digest = payload.get("replay_digest")
    if not isinstance(artifact_digest, str) or not artifact_digest:
        raise ReleaseManifestError(f"evidence artifact digest is missing: {path.name}")
    if not isinstance(replay_digest, str) or not replay_digest:
        raise ReleaseManifestError(f"evidence artifact replay digest is missing: {path.name}")
    body = dict(payload)
    body.pop("artifact_digest", None)
    if hashlib.sha256((_canonical(body) + "\n").encode("utf-8")).hexdigest() != artifact_digest:
        raise ReleaseManifestError(f"evidence artifact digest mismatch: {path.name}")
    return {
        "reference": path.name,
        "artifact_digest": artifact_digest,
        "replay_digest": replay_digest,
        "commit_sha": release_sha,
        "immutable": True,
    }


def _artifact_evidence_references(payload: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    evidence: list[dict[str, str]] = []
    replay: list[dict[str, str]] = []
    source_items = payload.get("evidence_sources", ())
    if isinstance(source_items, dict):
        source_items = [dict(value, source=name) for name, value in source_items.items() if isinstance(value, dict)]
    if isinstance(source_items, list):
        for item in source_items:
            if not isinstance(item, dict):
                continue
            source = item.get("source")
            report_digest = item.get("report_digest")
            replay_digest = item.get("replay_digest")
            if source and report_digest and replay_digest:
                evidence.append({"source": str(source), "report_digest": str(report_digest), "replay_digest": str(replay_digest)})
                replay.append({"source": str(source), "digest": str(replay_digest)})
    return evidence, replay


def build_manifest(
    *,
    repository_root: Path,
    release_sha: str | None = None,
    image_reference: str | None = None,
    image_digest: str | None = None,
    image_id: str | None = None,
    image_revision: str | None = None,
    image_source: str = EXPECTED_IMAGE_SOURCE,
    image_created: str | None = None,
    artifact_paths: tuple[Path, ...] = (),
) -> dict[str, Any]:
    """Return deterministic release evidence for the current reviewed tree."""

    root = repository_root.resolve()
    actual_head = _git_text(root, "rev-parse", "HEAD")
    selected_sha = release_sha or actual_head
    _validate_release_sha(selected_sha)
    if selected_sha != actual_head:
        raise ReleaseManifestError("release SHA must equal the checked-out HEAD")
    _assert_clean_worktree(root)

    branch = repository_branch(root)
    if not branch:
        raise ReleaseManifestError("release branch is unavailable")
    tree_id = _git_text(root, "rev-parse", f"{selected_sha}^{{tree}}")
    files: dict[str, dict[str, str]] = {}
    for path in RELEASE_FILE_SET:
        blob_id, content = _git_blob(root, selected_sha, path)
        files[path] = {
            "git_blob": blob_id,
            "sha256": hashlib.sha256(content).hexdigest(),
        }

    tracked_files = _tracked_file_inventory(root, selected_sha)
    artifact_references: list[dict[str, Any]] = []
    validation_evidence_references: list[dict[str, str]] = []
    replay_digest_references: list[dict[str, str]] = []
    for artifact_path in artifact_paths:
        reference = _artifact_reference(Path(artifact_path).resolve(), selected_sha)
        artifact_references.append(reference)
        replay_digest_references.append({"source": reference["reference"], "digest": reference["replay_digest"]})
        try:
            artifact_payload = json.loads(Path(artifact_path).resolve().read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            raise ReleaseManifestError(f"evidence artifact is not valid JSON: {Path(artifact_path).name}") from exc
        if isinstance(artifact_payload, dict):
            evidence, replay = _artifact_evidence_references(artifact_payload)
            validation_evidence_references.extend(evidence)
            replay_digest_references.extend(replay)
    artifact_references.sort(key=lambda item: item["reference"])
    validation_evidence_references.sort(key=lambda item: (item["source"], item["replay_digest"]))
    replay_digest_references.sort(key=lambda item: (item["source"], item["digest"]))

    _validate_digest(image_digest)
    _validate_created(image_created)
    if image_source != EXPECTED_IMAGE_SOURCE:
        raise ReleaseManifestError("image source identity is invalid")
    if image_digest is not None and image_created is None:
        raise ReleaseManifestError("image creation timestamp is required for image-bound release certification")
    if image_digest is not None and not image_id:
        raise ReleaseManifestError("image ID is required for image-bound release certification")
    image = {
        "reference": image_reference or f"deployment-app:{selected_sha}",
        "digest": image_digest,
        "id": image_id,
        "oci_revision": image_revision or selected_sha,
        "git_revision_full": image_revision or selected_sha,
        "oci_source": image_source,
        "oci_created": image_created,
    }
    if image["oci_revision"] != selected_sha:
        raise ReleaseManifestError("image OCI revision must equal the release SHA")
    if image["git_revision_full"] != selected_sha:
        raise ReleaseManifestError("image full Git revision must equal the release SHA")

    return {
        "schema_version": SCHEMA_VERSION,
        "repository": {
            "release_sha": selected_sha,
            "branch": branch,
            "tree_id": tree_id,
            "tree_id_type": "git-object-id",
        },
        "files": files,
        "tracked_files": tracked_files,
        "artifact_references": artifact_references,
        "validation_evidence_references": validation_evidence_references,
        "replay_digest_references": replay_digest_references,
        "image": image,
        "manifest_policy": {
            "generated_output": "outside-repository",
            "self_hash": "excluded",
            "identity_excludes": ["timestamps", "manifest_identity"],
        },
    }


def write_manifest(manifest: dict[str, Any], *, output: Path, repository_root: Path) -> None:
    """Atomically write a non-secret manifest outside the repository."""

    target = output.resolve()
    root = repository_root.resolve()
    _assert_outside_repository(target, root)
    if not target.parent.exists() or not target.parent.is_dir():
        raise ReleaseManifestError("manifest output parent must already exist")
    if target.parent.is_symlink():
        raise ReleaseManifestError("manifest output parent must not be a symlink")
    if target.exists():
        raise ReleaseManifestError("refusing to overwrite existing release manifest")

    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    temporary = target.with_name(f".{target.name}.tmp")
    if temporary.exists():
        raise ReleaseManifestError("refusing to overwrite an existing manifest temporary file")
    try:
        temporary.write_text(payload, encoding="utf-8", newline="\n")
        temporary.replace(target)
    except OSError as exc:
        raise ReleaseManifestError(f"could not write release manifest: {exc}") from exc


def verify_manifest(
    *,
    manifest_path: Path,
    repository_root: Path,
    require_current_head: bool = True,
    require_image: bool = False,
    expected_release_sha: str | None = None,
    expected_image_digest: str | None = None,
    artifact_paths: tuple[Path, ...] = (),
    require_artifact_references: bool = False,
    require_validation_evidence: bool = False,
) -> None:
    """Verify a manifest against the reviewed Git tree without reading secrets."""

    root = repository_root.resolve()
    path = manifest_path.resolve()
    _assert_outside_repository(path, root)
    _assert_regular_nonreparse(path, "release manifest")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseManifestError("release manifest is not valid JSON") from exc

    manifest = _require_exact_keys(manifest, MANIFEST_FIELDS, "release manifest fields are invalid")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise ReleaseManifestError("unsupported release manifest schema")
    policy = _require_exact_keys(
        manifest["manifest_policy"],
        MANIFEST_POLICY_FIELDS,
        "release manifest policy fields are invalid",
    )
    if policy != {
        "generated_output": "outside-repository",
        "self_hash": "excluded",
        "identity_excludes": ["timestamps", "manifest_identity"],
    }:
        raise ReleaseManifestError("release manifest self-hash policy is invalid")

    repository = _require_exact_keys(
        manifest["repository"],
        REPOSITORY_FIELDS,
        "release manifest repository section is invalid",
    )
    release_sha = repository["release_sha"]
    if not isinstance(release_sha, str):
        raise ReleaseManifestError("release manifest release SHA is missing")
    _validate_release_sha(release_sha)
    if expected_release_sha is not None and release_sha != expected_release_sha:
        raise ReleaseManifestError("release manifest SHA does not match requested release")
    _validate_digest(expected_image_digest)
    expected_tree = _git_text(root, "rev-parse", f"{release_sha}^{{tree}}")
    if repository["tree_id"] != expected_tree:
        raise ReleaseManifestError("release manifest tree identity does not match Git")
    if repository["tree_id_type"] != "git-object-id":
        raise ReleaseManifestError("release manifest tree identity type is invalid")
    if require_current_head and _git_text(root, "rev-parse", "HEAD") != release_sha:
        raise ReleaseManifestError("release manifest SHA does not match checked-out HEAD")
    if require_current_head:
        _assert_clean_worktree(root)
        current_branch = repository_branch(root)
        if current_branch != repository["branch"]:
            raise ReleaseManifestError("release manifest branch does not match checked-out branch")

    files = manifest["files"]
    if not isinstance(files, dict) or set(files) != set(RELEASE_FILE_SET):
        raise ReleaseManifestError("release manifest file set does not match policy")
    for file_path in RELEASE_FILE_SET:
        if file_path in {"deployment/release-manifest.json", "release-manifest.json"}:
            raise ReleaseManifestError("release manifest must not hash its own output")
        entry = _require_exact_keys(
            files[file_path],
            FILE_FIELDS,
            f"release manifest entry is invalid: {file_path}",
        )
        blob_id, content = _git_blob(root, release_sha, file_path)
        if entry["git_blob"] != blob_id:
            raise ReleaseManifestError(f"Git blob mismatch: {file_path}")
        if entry["sha256"] != hashlib.sha256(content).hexdigest():
            raise ReleaseManifestError(f"SHA-256 mismatch: {file_path}")

    tracked_files = manifest["tracked_files"]
    if not isinstance(tracked_files, dict) or set(tracked_files) != set(_tracked_file_inventory(root, release_sha)):
        raise ReleaseManifestError("release manifest tracked file inventory does not match repository")
    expected_inventory = _tracked_file_inventory(root, release_sha)
    for file_path, expected_entry in expected_inventory.items():
        entry = _require_exact_keys(
            tracked_files[file_path],
            FILE_FIELDS,
            f"release manifest tracked file entry is invalid: {file_path}",
        )
        if entry != expected_entry:
            raise ReleaseManifestError(f"Tracked file inventory mismatch: {file_path}")

    artifact_references = manifest["artifact_references"]
    if not isinstance(artifact_references, list):
        raise ReleaseManifestError("release manifest artifact references are invalid")
    normalized_artifact_refs = []
    for reference in artifact_references:
        item = _require_exact_keys(reference, ARTIFACT_FIELDS, "release manifest artifact reference is invalid")
        if item["commit_sha"] != release_sha or item["immutable"] is not True:
            raise ReleaseManifestError("release manifest artifact provenance is invalid")
        normalized_artifact_refs.append(item)
    if require_artifact_references and not normalized_artifact_refs:
        raise ReleaseManifestError("release manifest artifact references are missing")
    expected_evidence_references: list[dict[str, str]] = []
    expected_replay_references: list[dict[str, str]] = []
    if artifact_paths:
        expected_artifacts = [_artifact_reference(Path(path).resolve(), release_sha) for path in artifact_paths]
        if sorted(normalized_artifact_refs, key=lambda item: item["reference"]) != sorted(expected_artifacts, key=lambda item: item["reference"]):
            raise ReleaseManifestError("release manifest artifact references do not match supplied artifacts")
        for artifact_path, artifact_reference in zip(artifact_paths, expected_artifacts):
            artifact_path = Path(artifact_path).resolve()
            try:
                artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
                raise ReleaseManifestError(f"evidence artifact is not valid JSON: {artifact_path.name}") from exc
            if not isinstance(artifact_payload, dict):
                raise ReleaseManifestError(f"evidence artifact shape is invalid: {artifact_path.name}")
            evidence, replay = _artifact_evidence_references(artifact_payload)
            expected_evidence_references.extend(evidence)
            expected_replay_references.append({"source": artifact_reference["reference"], "digest": artifact_reference["replay_digest"]})
            expected_replay_references.extend(replay)
        expected_evidence_references.sort(key=lambda item: (item["source"], item["replay_digest"]))
        expected_replay_references.sort(key=lambda item: (item["source"], item["digest"]))

    evidence_references = manifest["validation_evidence_references"]
    if not isinstance(evidence_references, list):
        raise ReleaseManifestError("release manifest validation evidence references are invalid")
    for reference in evidence_references:
        _require_exact_keys(reference, VALIDATION_EVIDENCE_FIELDS, "release manifest validation evidence reference is invalid")
    if require_validation_evidence and not evidence_references:
        raise ReleaseManifestError("release manifest validation evidence references are missing")
    if artifact_paths and evidence_references != expected_evidence_references:
        raise ReleaseManifestError("release manifest validation evidence references do not match supplied artifacts")

    replay_references = manifest["replay_digest_references"]
    if not isinstance(replay_references, list):
        raise ReleaseManifestError("release manifest replay digest references are invalid")
    for reference in replay_references:
        _require_exact_keys(reference, REPLAY_REFERENCE_FIELDS, "release manifest replay digest reference is invalid")
    if require_artifact_references and not replay_references:
        raise ReleaseManifestError("release manifest replay digest references are missing")
    if artifact_paths and replay_references != expected_replay_references:
        raise ReleaseManifestError("release manifest replay digest references do not match supplied artifacts")

    image = _require_exact_keys(
        manifest["image"],
        IMAGE_FIELDS,
        "release manifest image section is invalid",
    )
    if image["oci_revision"] != release_sha:
        raise ReleaseManifestError("image OCI revision does not match release SHA")
    if image["git_revision_full"] != release_sha:
        raise ReleaseManifestError("image full Git revision does not match release SHA")
    if image["oci_source"] != EXPECTED_IMAGE_SOURCE:
        raise ReleaseManifestError("image source identity is invalid")
    created = image["oci_created"]
    if created is not None:
        if not isinstance(created, str):
            raise ReleaseManifestError("image creation timestamp field is invalid")
        _validate_created(created)
    digest = image["digest"]
    if digest is not None:
        if not isinstance(digest, str):
            raise ReleaseManifestError("image digest field is invalid")
        _validate_digest(digest)
    if require_image and digest is None:
        raise ReleaseManifestError("verified image digest is required for release certification")
    if require_image and (not isinstance(image["id"], str) or not image["id"]):
        raise ReleaseManifestError("verified image ID is required for release certification")
    if require_image and created is None:
        raise ReleaseManifestError("verified image creation timestamp is required for release certification")
    if expected_image_digest is not None and digest != expected_image_digest:
        raise ReleaseManifestError("release manifest image digest does not match requested digest")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="build a deterministic manifest")
    build.add_argument("--repository-root", type=Path, default=Path.cwd())
    build.add_argument("--release-sha")
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--image-reference")
    build.add_argument("--image-digest")
    build.add_argument("--image-id")
    build.add_argument("--image-revision")
    build.add_argument("--image-source", default=EXPECTED_IMAGE_SOURCE)
    build.add_argument("--image-created")
    build.add_argument("--artifact", action="append", type=Path, default=[])

    verify = subparsers.add_parser("verify", help="verify a deterministic manifest")
    verify.add_argument("--repository-root", type=Path, default=Path.cwd())
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--allow-different-head", action="store_true")
    verify.add_argument("--require-image", action="store_true")
    verify.add_argument("--expected-release-sha")
    verify.add_argument("--expected-image-digest")
    verify.add_argument("--artifact", action="append", type=Path, default=[])
    verify.add_argument("--require-artifact-references", action="store_true")
    verify.add_argument("--require-validation-evidence", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "build":
            manifest = build_manifest(
                repository_root=args.repository_root,
                release_sha=args.release_sha,
                image_reference=args.image_reference,
                image_digest=args.image_digest,
                image_id=args.image_id,
                image_revision=args.image_revision,
                image_source=args.image_source,
                image_created=args.image_created,
                artifact_paths=tuple(args.artifact),
            )
            write_manifest(manifest, output=args.output, repository_root=args.repository_root)
            print("Release manifest generated without secret material")
        else:
            verify_manifest(
                manifest_path=args.manifest,
                repository_root=args.repository_root,
                require_current_head=not args.allow_different_head,
                require_image=args.require_image,
                expected_release_sha=args.expected_release_sha,
                expected_image_digest=args.expected_image_digest,
                artifact_paths=tuple(args.artifact),
                require_artifact_references=args.require_artifact_references,
                require_validation_evidence=args.require_validation_evidence,
            )
            print("Release manifest verified")
    except ReleaseManifestError as exc:
        print(f"Release manifest blocked: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
