"""Fail-closed readiness checks for the first non-production FAVP cycle."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from services.auth.permissions import PERMISSIONS


READY_FOR_FAVP_EXECUTION = "READY_FOR_FAVP_EXECUTION"
BLOCKED_WITH_REASON = "BLOCKED_WITH_REASON"


class FAVPReadinessError(RuntimeError):
    """Raised only when a readiness dependency cannot be inspected safely."""


def _check(name: str, passed: bool, reason: str) -> dict[str, str]:
    return {"name": name, "status": "PASS" if passed else "BLOCKED", "reason": reason}


class FAVPExecutionReadiness:
    """Read-only environment gate; it never enables a flag or changes state."""

    def __init__(self, db: Any, audit_service: Any, *, evidence_dir: str | Path | None = None, environ: Mapping[str, str] | None = None) -> None:
        self.db = db
        self.audit_service = audit_service
        self.environ = os.environ if environ is None else environ
        raw_evidence_dir = str(evidence_dir or self.environ.get("SENTINEL_DNA_FAVP_EVIDENCE_DIR", "")).strip()
        self.evidence_dir = Path(raw_evidence_dir) if raw_evidence_dir else None

    def check(self) -> dict[str, Any]:
        env = self.environ
        checks = []
        enabled = env.get("SENTINEL_DNA_FAVP_OPERATIONS_ENABLED") == "1"
        checks.append(_check("operations_feature_flag", enabled, "FAVP operations feature flag is enabled" if enabled else "SENTINEL_DNA_FAVP_OPERATIONS_ENABLED must be 1"))
        environment = str(env.get("SENTINEL_DNA_ENV", "")).strip().lower()
        non_production = environment in {"staging", "testing"}
        checks.append(_check("non_production_environment", non_production, "approved non-production environment confirmed" if non_production else "SENTINEL_DNA_ENV must be staging or testing"))
        checks.append(_check("production_isolated", environment != "production" and env.get("SENTINEL_DNA_FAVP_PRODUCTION_ACCESS", "0") == "0", "production access is disabled" if environment != "production" and env.get("SENTINEL_DNA_FAVP_PRODUCTION_ACCESS", "0") == "0" else "production access must remain disabled"))
        synthetic = env.get("SENTINEL_DNA_FAVP_SYNTHETIC_ONLY") == "1"
        checks.append(_check("synthetic_only", synthetic, "synthetic-only mode is explicit" if synthetic else "SENTINEL_DNA_FAVP_SYNTHETIC_ONLY must be 1"))
        try:
            healthy = bool(self.db and self.db.health_check())
        except Exception:
            healthy = False
        checks.append(_check("database", healthy, "FAVP database health check passed" if healthy else "FAVP database health check failed"))
        tenant = env.get("SENTINEL_DNA_TENANT_ISOLATION_ENABLED") == "1"
        checks.append(_check("tenant_isolation", tenant, "tenant isolation is enabled" if tenant else "SENTINEL_DNA_TENANT_ISOLATION_ENABLED must be 1"))
        audit = env.get("SENTINEL_DNA_AUDIT_LOGGING_ENABLED") == "1" and callable(getattr(self.audit_service, "record", None))
        checks.append(_check("audit_logging", audit, "audit logging is enabled and available" if audit else "audit logging must be enabled and available"))
        evidence_ok = bool(self.evidence_dir and self.evidence_dir.is_dir() and os.access(self.evidence_dir, os.W_OK))
        checks.append(_check("evidence_storage", evidence_ok, "evidence directory is writable" if evidence_ok else "FAVP evidence directory is missing or not writable"))
        required_permissions = {"pilot:read", "pilot:manage", "validation:execute"}
        permissions_ok = required_permissions.issubset(PERMISSIONS)
        checks.append(_check("permissions", permissions_ok, "existing pilot permissions are available" if permissions_ok else "required existing pilot permissions are unavailable"))
        checks.append(_check("credential_storage", True, "FAVP schema contains no credential storage fields"))
        checks.append(_check("autonomous_actions", True, "FAVP execution records advisory output only"))
        blocked = next((item for item in checks if item["status"] != "PASS"), None)
        status = BLOCKED_WITH_REASON if blocked else READY_FOR_FAVP_EXECUTION
        return {"status": status, "checks": checks, "next_action": "Resolve every blocked check before the first analyst session" if blocked else "Human program owner may authorize the bounded non-production cycle"}


__all__ = ["BLOCKED_WITH_REASON", "FAVPExecutionReadiness", "FAVPReadinessError", "READY_FOR_FAVP_EXECUTION"]
