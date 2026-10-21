#!/usr/bin/env python3
"""Verify a GHCR candidate by immutable digest and emit non-secret evidence."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if __name__ == "__main__" and str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


EXPECTED_SOURCE = "https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA"
IMAGE_NAME = "ghcr.io/uwakwechukwuebukapaul-ai/sentinel-dna"
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
CREATED_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
EXPECTED_COMMAND = [
    "gunicorn",
    "wsgi:application",
    "--bind",
    "0.0.0.0:5000",
    "--workers",
    "1",
    "--access-logfile",
    "-",
    "--error-logfile",
    "-",
]


class CandidateVerificationError(RuntimeError):
    """The registry artifact cannot be proven to be the authorized candidate."""


def _created(value: object, *, name: str) -> datetime:
    if not isinstance(value, str) or not CREATED_RE.fullmatch(value):
        raise CandidateVerificationError(f"{name} is missing or malformed")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise CandidateVerificationError(f"{name} is missing or malformed") from exc


def resolve_manifest_digest(manifest: dict[str, Any], expected_digest: str) -> str:
    """Return a registry manifest digest only when it matches the expected value."""
    if not isinstance(manifest, dict):
        raise CandidateVerificationError("registry manifest metadata is incomplete")
    observed = manifest.get("digest")
    if not isinstance(observed, str) or not DIGEST_RE.fullmatch(observed):
        raise CandidateVerificationError("registry manifest digest is missing or malformed")
    if not isinstance(expected_digest, str) or not DIGEST_RE.fullmatch(expected_digest):
        raise CandidateVerificationError("authorized candidate digest is missing or malformed")
    if observed != expected_digest:
        raise CandidateVerificationError("registry digest does not match the authorized candidate")
    return observed


def verify_runtime_configuration(config: object, *, revision: str, image_version: str, image_created: str) -> dict[str, Any]:
    """Validate OCI identity and the Dockerfile runtime contract before publication."""
    if not isinstance(config, dict):
        raise CandidateVerificationError("candidate runtime configuration is incomplete")
    if not REVISION_RE.fullmatch(revision):
        raise CandidateVerificationError("authorized candidate revision is malformed")
    if not REVISION_RE.fullmatch(image_version) or image_version != revision:
        raise CandidateVerificationError("candidate image version must match the full authorized revision")
    _created(image_created, name="candidate creation metadata")

    labels = config.get("Labels")
    if not isinstance(labels, dict):
        raise CandidateVerificationError("candidate OCI provenance labels are incomplete")
    expected_labels = {
        "org.opencontainers.image.revision": revision,
        "com.sentinel-dna.git.revision.full": revision,
        "org.opencontainers.image.version": image_version,
        "org.opencontainers.image.source": EXPECTED_SOURCE,
        "org.opencontainers.image.created": image_created,
    }
    for key, value in expected_labels.items():
        if labels.get(key) != value:
            raise CandidateVerificationError(f"candidate OCI provenance mismatch: {key}")

    if config.get("User") != "sentinel":
        raise CandidateVerificationError("candidate runtime user does not match the deployment contract")
    if config.get("Cmd") != EXPECTED_COMMAND:
        raise CandidateVerificationError("candidate runtime command does not match the deployment contract")
    if config.get("Entrypoint") not in (None, []):
        raise CandidateVerificationError("candidate runtime entrypoint does not match the deployment contract")
    if config.get("WorkingDir") != "/app":
        raise CandidateVerificationError("candidate runtime working directory does not match the deployment contract")
    if config.get("ExposedPorts") != {"5000/tcp": {}}:
        raise CandidateVerificationError("candidate exposed ports do not match the deployment contract")
    environment = config.get("Env")
    if not isinstance(environment, list):
        raise CandidateVerificationError("candidate runtime environment metadata is incomplete")
    environment_values = {}
    for entry in environment:
        if not isinstance(entry, str) or "=" not in entry:
            raise CandidateVerificationError("candidate runtime environment metadata is malformed")
        key, value = entry.split("=", 1)
        if key in environment_values:
            raise CandidateVerificationError("candidate runtime environment metadata is ambiguous")
        environment_values[key] = value
    expected_environment = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "SENTINEL_DNA_ENV": "__RUNTIME_ENV_REQUIRED__",
    }
    if not environment_values.get("PATH") or any(
        environment_values.get(key) != value for key, value in expected_environment.items()
    ):
        raise CandidateVerificationError("candidate runtime environment does not match the deployment contract")
    if {"SENTINEL_DNA_SECRET_KEY", "POSTGRES_PASSWORD", "DATABASE_URL"}.intersection(environment_values):
        raise CandidateVerificationError("candidate runtime environment contains protected configuration")
    return config


def verify_image_inspect(
    inspect_data: object,
    *,
    digest: str,
    revision: str,
    image_version: str,
    candidate_tree: str,
    image_created: str,
    package_created_at: str,
    package_version_id: int,
) -> dict[str, Any]:
    """Validate the pulled digest's provenance labels and runtime contract."""
    if not DIGEST_RE.fullmatch(digest):
        raise CandidateVerificationError("candidate digest is missing or malformed")
    if not REVISION_RE.fullmatch(revision):
        raise CandidateVerificationError("authorized candidate revision is malformed")
    if not REVISION_RE.fullmatch(candidate_tree):
        raise CandidateVerificationError("authorized candidate tree is malformed")
    created_time = _created(image_created, name="candidate creation metadata")
    package_time = _created(package_created_at, name="package creation metadata")
    if package_time < created_time or (package_time - created_time).total_seconds() > 86400:
        raise CandidateVerificationError("package creation metadata conflicts with image creation metadata")
    if type(package_version_id) is not int or package_version_id <= 0:
        raise CandidateVerificationError("package version provenance is incomplete")

    if isinstance(inspect_data, list):
        if len(inspect_data) != 1:
            raise CandidateVerificationError("digest-pinned image inspection returned an unexpected result count")
        inspect_data = inspect_data[0]
    if not isinstance(inspect_data, dict):
        raise CandidateVerificationError("digest-pinned image inspection is incomplete")

    image_id = inspect_data.get("Id")
    repo_digests = inspect_data.get("RepoDigests")
    config = inspect_data.get("Config")
    if not isinstance(image_id, str) or not DIGEST_RE.fullmatch(image_id):
        raise CandidateVerificationError("candidate image ID is missing or malformed")
    reference = f"{IMAGE_NAME}@{digest}"
    if not isinstance(repo_digests, list) or reference not in repo_digests:
        raise CandidateVerificationError("pulled image does not resolve to the authorized registry digest")
    if not isinstance(config, dict):
        raise CandidateVerificationError("candidate runtime configuration is incomplete")

    verify_runtime_configuration(config, revision=revision, image_version=image_version, image_created=image_created)

    return {
        "candidate_sha": revision,
        "candidate_tree": candidate_tree,
        "registry": "ghcr.io",
        "repository": IMAGE_NAME,
        "image_reference": reference,
        "tag": f"sha-{revision}",
        "immutable_digest": digest,
        "repo_digest": reference,
        "image_id": image_id,
        "package_version_id": package_version_id,
        "package_created_at": package_created_at,
        "oci_revision": revision,
        "oci_source": EXPECTED_SOURCE,
        "oci_created": image_created,
        "runtime_user": config["User"],
        "runtime_working_directory": config["WorkingDir"],
        "entrypoint": config.get("Entrypoint") or [],
        "command": config["Cmd"],
        "exposed_ports": config["ExposedPorts"],
        "verification_status": "PASS",
        "custodian": "GitHub Actions workflow",
        "authorization_status": "workflow-token-scoped",
    }


def write_verified_outputs(evidence: dict[str, Any], *, evidence_path: Path, github_env: Path) -> None:
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with github_env.open("a", encoding="utf-8") as output:
        output.write(f"PUBLISHED_IMAGE_REFERENCE={evidence['image_reference']}\n")
        output.write(f"PUBLISHED_IMAGE_DIGEST={evidence['immutable_digest']}\n")
        output.write(f"PUBLISHED_IMAGE_ID={evidence['image_id']}\n")
        output.write(f"PUBLISHED_IMAGE_CREATED={evidence['oci_created']}\n")
        output.write(f"IMAGE_PROVENANCE_PATH={evidence_path}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspect-json", type=Path, required=True)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--image-version", required=True)
    parser.add_argument("--candidate-tree", required=True)
    parser.add_argument("--image-created", required=True)
    parser.add_argument("--package-created-at", required=True)
    parser.add_argument("--package-version-id", type=int, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--github-env", type=Path, required=True)
    args = parser.parse_args()
    try:
        inspect_data = json.loads(args.inspect_json.read_text(encoding="utf-8"))
        evidence = verify_image_inspect(
            inspect_data,
            digest=args.digest,
            revision=args.revision,
            image_version=args.image_version,
            candidate_tree=args.candidate_tree,
            image_created=args.image_created,
            package_created_at=args.package_created_at,
            package_version_id=args.package_version_id,
        )
        write_verified_outputs(evidence, evidence_path=args.evidence, github_env=args.github_env)
    except (OSError, UnicodeError, json.JSONDecodeError, CandidateVerificationError) as exc:
        print(f"candidate image verification failed: {exc}", file=sys.stderr)
        return 2
    print("candidate image identity and runtime contract verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
