#!/usr/bin/env python3
"""Prepare a protected, nonsecret Gate 1 release authorization artifact.

This command runs in the deployment/operator boundary, never in the
application container. It derives the checked-out revision and verifies the
local immutable image labels and digest before atomically writing a minimal
manifest outside the source tree.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from deployment.scripts.release_metadata import derive_release_metadata


REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
IMAGE_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
IMAGE_CREATED_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
IMAGE_SOURCE = "https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA"
METADATA_KEYS = frozenset(("release_sha", "image_digest"))


class TrustedReleaseMetadataError(RuntimeError):
    """Safe operator-facing release artifact failure."""


def _inspect_image(image: str, docker_executable: str = "docker") -> dict[str, Any]:
    try:
        result = subprocess.run(
            [docker_executable, "image", "inspect", image],
            check=True,
            capture_output=True,
            text=True,
        )
        inspected = json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, UnicodeError, ValueError, TypeError):
        raise TrustedReleaseMetadataError("trusted_release_image_unavailable")
    if not isinstance(inspected, list) or len(inspected) != 1 or not isinstance(inspected[0], dict):
        raise TrustedReleaseMetadataError("trusted_release_image_invalid")
    return inspected[0]


def _image_digest(info: dict[str, Any]) -> str:
    digests = info.get("RepoDigests") or []
    matching = [value.rsplit("@", 1)[1] for value in digests if isinstance(value, str) and "@" in value]
    if len(matching) != 1 or not IMAGE_DIGEST_PATTERN.fullmatch(matching[0]):
        raise TrustedReleaseMetadataError("trusted_release_image_digest_unavailable")
    return matching[0]


def _validate_output_path(output: Path, repository_root: Path) -> tuple[Path, Path]:
    if not output.is_absolute():
        raise TrustedReleaseMetadataError("trusted_release_metadata_path_must_be_absolute")
    try:
        resolved_output = output.resolve()
        resolved_root = repository_root.resolve()
        resolved_output.relative_to(resolved_root)
    except ValueError:
        pass
    else:
        raise TrustedReleaseMetadataError("trusted_release_metadata_must_be_outside_source_tree")
    parent = resolved_output.parent
    if not parent.is_dir() or parent.is_symlink():
        raise TrustedReleaseMetadataError("trusted_release_metadata_parent_unavailable")
    if os.name != "nt" and parent.stat().st_mode & 0o022:
        raise TrustedReleaseMetadataError("trusted_release_metadata_parent_insecure")
    if output.is_symlink():
        raise TrustedReleaseMetadataError("trusted_release_metadata_symlink_forbidden")
    return resolved_output, parent


def prepare_metadata(
    *,
    image: str,
    expected_revision: str,
    expected_digest: str,
    expected_created: str,
    output: Path,
    repository_root: Path,
    docker_executable: str = "docker",
) -> dict[str, str]:
    if not REVISION_PATTERN.fullmatch(expected_revision):
        raise TrustedReleaseMetadataError("trusted_release_revision_invalid")
    if not IMAGE_DIGEST_PATTERN.fullmatch(expected_digest):
        raise TrustedReleaseMetadataError("trusted_release_digest_invalid")
    if not IMAGE_CREATED_PATTERN.fullmatch(expected_created):
        raise TrustedReleaseMetadataError("trusted_release_image_created_invalid")
    try:
        datetime.strptime(expected_created, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise TrustedReleaseMetadataError("trusted_release_image_created_invalid") from exc
    current_revision = derive_release_metadata(repository_root=repository_root, source_date_epoch="0")[
        "SENTINEL_DNA_IMAGE_REVISION_FULL"
    ]
    if current_revision != expected_revision:
        raise TrustedReleaseMetadataError("trusted_release_revision_mismatch")
    info = _inspect_image(image, docker_executable=docker_executable)
    labels = info.get("Config", {}).get("Labels", {}) or {}
    if labels.get("com.sentinel-dna.git.revision.full") != expected_revision:
        raise TrustedReleaseMetadataError("trusted_release_image_revision_mismatch")
    if labels.get("org.opencontainers.image.revision") != expected_revision:
        raise TrustedReleaseMetadataError("trusted_release_oci_revision_mismatch")
    if labels.get("org.opencontainers.image.source") != IMAGE_SOURCE:
        raise TrustedReleaseMetadataError("trusted_release_image_source_mismatch")
    if _image_digest(info) != expected_digest:
        raise TrustedReleaseMetadataError("trusted_release_image_digest_mismatch")
    if labels.get("org.opencontainers.image.created") != expected_created:
        raise TrustedReleaseMetadataError("trusted_release_image_created_mismatch")

    resolved_output, parent = _validate_output_path(output, repository_root)
    metadata = {"release_sha": expected_revision, "image_digest": expected_digest}
    encoded = (json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=".gate1-release-", dir=parent)
    try:
        if os.name != "nt":
            os.fchmod(descriptor, 0o444)
        with os.fdopen(descriptor, "wb") as temporary:
            descriptor = -1
            temporary.write(encoded)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, resolved_output)
    except (OSError, ValueError):
        if descriptor >= 0:
            os.close(descriptor)
        try:
            Path(temporary_name).unlink(missing_ok=True)
        except OSError:
            pass
        raise TrustedReleaseMetadataError("trusted_release_metadata_write_failed")
    return metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--expected-digest", required=True)
    parser.add_argument("--expected-image-created", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--docker-executable", default="docker")
    args = parser.parse_args(argv)
    try:
        metadata = prepare_metadata(
            image=args.image,
            expected_revision=args.expected_revision,
            expected_digest=args.expected_digest,
            expected_created=args.expected_image_created,
            output=args.output,
            repository_root=REPOSITORY_ROOT,
            docker_executable=args.docker_executable,
        )
        print(f"Trusted release metadata prepared: revision={metadata['release_sha']}; digest={metadata['image_digest']}")
        return 0
    except TrustedReleaseMetadataError as exc:
        print(f"Trusted release metadata blocked: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
