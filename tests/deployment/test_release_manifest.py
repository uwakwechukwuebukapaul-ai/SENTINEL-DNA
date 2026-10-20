from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from types import SimpleNamespace

import pytest

import deployment.scripts.release_manifest as release_manifest_module
from deployment.scripts.trusted_release_metadata import (
    TrustedReleaseMetadataError,
    parse_trusted_release_metadata,
)
from deployment.scripts.release_manifest import (
    RELEASE_FILE_SET,
    SCHEMA_VERSION,
    ReleaseManifestError,
    _assert_regular_nonreparse,
    build_manifest,
    verify_manifest,
    write_manifest,
)
from tests.credential_helpers import random_token


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
IMAGE_ID = "sha256:" + "c" * 64


@pytest.fixture
def mock_trusted_metadata_reader(monkeypatch: pytest.MonkeyPatch):
    """Explicitly stub only secure reads in downstream manifest logic tests on Windows."""

    def install(responses: dict[Path, dict[str, str]]) -> None:
        if os.name == "nt":
            def read_metadata(path: str | os.PathLike[str], _repository_root: Path) -> dict[str, str]:
                try:
                    return responses[Path(path)]
                except KeyError as exc:
                    raise AssertionError("test did not provide a trusted metadata response") from exc

            monkeypatch.setattr(release_manifest_module, "read_trusted_release_metadata", read_metadata)

    return install


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
    assert "deployment/scripts/validate_deployment_contract.py" in RELEASE_FILE_SET
    assert "deployment/validation/contract.py" in RELEASE_FILE_SET
    assert "deployment/release-manifest.json" not in first["files"]
    assert first["manifest_policy"]["self_hash"] == "excluded"
    assert first["image"]["digest"] is None


def test_release_file_inventory_covers_trusted_release_boundary():
    required = {
        ".github/workflows/deployment-contract.yml",
        "deployment/scripts/controlled_deploy.py",
        "deployment/scripts/ghcr_candidate.py",
        "deployment/scripts/ghcr_tag_guard.py",
        "deployment/scripts/prepare_trusted_release_metadata.py",
        "deployment/scripts/release_manifest.py",
        "deployment/scripts/trusted_release_metadata.py",
        "deployment/scripts/validate_deployment_config.py",
        "tests/deployment/test_ghcr_candidate.py",
        "tests/deployment/test_ghcr_tag_guard.py",
    }

    assert required <= set(RELEASE_FILE_SET)


def test_manifest_supports_local_detached_checkout(
    tmp_path: Path, clean_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    subprocess.run(
        ["git", "checkout", "--detach", "HEAD"],
        cwd=clean_repository,
        check=True,
        capture_output=True,
        text=True,
    )

    manifest = build_manifest(repository_root=clean_repository)
    manifest_path = tmp_path / "detached-release-manifest.json"
    write_manifest(manifest, output=manifest_path, repository_root=clean_repository)
    verify_manifest(manifest_path=manifest_path, repository_root=clean_repository)

    assert manifest["repository"]["release_sha"] == subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=clean_repository, text=True
    ).strip()
    assert manifest["repository"]["branch"] == ""


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


def test_manifest_verification_rejects_symlink_path(tmp_path: Path, clean_repository: Path) -> None:
    manifest = build_manifest(repository_root=clean_repository)
    target_path = tmp_path / "valid-release-manifest.json"
    write_manifest(manifest, output=target_path, repository_root=clean_repository)
    link_path = tmp_path / "release-manifest-link.json"
    try:
        link_path.symlink_to(target_path)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(ReleaseManifestError, match="release manifest must not be a symlink or reparse point"):
        verify_manifest(manifest_path=link_path, repository_root=clean_repository)


def test_manifest_verification_rejects_intermediate_symlink(
    tmp_path: Path, clean_repository: Path
) -> None:
    manifest = build_manifest(repository_root=clean_repository)
    target_directory = tmp_path / "manifest-target"
    target_directory.mkdir()
    target_path = target_directory / "manifest.json"
    write_manifest(manifest, output=target_path, repository_root=clean_repository)
    link_directory = tmp_path / "manifest-link-directory"
    try:
        link_directory.symlink_to(target_directory, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(ReleaseManifestError, match="release manifest must not be a symlink or reparse point"):
        verify_manifest(manifest_path=link_directory / target_path.name, repository_root=clean_repository)


def test_manifest_verification_checks_reparse_point_before_resolving(
    tmp_path: Path, clean_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    component_path = tmp_path / "manifest-reparse-directory"
    manifest_path = component_path / "manifest.json"
    fake_stat = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_file_attributes=0x400)
    original_lstat = Path.lstat
    original_resolve = Path.resolve

    def lstat(path: Path):
        if path == component_path:
            return fake_stat
        return original_lstat(path)

    def resolve(path: Path, *args, **kwargs):
        if path == manifest_path:
            raise AssertionError("manifest path was resolved before component validation")
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", lstat)
    monkeypatch.setattr(Path, "resolve", resolve)
    with pytest.raises(ReleaseManifestError, match="release manifest must not be a symlink or reparse point"):
        verify_manifest(manifest_path=manifest_path, repository_root=clean_repository)


def test_manifest_writer_rejects_symlink_output(tmp_path: Path, clean_repository: Path) -> None:
    manifest = build_manifest(repository_root=clean_repository)
    target_path = tmp_path / "manifest-target.json"
    link_path = tmp_path / "release-manifest-link.json"
    try:
        link_path.symlink_to(target_path)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(ReleaseManifestError, match="manifest output must not be a symlink or reparse point"):
        write_manifest(manifest, output=link_path, repository_root=clean_repository)
    assert not target_path.exists()


def test_manifest_writer_rejects_intermediate_symlink(
    tmp_path: Path, clean_repository: Path
) -> None:
    manifest = build_manifest(repository_root=clean_repository)
    target_directory = tmp_path / "output-target"
    target_directory.mkdir()
    link_directory = tmp_path / "output-link-directory"
    try:
        link_directory.symlink_to(target_directory, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(ReleaseManifestError, match="manifest output must not be a symlink or reparse point"):
        write_manifest(
            manifest,
            output=link_directory / "manifest.json",
            repository_root=clean_repository,
        )
    assert not (target_directory / "manifest.json").exists()


def test_trusted_metadata_rejects_intermediate_symlink(
    tmp_path: Path, clean_repository: Path
) -> None:
    release_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=clean_repository, text=True
    ).strip()
    target_directory = tmp_path / "metadata-target"
    target_directory.mkdir()
    target_path = target_directory / "metadata.json"
    target_path.write_text(
        json.dumps({"release_sha": release_sha, "image_digest": "sha256:" + "a" * 64}),
        encoding="utf-8",
    )
    link_directory = tmp_path / "metadata-link-directory"
    try:
        link_directory.symlink_to(target_directory, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(ReleaseManifestError, match="trusted release metadata must not be a symlink or reparse point"):
        build_manifest(
            repository_root=clean_repository,
            trusted_metadata_path=link_directory / target_path.name,
        )


def test_trusted_metadata_rejects_intermediate_windows_reparse_component(
    tmp_path: Path, clean_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    component_path = tmp_path / "metadata-reparse-directory"
    metadata_path = component_path / "metadata.json"
    fake_stat = SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_file_attributes=0x400)
    original_lstat = Path.lstat
    original_resolve = Path.resolve

    def lstat(path: Path):
        if path == component_path:
            return fake_stat
        return original_lstat(path)

    def resolve(path: Path, *args, **kwargs):
        if path == metadata_path:
            raise AssertionError("metadata path was resolved before component validation")
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", lstat)
    monkeypatch.setattr(Path, "resolve", resolve)
    with pytest.raises(ReleaseManifestError, match="trusted release metadata must not be a symlink or reparse point"):
        build_manifest(repository_root=clean_repository, trusted_metadata_path=metadata_path)


def test_manifest_writer_checks_reparse_output_before_resolving(
    tmp_path: Path, clean_repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = build_manifest(repository_root=clean_repository)
    component_path = tmp_path / "manifest-reparse-directory"
    output = component_path / "manifest.json"
    fake_stat = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_file_attributes=0x400)
    original_lstat = Path.lstat
    original_resolve = Path.resolve

    def lstat(path: Path):
        if path == component_path:
            return fake_stat
        return original_lstat(path)

    def resolve(path: Path, *args, **kwargs):
        if path == output:
            raise AssertionError("output path was resolved before component validation")
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", lstat)
    monkeypatch.setattr(Path, "resolve", resolve)
    with pytest.raises(ReleaseManifestError, match="manifest output must not be a symlink or reparse point"):
        write_manifest(manifest, output=output, repository_root=clean_repository)


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


def _trusted_metadata(tmp_path: Path, release_sha: str, digest: str) -> Path:
    metadata_path = tmp_path / "trusted" / "metadata.json"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text(
        json.dumps({"release_sha": release_sha, "image_digest": digest}) + "\n",
        encoding="utf-8",
    )
    return metadata_path


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
        image_id=IMAGE_ID,
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
        expected_image_created="1970-01-01T00:00:00Z",
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
            expected_image_created="1970-01-01T00:00:00Z",
        )
    assert secret not in str(failure.value)


def test_image_bound_manifest_binds_trusted_metadata_and_creation_time(
    tmp_path: Path,
    clean_repository: Path,
    mock_trusted_metadata_reader,
) -> None:
    digest = "sha256:" + "a" * 64
    created = "1970-01-01T00:00:00Z"
    release_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=clean_repository, text=True).strip()
    trusted_metadata = _trusted_metadata(tmp_path, release_sha, digest)
    mock_trusted_metadata_reader(
        {trusted_metadata: {"release_sha": release_sha, "image_digest": digest}}
    )
    manifest = build_manifest(
        repository_root=clean_repository,
        image_reference="deployment-app:current-release",
        image_digest=digest,
        image_id=IMAGE_ID,
        image_revision=release_sha,
        image_created=created,
        trusted_metadata_path=trusted_metadata,
    )

    assert manifest["repository"]["release_sha"] == release_sha
    assert manifest["image"]["digest"] == digest
    assert manifest["image"]["oci_created"] == created
    manifest_path = _write_manifest_for_verification(tmp_path, clean_repository, manifest)
    verify_manifest(
        manifest_path=manifest_path,
        repository_root=clean_repository,
        require_image=True,
        require_trusted_metadata=True,
        trusted_metadata_path=trusted_metadata,
        expected_release_sha=release_sha,
        expected_image_digest=digest,
        expected_image_created=created,
    )


@pytest.mark.parametrize(
    ("metadata_sha", "metadata_digest", "release_sha", "image_digest", "error"),
    (
        ("0" * 40, "sha256:" + "a" * 64, None, "sha256:" + "a" * 64, "release SHA must equal the checked-out HEAD"),
        (None, "sha256:" + "b" * 64, None, "sha256:" + "a" * 64, "image digest does not match trusted release metadata"),
    ),
)
def test_manifest_build_rejects_trusted_metadata_mismatch(
    tmp_path: Path,
    clean_repository: Path,
    metadata_sha: str | None,
    metadata_digest: str,
    release_sha: str | None,
    image_digest: str,
    error: str,
    mock_trusted_metadata_reader,
) -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=clean_repository, text=True).strip()
    metadata_path = _trusted_metadata(tmp_path, metadata_sha or head, metadata_digest)
    mock_trusted_metadata_reader(
        {metadata_path: {"release_sha": metadata_sha or head, "image_digest": metadata_digest}}
    )
    with pytest.raises(ReleaseManifestError, match=error):
        build_manifest(
            repository_root=clean_repository,
            release_sha=release_sha or None,
            image_digest=image_digest,
            image_id=IMAGE_ID,
            image_created="1970-01-01T00:00:00Z",
            trusted_metadata_path=metadata_path,
        )


@pytest.mark.parametrize(
    ("payload", "error"),
    (
        ({"release_sha": "a" * 40}, "trusted release metadata fields are invalid"),
        ({"release_sha": "a" * 40, "image_digest": "sha256:" + "b" * 64, "extra": True}, "trusted release metadata fields are invalid"),
        ({"release_sha": "bad", "image_digest": "sha256:" + "b" * 64}, "release SHA must be a 40-character lowercase Git SHA"),
        ({"release_sha": "a" * 40, "image_digest": "bad"}, "image digest must be a full lowercase sha256 digest"),
    ),
)
def test_trusted_metadata_requires_exact_fields_and_valid_values(
    payload: dict, error: str
) -> None:
    with pytest.raises(TrustedReleaseMetadataError, match=error):
        parse_trusted_release_metadata(json.dumps(payload).encode("utf-8"))


def test_trusted_metadata_rejects_malformed_json() -> None:
    with pytest.raises(TrustedReleaseMetadataError, match="trusted release metadata is not valid JSON"):
        parse_trusted_release_metadata(b'{"release_sha":')


@pytest.mark.parametrize(
    "payload",
    (
        '{"release_sha":"' + "a" * 40 + '","release_sha":"' + "b" * 40 + '","image_digest":"sha256:' + "c" * 64 + '"}',
        '{"release_sha":"' + "a" * 40 + '","image_digest":"sha256:' + "c" * 64 + '","image_digest":"sha256:' + "d" * 64 + '"}',
        '{"release_sha":"' + "a" * 40 + '","image_digest":"sha256:' + "c" * 64 + '","extra":"private-marker","extra":"second"}',
        '{"release_sha":"' + "a" * 40 + '","image_digest":"sha256:' + "c" * 64 + '","extra":{"key":"one","key":"private-marker"}}',
    ),
)
def test_trusted_metadata_rejects_duplicate_keys_without_echoing_input(
    payload: str,
) -> None:
    with pytest.raises(TrustedReleaseMetadataError, match="trusted release metadata is not valid JSON") as failure:
        parse_trusted_release_metadata(payload.encode("utf-8"))
    assert "private-marker" not in str(failure.value)


def test_trusted_metadata_must_be_outside_repository(tmp_path: Path, clean_repository: Path) -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=clean_repository, text=True).strip()
    metadata_path = _trusted_metadata(tmp_path, head, "sha256:" + "a" * 64)
    in_repository = clean_repository / "trusted-metadata.json"
    in_repository.write_bytes(metadata_path.read_bytes())
    with pytest.raises(ReleaseManifestError, match="outside the repository"):
        build_manifest(repository_root=clean_repository, trusted_metadata_path=in_repository)


def test_trusted_metadata_rejects_symlink(tmp_path: Path, clean_repository: Path) -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=clean_repository, text=True).strip()
    metadata_path = _trusted_metadata(tmp_path, head, "sha256:" + "a" * 64)
    link_path = tmp_path / "trusted-metadata-link.json"
    try:
        link_path.symlink_to(metadata_path)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")
    with pytest.raises(ReleaseManifestError, match="symlink or reparse point"):
        build_manifest(repository_root=clean_repository, trusted_metadata_path=link_path)


def test_trusted_metadata_rejects_windows_reparse_attribute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    metadata_path = tmp_path / "trusted-metadata.json"
    metadata_path.write_text("{}", encoding="utf-8")
    fake_stat = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_file_attributes=0x400)
    monkeypatch.setattr(Path, "lstat", lambda _path: fake_stat)
    with pytest.raises(ReleaseManifestError, match="symlink or reparse point"):
        _assert_regular_nonreparse(metadata_path, "trusted release metadata")


def test_image_bound_certification_requires_trusted_metadata(tmp_path: Path, clean_repository: Path) -> None:
    digest = "sha256:" + "a" * 64
    manifest = build_manifest(
        repository_root=clean_repository,
        image_digest=digest,
        image_id=IMAGE_ID,
        image_created="1970-01-01T00:00:00Z",
    )
    manifest_path = _write_manifest_for_verification(tmp_path, clean_repository, manifest)
    with pytest.raises(ReleaseManifestError, match="trusted release metadata is required"):
        verify_manifest(
            manifest_path=manifest_path,
            repository_root=clean_repository,
            require_image=True,
            expected_release_sha=manifest["repository"]["release_sha"],
            expected_image_digest=digest,
            expected_image_created="1970-01-01T00:00:00Z",
            require_trusted_metadata=True,
        )


def test_image_bound_certification_requires_expected_creation_timestamp(
    tmp_path: Path,
    clean_repository: Path,
    mock_trusted_metadata_reader,
) -> None:
    digest = "sha256:" + "a" * 64
    release_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=clean_repository, text=True).strip()
    trusted_metadata = _trusted_metadata(tmp_path, release_sha, digest)
    mock_trusted_metadata_reader(
        {trusted_metadata: {"release_sha": release_sha, "image_digest": digest}}
    )
    manifest = build_manifest(
        repository_root=clean_repository,
        image_digest=digest,
        image_id=IMAGE_ID,
        image_created="1970-01-01T00:00:00Z",
        trusted_metadata_path=trusted_metadata,
    )
    manifest_path = _write_manifest_for_verification(tmp_path, clean_repository, manifest)
    with pytest.raises(ReleaseManifestError, match="expected image creation timestamp is required"):
        verify_manifest(
            manifest_path=manifest_path,
            repository_root=clean_repository,
            require_image=True,
            require_trusted_metadata=True,
            trusted_metadata_path=trusted_metadata,
            expected_release_sha=release_sha,
            expected_image_digest=digest,
        )


@pytest.mark.parametrize(
    ("metadata_sha", "metadata_digest", "expected_sha", "expected_digest", "expected_created", "error"),
    (
        ("0" * 40, "sha256:" + "a" * 64, None, "sha256:" + "a" * 64, "1970-01-01T00:00:00Z", "release manifest SHA does not match trusted release metadata"),
        (None, "sha256:" + "b" * 64, None, "sha256:" + "a" * 64, "1970-01-01T00:00:00Z", "release manifest image digest does not match trusted release metadata"),
        (None, "sha256:" + "a" * 64, None, "sha256:" + "b" * 64, "1970-01-01T00:00:00Z", "release manifest image digest does not match requested digest"),
        (None, "sha256:" + "a" * 64, "0" * 40, "sha256:" + "a" * 64, "1970-01-01T00:00:00Z", "release manifest SHA does not match requested release"),
        (None, "sha256:" + "a" * 64, None, "sha256:" + "a" * 64, "1970-01-01T00:00:01Z", "release manifest image creation timestamp does not match requested timestamp"),
    ),
)
def test_image_bound_certification_rejects_metadata_and_identity_mismatches(
    tmp_path: Path,
    clean_repository: Path,
    metadata_sha: str | None,
    metadata_digest: str,
    expected_sha: str | None,
    expected_digest: str,
    expected_created: str,
    error: str,
    mock_trusted_metadata_reader,
) -> None:
    digest = "sha256:" + "a" * 64
    created = "1970-01-01T00:00:00Z"
    release_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=clean_repository, text=True).strip()
    trusted_metadata = _trusted_metadata(tmp_path, metadata_sha or release_sha, metadata_digest)
    trusted_build_metadata = _trusted_metadata(tmp_path / "build", release_sha, digest)
    mock_trusted_metadata_reader(
        {
            trusted_build_metadata: {"release_sha": release_sha, "image_digest": digest},
            trusted_metadata: {
                "release_sha": metadata_sha or release_sha,
                "image_digest": metadata_digest,
            },
        }
    )
    manifest = build_manifest(
        repository_root=clean_repository,
        image_digest=digest,
        image_id=IMAGE_ID,
        image_created=created,
        trusted_metadata_path=trusted_build_metadata,
    )
    manifest_path = _write_manifest_for_verification(tmp_path, clean_repository, manifest)

    with pytest.raises(ReleaseManifestError, match=error):
        verify_manifest(
            manifest_path=manifest_path,
            repository_root=clean_repository,
            require_image=True,
            require_trusted_metadata=True,
            trusted_metadata_path=trusted_metadata,
            expected_release_sha=expected_sha or release_sha,
            expected_image_digest=expected_digest,
            expected_image_created=expected_created,
        )


def test_image_bound_manifest_cli_passes_trusted_metadata_and_timestamp(
    tmp_path: Path, clean_repository: Path
) -> None:
    digest = "sha256:" + "a" * 64
    created = "1970-01-01T00:00:00Z"
    release_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=clean_repository, text=True).strip()
    trusted_metadata = _trusted_metadata(tmp_path, release_sha, digest)
    manifest_path = tmp_path / "cli-release-manifest.json"
    script = REPOSITORY_ROOT / "deployment" / "scripts" / "release_manifest.py"
    build_result = subprocess.run(
        [
            sys.executable, str(script), "build", "--repository-root", str(clean_repository),
            "--output", str(manifest_path), "--image-digest", digest, "--image-id", IMAGE_ID,
            "--image-revision", release_sha, "--image-created", created,
            "--trusted-metadata", str(trusted_metadata),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if os.name != "posix":
        assert build_result.returncode == 2
        assert "trusted metadata is unsupported on this platform" in build_result.stderr
        assert not manifest_path.exists()
        return
    assert build_result.returncode == 0, build_result.stderr
    subprocess.run(
        [
            sys.executable, str(script), "verify", "--repository-root", str(clean_repository),
            "--manifest", str(manifest_path), "--require-image", "--require-trusted-metadata",
            "--trusted-metadata", str(trusted_metadata), "--expected-release-sha", release_sha,
            "--expected-image-digest", digest, "--expected-image-created", created,
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def test_image_bound_manifest_requires_creation_timestamp(clean_repository: Path) -> None:
    with pytest.raises(ReleaseManifestError, match="creation timestamp is required"):
        build_manifest(
            repository_root=clean_repository,
            image_digest="sha256:" + "a" * 64,
            image_id=IMAGE_ID,
        )


def test_manifest_rejects_tampered_full_git_revision(tmp_path: Path, clean_repository: Path) -> None:
    manifest = build_manifest(repository_root=clean_repository)
    manifest["image"]["git_revision_full"] = "0" * 40
    manifest_path = _write_manifest_for_verification(tmp_path, clean_repository, manifest)

    with pytest.raises(ReleaseManifestError, match="full Git revision"):
        verify_manifest(manifest_path=manifest_path, repository_root=clean_repository)


def test_image_bound_manifest_requires_image_id(tmp_path: Path) -> None:
    with pytest.raises(ReleaseManifestError, match="image ID is required"):
        build_manifest(
            repository_root=tmp_path,
            image_digest="sha256:" + "a" * 64,
            image_created="1970-01-01T00:00:00Z",
        )


@pytest.mark.parametrize("image_id", ["sha256:image-id", "sha256:" + "A" * 64])
def test_image_bound_manifest_rejects_malformed_image_id(tmp_path: Path, image_id: str) -> None:
    with pytest.raises(ReleaseManifestError, match="full lowercase sha256 image ID"):
        build_manifest(
            repository_root=tmp_path,
            image_digest="sha256:" + "a" * 64,
            image_id=image_id,
            image_created="1970-01-01T00:00:00Z",
        )


def test_manifest_rejects_inspected_image_id_mismatch_directly():
    from deployment.scripts.release_manifest import _validate_expected_image_id

    with pytest.raises(ReleaseManifestError, match="image ID does not match inspected image"):
        _validate_expected_image_id(IMAGE_ID, "sha256:" + "d" * 64)


def test_manifest_verification_rejects_malformed_image_id(tmp_path: Path, clean_repository: Path) -> None:
    manifest = build_manifest(repository_root=clean_repository)
    manifest["image"]["id"] = "sha256:malformed"
    manifest_path = _write_manifest_for_verification(tmp_path, clean_repository, manifest)

    with pytest.raises(ReleaseManifestError, match="full lowercase sha256 image ID"):
        verify_manifest(manifest_path=manifest_path, repository_root=clean_repository)


def test_image_bound_manifest_rejects_inspected_image_id_mismatch(
    tmp_path: Path,
    clean_repository: Path,
    mock_trusted_metadata_reader,
) -> None:
    digest = "sha256:" + "a" * 64
    release_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=clean_repository, text=True).strip()
    metadata = _trusted_metadata(tmp_path, release_sha, digest)
    mock_trusted_metadata_reader({metadata: {"release_sha": release_sha, "image_digest": digest}})
    manifest = build_manifest(
        repository_root=clean_repository,
        image_digest=digest,
        image_id=IMAGE_ID,
        image_created="1970-01-01T00:00:00Z",
        trusted_metadata_path=metadata,
    )
    manifest_path = _write_manifest_for_verification(tmp_path, clean_repository, manifest)

    with pytest.raises(ReleaseManifestError, match="image ID does not match inspected image"):
        verify_manifest(
            manifest_path=manifest_path,
            repository_root=clean_repository,
            require_image=True,
            expected_image_id="sha256:" + "d" * 64,
            expected_release_sha=release_sha,
            expected_image_digest=digest,
            expected_image_created="1970-01-01T00:00:00Z",
            trusted_metadata_path=metadata,
            require_trusted_metadata=True,
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
