"""Collect bounded operational-readiness evidence without performing operations."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deployment.validation.ownership import OperationalOwnershipEvidenceValidator
from deployment.validation.postgres_rehearsal import PostgresRehearsalValidator
from deployment.validation.release_hygiene import ReleaseHygieneValidator
from deployment.validation.runtime_readiness import RuntimeReadinessValidator


ARTIFACT_VERSION = "sentinel-dna-operational-evidence-collection.v1"
REPLAY_VERSION = "sentinel-dna-operational-evidence-collection-replay.v1"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Any) -> str:
    return hashlib.sha256((_canonical(value) + "\n").encode("utf-8")).hexdigest()


def _as_dict(report: Any) -> dict[str, Any]:
    if isinstance(report, dict):
        return dict(report)
    return dict(report.to_dict())


def collect(*, repository_root: Path, output: Path, generated_at: str, artifact_paths: tuple[Path, ...]) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite append-only artifact: {output}")

    reports = {
        "postgres_rehearsal": _as_dict(
            PostgresRehearsalValidator(repository_root=repository_root, generated_at=generated_at).run()
        ),
        "runtime_readiness": _as_dict(
            RuntimeReadinessValidator(repository_root=repository_root, environ={}, generated_at=generated_at).run()
        ),
        "operational_ownership": _as_dict(
            OperationalOwnershipEvidenceValidator(repository_root=repository_root, generated_at=generated_at).run()
        ),
        "release_hygiene": _as_dict(
            ReleaseHygieneValidator(
                repository_root=repository_root,
                artifact_paths=artifact_paths,
                generated_at=generated_at,
            ).run()
        ),
    }
    replay = _digest(
        {
            "replay_version": REPLAY_VERSION,
            "sources": [
                {"source": name, "status": reports[name].get("validation_result"), "replay_digest": reports[name].get("replay_digest")}
                for name in sorted(reports)
            ],
        }
    )
    body = {
        "artifact_version": ARTIFACT_VERSION,
        "generated_at": generated_at,
        "immutable": True,
        "collection_mode": "bounded_offline_evidence_only",
        "production_database_touched": False,
        "external_connections_used": False,
        "production_deployment_performed": False,
        "secrets_serialized": False,
        "evidence_sources": reports,
        "replay_digest": replay,
    }
    artifact = {**body, "artifact_digest": _digest(body)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--generated-at", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--artifact", action="append", type=Path, default=[])
    args = parser.parse_args()
    artifact = collect(
        repository_root=args.repository_root.resolve(),
        output=args.output.resolve(),
        generated_at=args.generated_at,
        artifact_paths=tuple(path.resolve() for path in args.artifact),
    )
    print(json.dumps({
        "artifact": str(args.output.resolve()),
        "artifact_digest": artifact["artifact_digest"],
        "replay_digest": artifact["replay_digest"],
        "statuses": {name: value.get("validation_result") for name, value in sorted(artifact["evidence_sources"].items())},
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
