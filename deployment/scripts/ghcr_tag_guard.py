#!/usr/bin/env python3
"""Fail-closed guard for immutable GHCR candidate tags.

The GitHub Packages API is used instead of interpreting Docker CLI error text.
A candidate is considered absent only after every package-version page is read
successfully. API/auth/network errors never count as absence.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


PAGE_SIZE = 100
IMAGE_PATTERN = re.compile(r"^ghcr\.io/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$")
TAG_PATTERN = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")


class ProbeError(RuntimeError):
    """The package API could not conclusively establish tag absence."""


def package_versions(image: str, token: str, api_url: str) -> list[dict]:
    match = IMAGE_PATTERN.fullmatch(image)
    if not match:
        raise ProbeError("image must be ghcr.io/<owner>/<package>")
    owner, package = match.groups()
    endpoint = (
        f"{api_url.rstrip('/')}/users/{quote(owner, safe='')}/packages/container/"
        f"{quote(package, safe='')}/versions"
    )
    versions: list[dict] = []
    page = 1

    while True:
        request = Request(
            f"{endpoint}?per_page={PAGE_SIZE}&page={page}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "sentinel-dna-release-guard",
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ProbeError(
                f"GitHub Packages API returned HTTP {exc.code}; package visibility "
                "or read permission may be insufficient"
            ) from None
        except (URLError, TimeoutError, OSError) as exc:
            # Avoid dumping exception objects: they can include request details.
            reason = "network or timeout error"
            if isinstance(exc, URLError) and isinstance(exc.reason, TimeoutError):
                reason = "network timeout"
            raise ProbeError(f"GitHub Packages API request failed ({reason})") from None
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ProbeError("GitHub Packages API returned invalid JSON") from None

        if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
            raise ProbeError("GitHub Packages API response shape was unexpected")
        versions.extend(payload)
        if len(payload) < PAGE_SIZE:
            return versions
        page += 1


def _parse_timestamp(value: object, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ProbeError(f"GitHub Packages API {field} metadata is missing or malformed")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ProbeError(f"GitHub Packages API {field} metadata is missing or malformed") from exc


def candidate_tag_version(versions: list[dict], tag: str) -> dict | None:
    matches = []
    for version in versions:
        if not isinstance(version, dict):
            raise ProbeError("GitHub Packages API version response was unexpected")
        if type(version.get("id")) is not int or version["id"] <= 0:
            raise ProbeError("GitHub Packages API version identity is incomplete")
        _parse_timestamp(version.get("created_at"), field="created_at")
        metadata = version.get("metadata")
        if not isinstance(metadata, dict) or not isinstance(metadata.get("container"), dict):
            raise ProbeError("GitHub Packages API container provenance is incomplete")
        container = metadata["container"]
        tags = container.get("tags")
        if not isinstance(tags, list) or any(not isinstance(value, str) for value in tags):
            raise ProbeError("GitHub Packages API container tags are incomplete")
        if tag in tags:
            matches.append(version)
    if len(matches) > 1:
        raise ProbeError("candidate tag is associated with multiple package versions")
    return matches[0] if matches else None


def candidate_tag_exists(versions: list[dict], tag: str) -> bool:
    """Compatibility helper: incomplete package data is an error, never absence."""
    return candidate_tag_version(versions, tag) is not None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--github-output", required=True)
    args = parser.parse_args()

    if not TAG_PATTERN.fullmatch(args.tag):
        print("candidate tag is malformed; refusing to continue", file=sys.stderr)
        return 2

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("GITHUB_TOKEN is missing; cannot prove candidate tag absence", file=sys.stderr)
        return 2

    try:
        versions = package_versions(
            args.image,
            token,
            os.environ.get("GITHUB_API_URL", "https://api.github.com"),
        )
        version = candidate_tag_version(versions, args.tag)
    except ProbeError as exc:
        print(f"candidate tag probe inconclusive: {exc}; refusing to publish", file=sys.stderr)
        return 2

    with open(args.github_output, "a", encoding="utf-8") as output:
        output.write(f"candidate_state={'present' if version else 'absent'}\n")
        if version is not None:
            output.write(f"package_version_id={version['id']}\n")
            output.write(f"package_created_at={version['created_at']}\n")

    if version is None:
        print(f"candidate tag absence confirmed by GitHub Packages API ({len(versions)} versions checked)")
    else:
        print("candidate tag exists; recovery verification is required before reuse")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
