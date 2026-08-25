"""Generate the Sentinel DNA enterprise trust closure report."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.intelligence.trust import EnterpriseTrustClosureRunner, TrustClosureReportGenerator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--generated-at")
    parser.add_argument("--commit-sha")
    args = parser.parse_args()
    runner = EnterpriseTrustClosureRunner(generated_at=args.generated_at, commit_sha=args.commit_sha)
    report = runner.run()
    replay = runner.run()
    if not runner.verify_replay(report, replay):
        return 1
    if args.output:
        TrustClosureReportGenerator.write(report, args.output)
    print(report.to_json(), end="")
    return 0 if not report.production_blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
