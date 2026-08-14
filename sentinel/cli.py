from __future__ import annotations
import argparse
import json
from customer_zero.scenarios.catalog import SCENARIOS
from customer_zero.simulator.investigation_runner import CustomerZeroInvestigationRunner

def main() -> None:
    parser = argparse.ArgumentParser(prog="sentinel")
    commands = parser.add_subparsers(dest="command", required=True)
    investigate = commands.add_parser("investigate")
    investigate.add_argument("--scenario", choices=tuple(SCENARIOS), required=True)
    args = parser.parse_args()
    if args.command == "investigate":
        print(json.dumps(CustomerZeroInvestigationRunner().investigate(args.scenario), indent=2, default=str))
