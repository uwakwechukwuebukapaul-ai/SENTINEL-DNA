"""Generate an offline benchmark report for investigation telemetry."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.intelligence.telemetry import run_performance_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--stage-delay-ms", type=float, default=0.05)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_performance_benchmark(
        iterations=args.iterations,
        synthetic_stage_delay_ms=args.stage_delay_ms,
    )
    if args.output:
        report.write(args.output)
    print(report.to_json(), end="")
    return 0 if all(report.control_checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
