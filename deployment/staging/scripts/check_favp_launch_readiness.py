"""Operator command for the non-production FAVP staging launch gate.

The command is fail-closed and never enables FAVP, provisions an analyst, or
changes production configuration. It may initialize the already-authorized
FAVP schema when the explicit staging flag is enabled, matching application
startup behavior.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.connection import database_for_environment  # noqa: E402
from services.audit.service import AuditService  # noqa: E402
from services.favp_operations import (  # noqa: E402
    FAVPOperationsRepository,
    FAVPOperationsService,
    FAVPExecutionService,
    FAVPStagingLaunchReadiness,
)


def build_readiness(*, compose_path: Path | None = None, evidence_dir: Path | None = None):
    db = None
    audit = None
    execution = None
    try:
        db = database_for_environment(require_postgresql=True)
    except Exception:
        # The checker returns safe blocked categories; database URLs and
        # driver exceptions must never cross the operator output boundary.
        db = None

    flag_enabled = os.getenv("SENTINEL_DNA_FAVP_OPERATIONS_ENABLED") == "1"
    if db is not None and flag_enabled:
        try:
            audit = AuditService(db)
            operations = FAVPOperationsService(FAVPOperationsRepository(db), audit)
            execution = FAVPExecutionService(operations, audit)
        except Exception:
            audit = None
            execution = None

    checker = FAVPStagingLaunchReadiness(
        db,
        audit,
        execution,
        evidence_dir=evidence_dir,
        compose_path=compose_path,
    )
    return checker.check()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the non-production FAVP staging launch boundary")
    parser.add_argument("--compose-file", type=Path, default=ROOT / "deployment" / "staging" / "docker-compose.yml")
    parser.add_argument("--evidence-dir", type=Path, default=None)
    parser.add_argument("--pretty", action="store_true", help="format the JSON dashboard for operators")
    args = parser.parse_args()
    result = build_readiness(compose_path=args.compose_file, evidence_dir=args.evidence_dir)
    import json
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["status"] == "FAVP_STAGING_LAUNCH_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
