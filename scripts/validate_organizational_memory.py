"""Generate the deterministic organizational cyber memory validation report."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.intelligence.memory import OrganizationalMemoryValidator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = OrganizationalMemoryValidator().run()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report.to_json(), encoding="utf-8")
    print(report.to_json(), end="")
    return 0 if report.validation_result == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
