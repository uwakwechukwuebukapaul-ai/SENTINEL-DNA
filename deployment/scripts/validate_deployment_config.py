"""Fail-closed validation for protected production deployment configuration.

Only variable names and validation categories are reported. Secret values are
read in memory and are never printed, serialized, or included in exceptions.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
import re
from typing import Mapping
from urllib.parse import urlparse

try:
    from .release_metadata import derive_release_metadata
except ImportError:  # pragma: no cover - supports direct script execution
    from release_metadata import derive_release_metadata


SECRET_NAMES = ("SENTINEL_DNA_SECRET_KEY", "POSTGRES_PASSWORD")
METADATA_NAMES = (
    "SENTINEL_DNA_IMAGE_TAG",
    "SENTINEL_DNA_IMAGE_REVISION",
    "SENTINEL_DNA_IMAGE_REVISION_FULL",
    "SENTINEL_DNA_IMAGE_CREATED",
)
IMAGE_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
IMAGE_CREATED_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
IMAGE_TAG_PATTERN = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")
IMAGE_REVISION_SHORT_PATTERN = re.compile(r"^[0-9a-f]{7,39}$")
_PLACEHOLDER_MARKERS = ("change-me", "replace-with", "development-only")


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[name] = value
    return values


def merged_environment(
    *,
    environ: Mapping[str, str] | None = None,
    env_file: Path | None = None,
) -> dict[str, str]:
    values: dict[str, str] = {}
    if env_file is not None and env_file.exists():
        values.update(_parse_env_file(env_file))
    values.update(dict(os.environ if environ is None else environ))
    return values


def validate_configuration(
    *,
    environ: Mapping[str, str] | None = None,
    env_file: Path | None = None,
    repository_root: Path | None = None,
    require_postgresql: bool = False,
) -> list[str]:
    """Return safe error names; an empty list means valid configuration."""
    values = merged_environment(environ=environ, env_file=env_file)
    errors: list[str] = []
    for name in SECRET_NAMES:
        value = values.get(name, "").strip()
        if not value:
            errors.append(f"{name}:missing")
            continue
        if name == "SENTINEL_DNA_SECRET_KEY" and (
            len(value) < 32 or any(marker in value.lower() for marker in _PLACEHOLDER_MARKERS)
        ):
            errors.append(f"{name}:invalid")
        if name == "POSTGRES_PASSWORD" and any(marker in value.lower() for marker in _PLACEHOLDER_MARKERS):
            errors.append(f"{name}:invalid")

    expected = derive_release_metadata(repository_root=repository_root or Path(__file__).resolve().parents[2])
    expected_full_revision = expected["SENTINEL_DNA_IMAGE_REVISION_FULL"]
    for name in METADATA_NAMES:
        value = values.get(name, "").strip()
        if not value:
            errors.append(f"{name}:missing")
        elif name == "SENTINEL_DNA_IMAGE_TAG":
            # The tag is a release identifier supplied by the release
            # authority.  The release manifest, not the tag spelling, binds
            # that identifier to the reviewed commit and image digest.
            if not IMAGE_TAG_PATTERN.fullmatch(value):
                errors.append(f"{name}:invalid")
        elif name == "SENTINEL_DNA_IMAGE_REVISION":
            # This is an abbreviated presentation of the full revision.  It
            # may use Git's default seven characters or a longer abbreviation,
            # but it must be a prefix of the exact HEAD SHA.
            if not IMAGE_REVISION_SHORT_PATTERN.fullmatch(value):
                errors.append(f"{name}:invalid")
            elif not expected_full_revision.startswith(value):
                errors.append(f"{name}:does-not-match-full-revision")
        elif name == "SENTINEL_DNA_IMAGE_REVISION_FULL" and value != expected_full_revision:
            errors.append(f"{name}:does-not-match-HEAD")
        elif name == "SENTINEL_DNA_IMAGE_CREATED":
            if not IMAGE_CREATED_PATTERN.fullmatch(value):
                errors.append(f"{name}:invalid-ISO-8601")
            else:
                try:
                    datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
                except ValueError:
                    errors.append(f"{name}:invalid-ISO-8601")

    image_digest = values.get("SENTINEL_DNA_IMAGE_DIGEST", "").strip()
    if not image_digest:
        errors.append("SENTINEL_DNA_IMAGE_DIGEST:missing")
    elif not IMAGE_DIGEST_PATTERN.fullmatch(image_digest):
        errors.append("SENTINEL_DNA_IMAGE_DIGEST:invalid")

    metadata_path_value = values.get("SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE", "").strip()
    if not metadata_path_value:
        errors.append("SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE:missing")
    else:
        metadata_path = Path(metadata_path_value)
        try:
            if not metadata_path.is_absolute():
                errors.append("SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE:must-be-absolute")
            elif metadata_path.is_symlink() or not metadata_path.is_file():
                errors.append("SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE:unavailable")
            elif os.name != "nt" and (metadata_path.stat().st_mode & 0o222 or os.access(metadata_path, os.W_OK)):
                errors.append("SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE:writable")
            else:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                if not isinstance(metadata, dict):
                    errors.append("SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE:invalid")
                elif set(metadata) != {"release_sha", "image_digest"}:
                    errors.append("SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE:unexpected-fields")
                elif (
                    not isinstance(metadata.get("release_sha"), str)
                    or not isinstance(metadata.get("image_digest"), str)
                    or metadata["release_sha"] != expected["SENTINEL_DNA_IMAGE_REVISION_FULL"]
                    or metadata["image_digest"] != image_digest
                ):
                    errors.append("SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE:mismatch")
        except (OSError, UnicodeError, TypeError, ValueError, json.JSONDecodeError):
            errors.append("SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE:invalid")

    if values.get("SENTINEL_DNA_ENV", "production").lower() != "production":
        errors.append("SENTINEL_DNA_ENV:must-be-production")
    if values.get("SENTINEL_DNA_SECURE_COOKIES", "1") != "1":
        errors.append("SENTINEL_DNA_SECURE_COOKIES:must-be-enabled")
    database_url = values.get("DATABASE_URL", "").strip()
    if not database_url and require_postgresql:
        errors.append("DATABASE_URL:missing")
    elif database_url:
        parsed = urlparse(database_url)
        if parsed.scheme not in {"postgres", "postgresql"} or not parsed.netloc:
            errors.append("DATABASE_URL:invalid-postgresql-url")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    errors = validate_configuration(env_file=args.env_file)
    if errors:
        print("Deployment configuration invalid: " + ", ".join(errors))
        return 1
    print("Deployment configuration valid: protected variables present; release metadata contract verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
