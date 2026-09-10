"""Generate the offline operational cyber memory validation report."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.intelligence.memory.validation import OperationalCyberMemoryValidator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional path for the auditable JSON report")
    args = parser.parse_args()
    report = OperationalCyberMemoryValidator().run()
    if args.output:
        report.write(args.output)
    print(report.to_json(), end="")
    return 0 if report.validation_result == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
