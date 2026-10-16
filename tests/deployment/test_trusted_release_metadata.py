import json
import os
from pathlib import Path
import stat
import subprocess
from types import SimpleNamespace

import pytest

from deployment.scripts import prepare_trusted_release_metadata as trusted


REVISION = "a1" * 20
DIGEST = "sha256:" + "b" * 64
SOURCE = "https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA"
CREATED = "1970-01-01T00:00:00Z"


def fake_image(revision=REVISION, digest=DIGEST, created=CREATED):
    return {
        "RepoDigests": [f"deployment-app@{digest}"],
        "Config": {
            "Labels": {
                "com.sentinel-dna.git.revision.full": revision,
                "org.opencontainers.image.revision": revision,
                "org.opencontainers.image.source": SOURCE,
                "org.opencontainers.image.created": created,
            }
        },
    }


def configure_fake_release(monkeypatch, image_info=None):
    monkeypatch.setattr(
        trusted,
        "derive_release_metadata",
        lambda **_kwargs: {"SENTINEL_DNA_IMAGE_REVISION_FULL": REVISION},
    )
    monkeypatch.setattr(trusted, "_inspect_image", lambda *_args, **_kwargs: image_info or fake_image())


def test_prepare_metadata_requires_exact_verified_checkout_and_image(tmp_path, monkeypatch):
    configure_fake_release(monkeypatch)
    repository_root = tmp_path / "repository"
    repository_root.mkdir()
    output = tmp_path / "release" / "metadata.json"
    output.parent.mkdir(mode=0o700)
    if os.name != "nt":
        assert output.parent.stat().st_mode & 0o777 == 0o700

    metadata = trusted.prepare_metadata(
        image="deployment-app:" + REVISION,
        expected_revision=REVISION,
        expected_digest=DIGEST,
        expected_created=CREATED,
        output=output,
        repository_root=repository_root,
    )

    assert metadata == {"release_sha": REVISION, "image_digest": DIGEST}
    assert json.loads(output.read_text(encoding="utf-8")) == metadata
    assert set(json.loads(output.read_text(encoding="utf-8"))) == {"release_sha", "image_digest"}
    if os.name != "nt":
        assert output.stat().st_mode & 0o222 == 0


@pytest.mark.parametrize(
    ("expected_revision", "expected_digest", "image_info", "error"),
    [
        ("c2" * 20, DIGEST, fake_image(), "trusted_release_revision_mismatch"),
        (REVISION, "sha256:" + "c" * 64, fake_image(), "trusted_release_image_digest_mismatch"),
        (REVISION, DIGEST, fake_image(revision="c2" * 20), "trusted_release_image_revision_mismatch"),
        (
            REVISION,
            DIGEST,
            {**fake_image(), "Config": {"Labels": {**fake_image()["Config"]["Labels"], "org.opencontainers.image.revision": "c2" * 20}}},
            "trusted_release_oci_revision_mismatch",
        ),
        (REVISION, DIGEST, fake_image(digest="sha256:" + "c" * 64), "trusted_release_image_digest_mismatch"),
        (REVISION, DIGEST, fake_image(created="1970-01-01T00:00:01Z"), "trusted_release_image_created_mismatch"),
    ],
)
def test_prepare_metadata_fails_closed_for_release_mismatches(
    tmp_path, monkeypatch, expected_revision, expected_digest, image_info, error
):
    configure_fake_release(monkeypatch, image_info)
    output = tmp_path / "release" / "metadata.json"
    output.parent.mkdir(mode=0o700)
    with pytest.raises(trusted.TrustedReleaseMetadataError, match=error):
        trusted.prepare_metadata(
            image="deployment-app:" + REVISION,
            expected_revision=expected_revision,
            expected_digest=expected_digest,
            expected_created=CREATED,
            output=output,
            repository_root=Path(__file__).parents[2],
        )
    assert not output.exists()


def test_prepare_metadata_never_writes_inside_source_tree(tmp_path, monkeypatch):
    configure_fake_release(monkeypatch)
    with pytest.raises(trusted.TrustedReleaseMetadataError, match="outside_source_tree"):
        trusted.prepare_metadata(
            image="deployment-app:" + REVISION,
            expected_revision=REVISION,
            expected_digest=DIGEST,
            expected_created=CREATED,
            output=Path(__file__).parents[2] / "trusted-release-metadata.json",
            repository_root=Path(__file__).parents[2],
        )


def test_prepare_metadata_rejects_symlinked_parent_directory(tmp_path, monkeypatch):
    configure_fake_release(monkeypatch)
    repository_root = tmp_path / "repository"
    repository_root.mkdir()
    output_parent = tmp_path / "release"
    output_parent.mkdir(mode=0o700)
    output = output_parent / "metadata.json"
    original_lstat = Path.lstat

    def lstat_with_symlink(path):
        file_stat = original_lstat(path)
        if path == output_parent:
            return SimpleNamespace(st_mode=stat.S_IFLNK | 0o777, st_file_attributes=0)
        return file_stat

    monkeypatch.setattr(Path, "lstat", lstat_with_symlink)

    with pytest.raises(trusted.TrustedReleaseMetadataError, match="trusted_release_metadata_symlink_forbidden"):
        trusted.prepare_metadata(
            image="deployment-app:" + REVISION,
            expected_revision=REVISION,
            expected_digest=DIGEST,
            expected_created=CREATED,
            output=output,
            repository_root=repository_root,
        )

    assert not output.exists()


def test_prepare_metadata_rejects_real_junction_parent_before_canonicalization(tmp_path, monkeypatch):
    if os.name != "nt":
        pytest.skip("directory junctions require Windows")
    configure_fake_release(monkeypatch)
    repository_root = tmp_path / "repository"
    repository_root.mkdir()
    target_parent = tmp_path / "release-target"
    target_parent.mkdir(mode=0o700)
    output_parent = tmp_path / "release-junction"
    output = output_parent / "metadata.json"
    result = subprocess.run(
        [
            os.environ.get("COMSPEC", "cmd.exe"),
            "/c",
            "mklink",
            "/J",
            str(output_parent),
            str(target_parent),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"directory junction creation is unavailable: {result.stdout}{result.stderr}")

    original_resolve = Path.resolve
    resolve_calls = []

    def track_resolve(path, *args, **kwargs):
        resolve_calls.append(path)
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", track_resolve)
    try:
        with pytest.raises(
            trusted.TrustedReleaseMetadataError,
            match="trusted_release_metadata_symlink_forbidden",
        ):
            trusted.prepare_metadata(
                image="deployment-app:" + REVISION,
                expected_revision=REVISION,
                expected_digest=DIGEST,
                expected_created=CREATED,
                output=output,
                repository_root=repository_root,
            )

        assert resolve_calls == []
        assert not (target_parent / "metadata.json").exists()
    finally:
        output_parent.rmdir()


def test_prepare_metadata_rejects_reparse_component_before_canonicalization(tmp_path, monkeypatch):
    configure_fake_release(monkeypatch)
    repository_root = tmp_path / "repository"
    repository_root.mkdir()
    output_parent = tmp_path / "release"
    output_parent.mkdir(mode=0o700)
    output = output_parent / "metadata.json"
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    original_lstat = Path.lstat
    original_resolve = Path.resolve
    resolve_calls = []

    def lstat_with_reparse_point(path):
        file_stat = original_lstat(path)
        if path == output_parent:
            return SimpleNamespace(
                st_mode=file_stat.st_mode,
                st_file_attributes=reparse_flag,
            )
        return file_stat

    def track_resolve(path, *args, **kwargs):
        resolve_calls.append(path)
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", lstat_with_reparse_point)
    monkeypatch.setattr(Path, "resolve", track_resolve)

    with pytest.raises(trusted.TrustedReleaseMetadataError, match="trusted_release_metadata_symlink_forbidden"):
        trusted.prepare_metadata(
            image="deployment-app:" + REVISION,
            expected_revision=REVISION,
            expected_digest=DIGEST,
            expected_created=CREATED,
            output=output,
            repository_root=repository_root,
        )

    assert resolve_calls == []
    assert not output.exists()


def test_prepare_metadata_rejects_missing_parent_component(tmp_path, monkeypatch):
    configure_fake_release(monkeypatch)
    repository_root = tmp_path / "repository"
    repository_root.mkdir()
    output = tmp_path / "missing" / "release" / "metadata.json"

    with pytest.raises(
        trusted.TrustedReleaseMetadataError,
        match="trusted_release_metadata_parent_unavailable",
    ):
        trusted.prepare_metadata(
            image="deployment-app:" + REVISION,
            expected_revision=REVISION,
            expected_digest=DIGEST,
            expected_created=CREATED,
            output=output,
            repository_root=repository_root,
        )

    assert not output.parent.exists()


def test_prepare_metadata_rejects_invalid_digest_without_writing(tmp_path, monkeypatch):
    configure_fake_release(monkeypatch)
    output = tmp_path / "release" / "metadata.json"
    output.parent.mkdir(mode=0o700)
    with pytest.raises(trusted.TrustedReleaseMetadataError, match="trusted_release_digest_invalid"):
        trusted.prepare_metadata(
            image="deployment-app:" + REVISION,
            expected_revision=REVISION,
            expected_digest="not-a-digest",
            expected_created=CREATED,
            output=output,
            repository_root=Path(__file__).parents[2],
        )
    assert not output.exists()


def test_prepare_metadata_rejects_invalid_creation_timestamp_without_writing(tmp_path, monkeypatch):
    configure_fake_release(monkeypatch)
    output = tmp_path / "release" / "metadata.json"
    output.parent.mkdir(mode=0o700)
    with pytest.raises(trusted.TrustedReleaseMetadataError, match="trusted_release_image_created_invalid"):
        trusted.prepare_metadata(
            image="deployment-app:" + REVISION,
            expected_revision=REVISION,
            expected_digest=DIGEST,
            expected_created="2026-02-30T00:00:00Z",
            output=output,
            repository_root=Path(__file__).parents[2],
        )
    assert not output.exists()


def test_prepare_metadata_cli_requires_and_checks_expected_creation_time(tmp_path, monkeypatch):
    repository_root = tmp_path / "repository"
    repository_root.mkdir()
    output = tmp_path / "release" / "metadata.json"
    output.parent.mkdir(mode=0o700)
    configure_fake_release(monkeypatch)
    monkeypatch.setattr(trusted, "REPOSITORY_ROOT", repository_root)

    assert trusted.main(
        [
            "--image", "deployment-app:" + REVISION,
            "--expected-revision", REVISION,
            "--expected-digest", DIGEST,
            "--expected-image-created", CREATED,
            "--output", str(output),
        ]
    ) == 0
    assert json.loads(output.read_text(encoding="utf-8")) == {"release_sha": REVISION, "image_digest": DIGEST}
