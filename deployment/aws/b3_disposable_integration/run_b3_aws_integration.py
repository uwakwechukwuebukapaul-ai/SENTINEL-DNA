"""Entry point for the disposable B3 AWS integration harness.

Safe default: without explicit disposable-account configuration this performs
no AWS calls and reports that live execution is pending.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .evidence import canonical_evidence, new_evidence
from .resource_manager import ResourceManager
from .safety import SafetyError, load_config, verify_caller_account


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run B3 integration only in an explicitly disposable AWS account")
    parser.add_argument("--evidence", type=Path, help="write secret-free evidence JSON")
    parser.add_argument("--plan", action="store_true", help="validate gates and print the planned resource set")
    args = parser.parse_args(argv)
    try:
        config = load_config()
    except SafetyError as exc:
        print(json.dumps({"status": "IMPLEMENTED_LIVE_AWS_EXECUTION_PENDING_DISPOSABLE_ACCOUNT", "reason": str(exc)}))
        return 0

    try:
        import boto3
        session = boto3.Session(region_name=config.region)
        identity = verify_caller_account(session.client("sts"), config)
    except SafetyError as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}))
        return 2
    except Exception as exc:  # noqa: BLE001 - safe type-only diagnostic
        print(json.dumps({"status": "REFUSED", "reason": type(exc).__name__}))
        return 2

    evidence = new_evidence(config.run_id, config.account_id, config.region)
    evidence["caller"] = identity
    evidence["resource_names"] = config.names
    evidence["provider_deployment"] = "PENDING_REVIEWED_DISPOSABLE_PROVIDER_BUILD"
    evidence["status"] = "PENDING"
    evidence["reason"] = (
        "The reviewed provider source is pinned to the existing Trust resource graph; "
        "a disposable provider build/deployment is required before live custody tests."
    )
    if args.plan:
        print(json.dumps({"status": "PENDING", "account": config.account_id, "region": config.region, "resources": config.names}, sort_keys=True))
    if args.evidence:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_bytes(canonical_evidence(evidence))
    return 0


if __name__ == "__main__":
    sys.exit(main())

