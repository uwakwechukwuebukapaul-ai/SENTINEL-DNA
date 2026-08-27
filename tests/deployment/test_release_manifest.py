from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest

from deployment.scripts.release_manifest import (
    RELEASE_FILE_SET,
    SCHEMA_VERSION,
    ReleaseManifestError,
    build_manifest,
    verify_manifest,
    write_manifest,
)
from tests.credential_helpers import random_token


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def clean_repository(tmp_path: Path) -> Path:
    repository_root = tmp_path / "repository"
    subprocess.run(
        ["git", "clone", "--quiet", "--no-local", str(REPOSITORY_ROOT), str(repository_root)],
        check=True,
        capture_output=True,
        text=True,
    )
    if os.name != "nt":
        repository_root.chmod(0o700)
    return repository_root


def test_manifest_is_deterministic_and_excludes_its_output(tmp_path: Path, clean_repository: Path) -> None:
    first = build_manifest(
        repository_root=clean_repository,
        image_reference="deployment-app:current-release",
    )
    second = build_manifest(
        repository_root=clean_repository,
        image_reference="deployment-app:current-release",
    )

    assert first == second
    assert first["schema_version"] == SCHEMA_VERSION
    assert tuple(first["files"]) == RELEASE_FILE_SET
    assert "deployment/release-manifest.json" not in first["files"]
    assert first["manifest_policy"]["self_hash"] == "excluded"
    assert first["image"]["digest"] is None


def test_manifest_rejects_dirty_worktree(clean_repository: Path) -> None:
    tracked_file = clean_repository / "Dockerfile"
    tracked_file.write_text(tracked_file.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(ReleaseManifestError, match="repository worktree is not clean"):
        build_manifest(repository_root=clean_repository)


def test_manifest_round_trip_verifies_against_current_tree(tmp_path: Path, clean_repository: Path) -> None:
    manifest = build_manifest(
        repository_root=clean_repository,
        image_reference="deployment-app:current-release",
    )
    manifest_path = tmp_path / "sentinel-dna-release-manifest.json"
    write_manifest(manifest, output=manifest_path, repository_root=clean_repository)

    verify_manifest(
        manifest_path=manifest_path,
        repository_root=clean_repository,
    )


def test_manifest_rejects_output_inside_repository(clean_repository: Path) -> None:
    manifest = build_manifest(repository_root=clean_repository)

    with pytest.raises(ReleaseManifestError, match="outside the repository"):
        write_manifest(
            manifest,
            output=clean_repository / "deployment" / "release-manifest.json",
            repository_root=clean_repository,
        )


def test_manifest_rejects_tampered_hash(tmp_path: Path, clean_repository: Path) -> None:
    manifest = build_manifest(repository_root=clean_repository)
    manifest_path = tmp_path / "sentinel-dna-release-manifest.json"
    write_manifest(manifest, output=manifest_path, repository_root=clean_repository)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["files"]["Dockerfile"]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ReleaseManifestError, match="SHA-256 mismatch: Dockerfile"):
        verify_manifest(
            manifest_path=manifest_path,
            repository_root=clean_repository,
        )


def _write_manifest_for_verification(tmp_path: Path, clean_repository: Path, manifest: dict) -> Path:
    manifest_path = tmp_path / "sentinel-dna-release-manifest.json"
    write_manifest(manifest, output=manifest_path, repository_root=clean_repository)
    return manifest_path


@pytest.mark.parametrize(
    ("section", "field", "error"),
    (
        ("top-level", "unexpected", "release manifest fields are invalid"),
        ("repository", "unexpected", "release manifest repository section is invalid"),
        ("image", "unexpected", "release manifest image section is invalid"),
        ("file", "unexpected", "release manifest entry is invalid: Dockerfile"),
        ("manifest_policy", "unexpected", "release manifest policy fields are invalid"),
    ),
)
def test_manifest_rejects_unexpected_fields(tmp_path: Path, clean_repository: Path, section: str, field: str, error: str) -> None:
    manifest = build_manifest(repository_root=clean_repository)
    if section == "top-level":
        manifest[field] = "unexpected"
    elif section == "file":
        manifest["files"]["Dockerfile"][field] = "unexpected"
    else:
        manifest[section][field] = "unexpected"

    manifest_path = _write_manifest_for_verification(tmp_path, clean_repository, manifest)
    with pytest.raises(ReleaseManifestError, match=error):
        verify_manifest(manifest_path=manifest_path, repository_root=clean_repository)


@pytest.mark.parametrize(
    ("section", "field", "error"),
    (
        ("top-level", "image", "release manifest fields are invalid"),
        ("repository", "tree_id", "release manifest repository section is invalid"),
        ("image", "oci_source", "release manifest image section is invalid"),
        ("file", "sha256", "release manifest entry is invalid: Dockerfile"),
        ("manifest_policy", "self_hash", "release manifest policy fields are invalid"),
    ),
)
def test_manifest_rejects_missing_required_fields(tmp_path: Path, clean_repository: Path, section: str, field: str, error: str) -> None:
    manifest = build_manifest(repository_root=clean_repository)
    if section == "top-level":
        del manifest[field]
    elif section == "file":
        del manifest["files"]["Dockerfile"][field]
    else:
        del manifest[section][field]

    manifest_path = _write_manifest_for_verification(tmp_path, clean_repository, manifest)
    with pytest.raises(ReleaseManifestError, match=error):
        verify_manifest(manifest_path=manifest_path, repository_root=clean_repository)


def test_image_bound_manifest_remains_verifiable_and_failures_do_not_expose_secrets(tmp_path: Path, clean_repository: Path) -> None:
    digest = "sha256:" + "a" * 64
    secret = random_token()
    manifest = build_manifest(
        repository_root=clean_repository,
        image_reference="deployment-app:current-release",
        image_digest=digest,
        image_id="sha256:image-id",
    )
    valid_manifest_path = tmp_path / "valid-release-manifest.json"
    write_manifest(manifest, output=valid_manifest_path, repository_root=clean_repository)
    verify_manifest(
        manifest_path=valid_manifest_path,
        repository_root=clean_repository,
        require_image=True,
        expected_release_sha=manifest["repository"]["release_sha"],
        expected_image_digest=digest,
    )

    manifest["image"][secret] = "unexpected"
    manifest_path = _write_manifest_for_verification(tmp_path, clean_repository, manifest)

    with pytest.raises(ReleaseManifestError) as failure:
        verify_manifest(
            manifest_path=manifest_path,
            repository_root=clean_repository,
            require_image=True,
            expected_release_sha=manifest["repository"]["release_sha"],
            expected_image_digest=digest,
        )
    assert secret not in str(failure.value)
