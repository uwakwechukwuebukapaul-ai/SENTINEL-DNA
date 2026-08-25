"""Run the Sentinel DNA controlled operational pilot validation."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.intelligence.pilot import OperationalPilotReportGenerator, OperationalPilotRunner


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--generated-at")
    args = parser.parse_args()
    runner = OperationalPilotRunner(generated_at=args.generated_at)
    report = runner.run()
    replay = runner.run()
    if not runner.verify_replay(report, replay):
        return 1
    if args.output:
        OperationalPilotReportGenerator.write(report, args.output)
    print(report.to_json(), end="")
    return 0 if all(report.safety_validation.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
