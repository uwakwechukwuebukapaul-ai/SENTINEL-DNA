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
        image_created="1970-01-01T00:00:00Z",
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


def test_image_bound_manifest_requires_creation_timestamp(clean_repository: Path) -> None:
    with pytest.raises(ReleaseManifestError, match="creation timestamp is required"):
        build_manifest(
            repository_root=clean_repository,
            image_digest="sha256:" + "a" * 64,
            image_id="sha256:image-id",
        )


def test_manifest_rejects_tampered_full_git_revision(tmp_path: Path, clean_repository: Path) -> None:
    manifest = build_manifest(repository_root=clean_repository)
    manifest["image"]["git_revision_full"] = "0" * 40
    manifest_path = _write_manifest_for_verification(tmp_path, clean_repository, manifest)

    with pytest.raises(ReleaseManifestError, match="full Git revision"):
        verify_manifest(manifest_path=manifest_path, repository_root=clean_repository)


def test_image_bound_manifest_requires_image_id(clean_repository: Path) -> None:
    with pytest.raises(ReleaseManifestError, match="image ID is required"):
        build_manifest(
            repository_root=clean_repository,
            image_digest="sha256:" + "a" * 64,
            image_created="1970-01-01T00:00:00Z",
        )


def test_manifest_rejects_wrong_image_source(clean_repository: Path) -> None:
    with pytest.raises(ReleaseManifestError, match="image source identity is invalid"):
        build_manifest(repository_root=clean_repository, image_source="https://example.invalid/repo")


def _prepare_detached_github_pr_checkout(clean_repository: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    subprocess.run(
        ["git", "checkout", "--detach", "HEAD"],
        cwd=clean_repository,
        check=True,
        capture_output=True,
        text=True,
    )
    commit_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=clean_repository, text=True).strip()
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_REF", "refs/pull/3/merge")
    monkeypatch.setenv("GITHUB_HEAD_REF", "integrate/staging-persistence-dns-fix")
    monkeypatch.setenv("GITHUB_SHA", commit_sha)
    return commit_sha


def test_manifest_uses_verified_github_source_branch_for_detached_pr_checkout(
    clean_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_detached_github_pr_checkout(clean_repository, monkeypatch)

    manifest = build_manifest(repository_root=clean_repository)

    assert manifest["repository"]["branch"] == "integrate/staging-persistence-dns-fix"


def test_manifest_fails_closed_when_github_commit_identity_does_not_match_detached_head(
    clean_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_detached_github_pr_checkout(clean_repository, monkeypatch)
    monkeypatch.setenv("GITHUB_SHA", "0" * 40)

    with pytest.raises(ReleaseManifestError, match="release branch is unavailable"):
        build_manifest(repository_root=clean_repository)


def _prepare_detached_github_workflow_dispatch_checkout(
    clean_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[str, str]:
    subprocess.run(
        ["git", "checkout", "--detach", "HEAD"],
        cwd=clean_repository,
        check=True,
        capture_output=True,
        text=True,
    )
    commit_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=clean_repository, text=True).strip()
    tree_id = subprocess.check_output(
        ["git", "show", "-s", "--format=%T", "HEAD"], cwd=clean_repository, text=True
    ).strip()
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv(
        "GITHUB_WORKFLOW_REF",
        "sentinel/example/.github/workflows/deployment-contract.yml@refs/heads/main",
    )
    monkeypatch.setenv("GITHUB_WORKFLOW_SHA", "f" * 40)
    monkeypatch.setenv("GITHUB_REPOSITORY", "sentinel/example")
    monkeypatch.setenv("GITHUB_SHA", "0" * 40)
    monkeypatch.setenv("SENTINEL_DNA_AUTHORIZED_WORKFLOW_REF", "main")
    monkeypatch.setenv("SENTINEL_DNA_AUTHORIZED_WORKFLOW_SHA", "e" * 40)
    monkeypatch.setenv("SENTINEL_DNA_AUTHORIZED_RELEASE_REF", "main")
    monkeypatch.setenv("SENTINEL_DNA_AUTHORIZED_RELEASE_SHA", commit_sha)
    monkeypatch.setenv("SENTINEL_DNA_AUTHORIZED_RELEASE_TREE", tree_id)
    return commit_sha, tree_id


def test_manifest_accepts_detached_workflow_dispatch_with_separate_event_sha(
    clean_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commit_sha, tree_id = _prepare_detached_github_workflow_dispatch_checkout(clean_repository, monkeypatch)

    manifest = build_manifest(repository_root=clean_repository)

    assert manifest["repository"]["branch"] == "main"
    assert manifest["repository"]["release_sha"] == commit_sha
    assert manifest["repository"]["tree_id"] == tree_id
    assert os.environ.get("GITHUB_SHA") != commit_sha


def test_manifest_workflow_dispatch_event_sha_mismatch_does_not_bypass_release_binding(
    clean_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commit_sha, _tree_id = _prepare_detached_github_workflow_dispatch_checkout(clean_repository, monkeypatch)
    monkeypatch.setenv("GITHUB_SHA", "1" * 40)

    manifest = build_manifest(repository_root=clean_repository)

    assert manifest["repository"]["release_sha"] == commit_sha


def test_manifest_workflow_dispatch_requires_protected_release_ref(
    clean_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_detached_github_workflow_dispatch_checkout(clean_repository, monkeypatch)
    monkeypatch.delenv("SENTINEL_DNA_AUTHORIZED_RELEASE_REF")

    with pytest.raises(ReleaseManifestError, match="release branch is unavailable"):
        build_manifest(repository_root=clean_repository)


@pytest.mark.parametrize("field", ("SENTINEL_DNA_AUTHORIZED_RELEASE_SHA", "SENTINEL_DNA_AUTHORIZED_RELEASE_TREE"))
def test_manifest_workflow_dispatch_rejects_conflicting_protected_release_identity(
    clean_repository: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    _prepare_detached_github_workflow_dispatch_checkout(clean_repository, monkeypatch)
    monkeypatch.setenv(field, "a" * 40)

    with pytest.raises(ReleaseManifestError, match="release branch is unavailable"):
        build_manifest(repository_root=clean_repository)
