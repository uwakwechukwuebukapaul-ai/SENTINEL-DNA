"""Run the offline, evidence-only deployment contract validator."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from deployment.validation.contract import DeploymentContractValidator, write_immutable_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--release-manifest", type=Path)
    parser.add_argument("--backup-source", type=Path, help="Read-only source database used for isolated backup creation rehearsal")
    parser.add_argument("--backup-artifact", type=Path)
    parser.add_argument("--backup-manifest", type=Path)
    parser.add_argument("--backup-restored", type=Path, help="Read-only restored database evidence; defaults to release-scoped restore-test/restored.db")
    parser.add_argument("--output", type=Path, help="Immutable report path outside the repository")
    args = parser.parse_args()
    validator = DeploymentContractValidator(
        repository_root=args.repository_root,
        env_file=args.env_file,
        release_manifest=args.release_manifest,
        backup_source=args.backup_source,
        backup_artifact=args.backup_artifact,
        backup_manifest=args.backup_manifest,
        backup_restored=args.backup_restored,
    )
    report = validator.run()
    if args.output:
        write_immutable_report(report, args.output, repository_root=args.repository_root)
    print(report.to_json(), end="")
    return 0 if report.validation_result == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
