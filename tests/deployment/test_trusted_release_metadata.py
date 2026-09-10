import json
import os
from pathlib import Path

import pytest

from deployment.scripts import prepare_trusted_release_metadata as trusted


REVISION = "a1" * 20
DIGEST = "sha256:" + "b" * 64
SOURCE = "https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA"


def fake_image(revision=REVISION, digest=DIGEST):
    return {
        "RepoDigests": [f"deployment-app@{digest}"],
        "Config": {
            "Labels": {
                "com.sentinel-dna.git.revision.full": revision,
                "org.opencontainers.image.source": SOURCE,
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
    output = tmp_path / "release" / "metadata.json"
    output.parent.mkdir(mode=0o700)
    if os.name != "nt":
        assert output.parent.stat().st_mode & 0o777 == 0o700

    metadata = trusted.prepare_metadata(
        image="deployment-app:" + REVISION,
        expected_revision=REVISION,
        expected_digest=DIGEST,
        output=output,
        repository_root=Path(__file__).parents[2],
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
        (REVISION, DIGEST, fake_image(digest="sha256:" + "c" * 64), "trusted_release_image_digest_mismatch"),
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
            output=Path(__file__).parents[2] / "trusted-release-metadata.json",
            repository_root=Path(__file__).parents[2],
        )


def test_prepare_metadata_rejects_invalid_digest_without_writing(tmp_path, monkeypatch):
    configure_fake_release(monkeypatch)
    output = tmp_path / "release" / "metadata.json"
    output.parent.mkdir(mode=0o700)
    with pytest.raises(trusted.TrustedReleaseMetadataError, match="trusted_release_digest_invalid"):
        trusted.prepare_metadata(
            image="deployment-app:" + REVISION,
            expected_revision=REVISION,
            expected_digest="not-a-digest",
            output=output,
            repository_root=Path(__file__).parents[2],
        )
    assert not output.exists()
