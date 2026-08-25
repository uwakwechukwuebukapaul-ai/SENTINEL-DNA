"""Generate the Sentinel DNA enterprise proof validation report."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.intelligence.enterprise_proof import EnterpriseProofReportGenerator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    generator = EnterpriseProofReportGenerator()
    report = generator.generate()
    if args.output:
        generator.write(report, args.output)
    print(report.to_json(), end="")
    return 0 if all(report.safety_validation.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
