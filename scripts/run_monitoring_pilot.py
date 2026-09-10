"""Run the bounded founder-operated synthetic monitoring pilot."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.monitoring.pilot import SyntheticMonitoringPilot, write_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("pilot-evidence/MONITOR-PILOT-001.json"))
    parser.add_argument("--checksums", type=Path)
    args = parser.parse_args()
    try:
        evidence = SyntheticMonitoringPilot().run()
        target, checksums, digest = write_evidence(evidence, args.output, args.checksums)
    except Exception as exc:
        print(json.dumps({"validation_result": "FAIL", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps({
        "validation_result": evidence["validation_result"],
        "event_id": evidence["event_id"],
        "evidence_path": str(target),
        "checksums_path": str(checksums),
        "sha256": digest,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
