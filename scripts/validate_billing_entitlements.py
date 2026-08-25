"""Generate the offline billing entitlement operational validation report."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.billing.validation import BillingEvidenceReportGenerator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Immutable report path outside the repository")
    parser.add_argument("--generated-at", help="Fixed ISO timestamp for reproducible report fixtures")
    args = parser.parse_args()
    repository_root = Path(__file__).resolve().parents[1]
    report = BillingEvidenceReportGenerator.generate(generated_at=args.generated_at)
    if args.output:
        BillingEvidenceReportGenerator.write(report, args.output, repository_root=repository_root)
    print(report.to_json(), end="")
    return 0 if report.validation_result == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
