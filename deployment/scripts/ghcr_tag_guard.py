#!/usr/bin/env python3
"""Fail-closed guard for immutable GHCR candidate tags.

The GitHub Packages API is used instead of interpreting Docker CLI error text.
A candidate is considered absent only after every package-version page is read
successfully. API/auth/network errors never count as absence.
"""
from __future__ import annotations

import argparse
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


def candidate_tag_exists(versions: list[dict], tag: str) -> bool:
    for version in versions:
        metadata = version.get("metadata")
        if not isinstance(metadata, dict):
            continue
        container = metadata.get("container")
        if not isinstance(container, dict):
            continue
        tags = container.get("tags")
        if isinstance(tags, list) and tag in tags:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--tag", required=True)
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
    except ProbeError as exc:
        print(f"candidate tag probe inconclusive: {exc}; refusing to publish", file=sys.stderr)
        return 2

    if candidate_tag_exists(versions, args.tag):
        print("candidate GHCR tag already exists; refusing to overwrite", file=sys.stderr)
        return 1

    print(f"candidate tag absence confirmed by GitHub Packages API ({len(versions)} versions checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
