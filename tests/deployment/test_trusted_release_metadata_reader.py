from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from deployment.scripts import trusted_release_metadata as metadata_reader


@pytest.mark.parametrize(
    ("raw", "error"),
    (
        (b'{"release_sha":"' + b"a" * 40 + b'","image_digest":"sha256:' + b"b" * 64 + b'"}', None),
        (b'{"release_sha":"bad","image_digest":"sha256:' + b"b" * 64 + b'"}', "release SHA"),
        (b'{"release_sha":"' + b"a" * 40 + b'","image_digest":"bad"}', "image digest"),
        (b'{"release_sha":"' + b"a" * 40 + b'","release_sha":"' + b"b" * 40 + b'","image_digest":"sha256:' + b"c" * 64 + b'"}', "not valid JSON"),
        (b'{"release_sha":', "not valid JSON"),
        (b"{}" , "fields are invalid"),
        (b" " * 4097, "not valid JSON"),
    ),
)
def test_payload_validation_is_platform_independent(raw: bytes, error: str | None) -> None:
    if error is None:
        assert metadata_reader.parse_trusted_release_metadata(raw) == {
            "release_sha": "a" * 40,
            "image_digest": "sha256:" + "b" * 64,
        }
    else:
        with pytest.raises(metadata_reader.TrustedReleaseMetadataError, match=error):
            metadata_reader.parse_trusted_release_metadata(raw)


@pytest.mark.parametrize("raw", (None, "{}", 123, bytearray(b"{}")))
def test_payload_parser_rejects_non_bytes(raw: object) -> None:
    with pytest.raises(
        metadata_reader.TrustedReleaseMetadataError,
        match="trusted release metadata is not valid JSON",
    ):
        metadata_reader.parse_trusted_release_metadata(raw)  # type: ignore[arg-type]


@pytest.mark.skipif(os.name != "posix", reason="trusted metadata certification is unsupported on Windows")
def test_reader_returns_exact_release_binding(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    metadata_path = tmp_path / "protected" / "metadata.json"
    metadata_path.parent.mkdir()
    metadata_path.write_text(
        json.dumps({"release_sha": "a" * 40, "image_digest": "sha256:" + "b" * 64}) + "\n",
        encoding="utf-8",
    )
    if os.name == "posix":
        metadata_path.parent.chmod(0o700)
        metadata_path.chmod(0o444)

    assert metadata_reader.read_trusted_release_metadata(metadata_path, repository) == {
        "release_sha": "a" * 40,
        "image_digest": "sha256:" + "b" * 64,
    }


@pytest.mark.skipif(os.name != "posix", reason="descriptor-relative trusted metadata reads are POSIX-only")
def test_reader_rejects_parent_replacement_race(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    parent = tmp_path / "protected"
    parent.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    metadata_path = parent / "metadata.json"
    metadata_path.write_text(
        json.dumps({"release_sha": "a" * 40, "image_digest": "sha256:" + "b" * 64}) + "\n",
        encoding="utf-8",
    )
    (outside / "metadata.json").write_text(
        json.dumps({"release_sha": "c" * 40, "image_digest": "sha256:" + "d" * 64}) + "\n",
        encoding="utf-8",
    )
    parent.chmod(0o700)
    metadata_path.chmod(0o444)
    held_parent = tmp_path / "protected-original"
    real_open = os.open
    changed = False

    def replace_parent_before_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal changed
        if path == "protected" and dir_fd is not None and not changed:
            parent.rename(held_parent)
            parent.symlink_to(outside, target_is_directory=True)
            changed = True
        if dir_fd is None:
            return real_open(path, flags, mode)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(metadata_reader.os, "open", replace_parent_before_open)
    try:
        with pytest.raises(
            metadata_reader.TrustedReleaseMetadataError,
            match="must not be a symlink or reparse point",
        ):
            metadata_reader.read_trusted_release_metadata(metadata_path, repository)
    finally:
        if parent.is_symlink():
            parent.unlink()
        if held_parent.exists():
            held_parent.rename(parent)


@pytest.mark.skipif(os.name != "nt", reason="native Windows must fail closed")
def test_reader_rejects_native_windows(tmp_path: Path) -> None:
    metadata_path = tmp_path.parent / f"{tmp_path.name}-metadata.json"
    with pytest.raises(metadata_reader.TrustedReleaseMetadataError, match="unsupported on this platform"):
        metadata_reader.read_trusted_release_metadata(metadata_path, tmp_path)
