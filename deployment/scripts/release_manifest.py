"""Build and verify a deterministic, non-secret release-boundary manifest.

The manifest is a release evidence artifact.  It is intentionally generated
outside the repository tree, and its own output is excluded from the hashed
file set so there is no circular self-hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "sentinel-dna-release-manifest-v1"
EXPECTED_IMAGE_SOURCE = "https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
MANIFEST_FIELDS = frozenset(("schema_version", "repository", "files", "image", "manifest_policy"))
REPOSITORY_FIELDS = frozenset(("release_sha", "tree_id", "tree_id_type"))
FILE_FIELDS = frozenset(("git_blob", "sha256"))
IMAGE_FIELDS = frozenset(("reference", "digest", "id", "oci_revision", "oci_source"))
MANIFEST_POLICY_FIELDS = frozenset(("generated_output", "self_hash"))

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


def build_manifest(
    *,
    repository_root: Path,
    release_sha: str | None = None,
    image_reference: str | None = None,
    image_digest: str | None = None,
    image_id: str | None = None,
    image_revision: str | None = None,
    image_source: str = EXPECTED_IMAGE_SOURCE,
) -> dict[str, Any]:
    """Return deterministic release evidence for the current reviewed tree."""

    root = repository_root.resolve()
    actual_head = _git_text(root, "rev-parse", "HEAD")
    selected_sha = release_sha or actual_head
    _validate_release_sha(selected_sha)
    if selected_sha != actual_head:
        raise ReleaseManifestError("release SHA must equal the checked-out HEAD")
    _assert_clean_worktree(root)

    tree_id = _git_text(root, "rev-parse", f"{selected_sha}^{{tree}}")
    files: dict[str, dict[str, str]] = {}
    for path in RELEASE_FILE_SET:
        blob_id, content = _git_blob(root, selected_sha, path)
        files[path] = {
            "git_blob": blob_id,
            "sha256": hashlib.sha256(content).hexdigest(),
        }

    _validate_digest(image_digest)
    image = {
        "reference": image_reference or f"deployment-app:{selected_sha}",
        "digest": image_digest,
        "id": image_id,
        "oci_revision": image_revision or selected_sha,
        "oci_source": image_source,
    }
    if image["oci_revision"] != selected_sha:
        raise ReleaseManifestError("image OCI revision must equal the release SHA")

    return {
        "schema_version": SCHEMA_VERSION,
        "repository": {
            "release_sha": selected_sha,
            "tree_id": tree_id,
            "tree_id_type": "git-object-id",
        },
        "files": files,
        "image": image,
        "manifest_policy": {
            "generated_output": "outside-repository",
            "self_hash": "excluded",
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
    if policy != {"generated_output": "outside-repository", "self_hash": "excluded"}:
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

    image = _require_exact_keys(
        manifest["image"],
        IMAGE_FIELDS,
        "release manifest image section is invalid",
    )
    if image["oci_revision"] != release_sha:
        raise ReleaseManifestError("image OCI revision does not match release SHA")
    if image["oci_source"] != EXPECTED_IMAGE_SOURCE:
        raise ReleaseManifestError("image source identity is invalid")
    digest = image["digest"]
    if digest is not None:
        if not isinstance(digest, str):
            raise ReleaseManifestError("image digest field is invalid")
        _validate_digest(digest)
    if require_image and digest is None:
        raise ReleaseManifestError("verified image digest is required for release certification")
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

    verify = subparsers.add_parser("verify", help="verify a deterministic manifest")
    verify.add_argument("--repository-root", type=Path, default=Path.cwd())
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--allow-different-head", action="store_true")
    verify.add_argument("--require-image", action="store_true")
    verify.add_argument("--expected-release-sha")
    verify.add_argument("--expected-image-digest")
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
            )
            print("Release manifest verified")
    except ReleaseManifestError as exc:
        print(f"Release manifest blocked: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
