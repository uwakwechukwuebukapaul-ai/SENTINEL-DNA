"""Fail-closed validation for protected production deployment configuration.

Only variable names and validation categories are reported. Secret values are
read in memory and are never printed, serialized, or included in exceptions.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Mapping

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
    for name in METADATA_NAMES:
        value = values.get(name, "").strip()
        if not value:
            errors.append(f"{name}:missing")
        elif name != "SENTINEL_DNA_IMAGE_CREATED" and value != expected[name]:
            errors.append(f"{name}:does-not-match-HEAD")
        elif name == "SENTINEL_DNA_IMAGE_CREATED":
            try:
                created = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{name}:invalid-ISO-8601")
            else:
                if created.tzinfo is None or not value.endswith("Z"):
                    errors.append(f"{name}:must-be-UTC")

    if values.get("SENTINEL_DNA_ENV", "production").lower() != "production":
        errors.append("SENTINEL_DNA_ENV:must-be-production")
    if values.get("SENTINEL_DNA_SECURE_COOKIES", "1") != "1":
        errors.append("SENTINEL_DNA_SECURE_COOKIES:must-be-enabled")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    errors = validate_configuration(env_file=args.env_file)
    if errors:
        print("Deployment configuration invalid: " + ", ".join(errors))
        return 1
    print("Deployment configuration valid: protected variables present; release metadata matches HEAD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
