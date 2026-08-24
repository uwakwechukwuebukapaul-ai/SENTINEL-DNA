from __future__ import annotations

import json
from pathlib import Path

import pytest

from deployment.scripts.release_manifest import (
    RELEASE_FILE_SET,
    SCHEMA_VERSION,
    ReleaseManifestError,
    build_manifest,
    verify_manifest,
    write_manifest,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_manifest_is_deterministic_and_excludes_its_output() -> None:
    first = build_manifest(
        repository_root=REPOSITORY_ROOT,
        image_reference="deployment-app:current-release",
    )
    second = build_manifest(
        repository_root=REPOSITORY_ROOT,
        image_reference="deployment-app:current-release",
    )

    assert first == second
    assert first["schema_version"] == SCHEMA_VERSION
    assert tuple(first["files"]) == RELEASE_FILE_SET
    assert "deployment/release-manifest.json" not in first["files"]
    assert first["manifest_policy"]["self_hash"] == "excluded"
    assert first["image"]["digest"] is None


def test_manifest_round_trip_verifies_against_current_tree(tmp_path: Path) -> None:
    manifest = build_manifest(
        repository_root=REPOSITORY_ROOT,
        image_reference="deployment-app:current-release",
    )
    manifest_path = tmp_path / "sentinel-dna-release-manifest.json"
    write_manifest(manifest, output=manifest_path, repository_root=REPOSITORY_ROOT)

    verify_manifest(
        manifest_path=manifest_path,
        repository_root=REPOSITORY_ROOT,
    )


def test_manifest_rejects_output_inside_repository(tmp_path: Path) -> None:
    manifest = build_manifest(repository_root=REPOSITORY_ROOT)

    with pytest.raises(ReleaseManifestError, match="outside the repository"):
        write_manifest(
            manifest,
            output=REPOSITORY_ROOT / "deployment" / "release-manifest.json",
            repository_root=REPOSITORY_ROOT,
        )


def test_manifest_rejects_tampered_hash(tmp_path: Path) -> None:
    manifest = build_manifest(repository_root=REPOSITORY_ROOT)
    manifest_path = tmp_path / "sentinel-dna-release-manifest.json"
    write_manifest(manifest, output=manifest_path, repository_root=REPOSITORY_ROOT)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["files"]["Dockerfile"]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ReleaseManifestError, match="SHA-256 mismatch: Dockerfile"):
        verify_manifest(
            manifest_path=manifest_path,
            repository_root=REPOSITORY_ROOT,
        )
