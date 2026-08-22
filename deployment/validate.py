"""Backward-compatible deployment validation adapter.

The richer gate report lives in ``deployment.production.readiness``. This
adapter retains the historic boolean keys for existing CI consumers.
"""
from __future__ import annotations

import json

from deployment.production.readiness import build_report


def validate(checks=None):
    checks = checks or {}
    report = build_report()
    return {
        "docker": bool(checks.get("docker", False)),
        "postgresql": bool(checks.get("postgresql", False)),
        "redis": bool(checks.get("redis", False)),
        "workers": bool(checks.get("workers", False)),
        "migrations": bool(checks.get("migrations", False)),
        "backup": bool(checks.get("backup", False)),
        "health_endpoints": report["release_status"] not in {"FAIL", "BLOCKED"},
        "production_readiness": report,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2, sort_keys=True))
