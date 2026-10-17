"""Race-resistant reader for protected Gate 1 release metadata."""

from __future__ import annotations

import json
import errno
import os
from pathlib import Path
import re
import stat
from typing import Any


REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
FIELDS = frozenset(("release_sha", "image_digest"))


class TrustedReleaseMetadataError(RuntimeError):
    """Raised when protected release metadata cannot be safely read."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def parse_trusted_release_metadata(raw: bytes) -> dict[str, str]:
    """Validate the bounded JSON payload independently of filesystem access."""

    if not isinstance(raw, bytes):
        raise TrustedReleaseMetadataError("trusted release metadata is not valid JSON")
    if len(raw) > 4096:
        raise TrustedReleaseMetadataError("trusted release metadata is not valid JSON")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise TrustedReleaseMetadataError("trusted release metadata is not valid JSON") from exc

    if not isinstance(payload, dict) or set(payload) != FIELDS:
        raise TrustedReleaseMetadataError("trusted release metadata fields are invalid")
    release_sha = payload["release_sha"]
    image_digest = payload["image_digest"]
    if not isinstance(release_sha, str) or not REVISION_RE.fullmatch(release_sha):
        raise TrustedReleaseMetadataError("release SHA must be a 40-character lowercase Git SHA")
    if not isinstance(image_digest, str) or not DIGEST_RE.fullmatch(image_digest):
        raise TrustedReleaseMetadataError("image digest must be a full lowercase sha256 digest")
    return {"release_sha": release_sha, "image_digest": image_digest}


def _validate_metadata_location(
    path: str | os.PathLike[str], repository_root: str | os.PathLike[str]
) -> Path:
    candidate = Path(os.path.abspath(os.fspath(path)))
    if not Path(path).is_absolute() or ".." in Path(path).parts:
        raise TrustedReleaseMetadataError("trusted metadata path is invalid")
    root = Path(repository_root).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        pass
    else:
        raise TrustedReleaseMetadataError("trusted release metadata must be outside the repository")
    if len(candidate.parts) < 2:
        raise TrustedReleaseMetadataError("trusted metadata path is invalid")
    return candidate


def read_trusted_release_metadata(
    path: str | os.PathLike[str], repository_root: str | os.PathLike[str]
) -> dict[str, str]:
    """Open metadata through pinned POSIX directory descriptors.

    Native Windows deliberately fails closed because this implementation's
    no-follow, descriptor-relative guarantees are POSIX-specific.
    """

    candidate = _validate_metadata_location(path, repository_root)
    if os.name != "posix":
        raise TrustedReleaseMetadataError("trusted metadata is unsupported on this platform")

    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(candidate.parts[0], directory_flags)
        for component in candidate.parts[1:-1]:
            next_descriptor = os.open(component, directory_flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        file_descriptor = os.open(candidate.parts[-1], file_flags, dir_fd=descriptor)
        file_stat = os.fstat(file_descriptor)
        parent_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise TrustedReleaseMetadataError("trusted release metadata is not a regular file")
        if file_stat.st_mode & 0o022 or parent_stat.st_mode & 0o022:
            raise TrustedReleaseMetadataError("trusted release metadata path is writable by group or other")
        with os.fdopen(file_descriptor, "rb") as stream:
            file_descriptor = -1
            raw = stream.read(4097)
        return parse_trusted_release_metadata(raw)
    except TrustedReleaseMetadataError:
        raise
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            message = "trusted release metadata must not be a symlink or reparse point"
        else:
            message = "trusted release metadata could not be safely read"
        raise TrustedReleaseMetadataError(message) from exc
    except (UnicodeError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise TrustedReleaseMetadataError("trusted release metadata is not valid JSON") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if "file_descriptor" in locals() and file_descriptor >= 0:
            os.close(file_descriptor)
