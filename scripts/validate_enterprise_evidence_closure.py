"""Generate the immutable Sentinel DNA enterprise evidence closure artifact."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.intelligence.certification.evidence_closure import (
    EnterpriseEvidenceClosureRunner,
    EvidenceClosureReportGenerator,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--generated-at")
    parser.add_argument("--commit-sha")
    args = parser.parse_args()
    runner = EnterpriseEvidenceClosureRunner(generated_at=args.generated_at, commit_sha=args.commit_sha)
    report = runner.run()
    replay = runner.run()
    if not runner.verify_replay(report, replay):
        return 1
    if args.output:
        EvidenceClosureReportGenerator.write(report, args.output)
    print(report.to_json(), end="")
    return 0 if report.closure_result == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
