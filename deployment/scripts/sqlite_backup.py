"""Create, validate, or restore a non-secret SQLite recovery artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from deployment.disaster_recovery.sqlite_backup import SQLiteBackupService


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _path(value: str) -> Path:
    return Path(value).expanduser()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup = subparsers.add_parser("backup")
    backup.add_argument("--source", type=_path, required=True)
    backup.add_argument("--artifact", type=_path, required=True)
    backup.add_argument("--manifest", type=_path, required=True)
    backup.add_argument("--commit", default=None)
    backup.add_argument("--tree", default=None)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--artifact", type=_path, required=True)
    validate.add_argument("--manifest", type=_path, required=True)

    restore = subparsers.add_parser("restore")
    restore.add_argument("--artifact", type=_path, required=True)
    restore.add_argument("--manifest", type=_path, required=True)
    restore.add_argument("--target", type=_path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    service = SQLiteBackupService()
    if args.command == "backup":
        result = service.backup(
            args.source,
            args.artifact,
            args.manifest,
            source_commit=args.commit or _git("rev-parse", "HEAD"),
            source_tree=args.tree or _git("show", "-s", "--format=%T", "HEAD"),
        ).manifest
    elif args.command == "validate":
        result = service.validate(args.artifact, args.manifest)
    else:
        restored = service.restore(args.artifact, args.manifest, args.target)
        result = {
            "manifest": restored.manifest,
            "restored_database": restored.restored_database,
            "integrity_check": restored.integrity_check,
            "table_counts": restored.table_counts,
            "elapsed_seconds": restored.elapsed_seconds,
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
