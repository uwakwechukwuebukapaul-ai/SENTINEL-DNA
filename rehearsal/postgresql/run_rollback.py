"""CLI wrapper for the guarded disposable PostgreSQL rollback rehearsal."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from database.backend import PostgreSQLBackend  # noqa: E402

try:  # noqa: E402 - supports direct operator invocation
    from .common import digest, report_metadata, require_authorized_url, write_report
    from .rollback import run_rollback
except ImportError:  # pragma: no cover - direct operator invocation
    from common import digest, report_metadata, require_authorized_url, write_report
    from rollback import run_rollback


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        url = require_authorized_url()
    except RuntimeError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    backend = PostgreSQLBackend(url, connect_timeout=5)
    report = {"report_version": "sentinel-dna-postgresql-rollback.v1", **run_rollback(backend), **report_metadata(REPO_ROOT)}
    report["replay_digest"] = digest({key: value for key, value in report.items() if key != "generated_at"})
    if args.output:
        write_report(report, args.output, REPO_ROOT)
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
