"""Derive immutable Docker release metadata from the checked-out Git commit.

This helper emits release metadata only. It never reads or prints deployment
secrets. The output is suitable for a process environment or GitHub Actions'
GITHUB_ENV file.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
METADATA_NAMES = (
    "SENTINEL_DNA_IMAGE_TAG",
    "SENTINEL_DNA_IMAGE_REVISION",
    "SENTINEL_DNA_IMAGE_REVISION_FULL",
    "SENTINEL_DNA_IMAGE_CREATED",
)


def _git(*args: str, repository_root: Path = REPOSITORY_ROOT) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _created_at(source_date_epoch: str | None = None) -> str:
    value = source_date_epoch or os.getenv("SOURCE_DATE_EPOCH")
    if value:
        timestamp = datetime.fromtimestamp(int(value), tz=timezone.utc)
    else:
        timestamp = datetime.now(timezone.utc)
    return timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def derive_release_metadata(
    *,
    repository_root: Path = REPOSITORY_ROOT,
    source_date_epoch: str | None = None,
) -> dict[str, str]:
    """Return metadata for the exact checked-out commit."""
    full_revision = _git("rev-parse", "HEAD", repository_root=repository_root)
    short_revision = _git("rev-parse", "--short=9", "HEAD", repository_root=repository_root)
    if not full_revision.startswith(short_revision):
        raise RuntimeError("Git short revision is not a prefix of the full revision")
    return {
        "SENTINEL_DNA_IMAGE_TAG": full_revision,
        "SENTINEL_DNA_IMAGE_REVISION": short_revision,
        "SENTINEL_DNA_IMAGE_REVISION_FULL": full_revision,
        "SENTINEL_DNA_IMAGE_CREATED": _created_at(source_date_epoch),
    }


def format_metadata(metadata: Mapping[str, str], output_format: str) -> str:
    """Format nonsecret metadata for a shell, dotenv file, JSON, or GHA."""
    values = {name: str(metadata[name]) for name in METADATA_NAMES}
    if output_format == "json":
        return json.dumps(values, sort_keys=True)
    if output_format == "shell":
        return "\n".join(f"export {name}={shlex.quote(values[name])}" for name in METADATA_NAMES)
    if output_format in {"dotenv", "github-env"}:
        return "\n".join(f"{name}={values[name]}" for name in METADATA_NAMES)
    raise ValueError(f"unsupported output format: {output_format}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("dotenv", "github-env", "json", "shell"), default="dotenv")
    parser.add_argument("--source-date-epoch")
    args = parser.parse_args()
    print(format_metadata(derive_release_metadata(source_date_epoch=args.source_date_epoch), args.format))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
