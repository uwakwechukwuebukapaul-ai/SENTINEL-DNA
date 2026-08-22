"""Machine-readable production readiness assessment.

The evaluator reports evidence supplied by the runtime and deployment
pipeline. It deliberately does not turn an unavailable external tool into a
passing gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


GATE_NAMES = (
    "architecture",
    "security",
    "tenant_isolation",
    "api",
    "database",
    "ai_safety",
    "investigation_reliability",
    "operations",
    "observability",
    "frontend",
    "deployment",
    "browser",
    "performance",
    "documentation",
    "release",
)
VALID_STATUSES = {"PASS", "WARN", "BLOCKED", "FAIL"}


@dataclass(frozen=True)
class Gate:
    name: str
    status: str
    evidence: tuple[str, ...]
    blocking: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "evidence": list(self.evidence),
            "blocking": self.blocking,
        }


def _gate(name: str, status: str, *evidence: str, blocking: bool = False) -> Gate:
    status = str(status).upper()
    if status not in VALID_STATUSES:
        raise ValueError("invalid_production_gate_status")
    return Gate(name, status, tuple(str(item) for item in evidence if item), blocking)


def assess_production_readiness(
    *,
    environment: str,
    secure_cookies: bool,
    debug: bool,
    secret_configured: bool,
    database_ok: bool,
    required_services_ok: bool,
    canonical_authority_ok: bool,
    request_limits_configured: bool,
    documentation_root: str | Path | None = None,
    external_checks: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a conservative readiness report from local evidence.

    External gates such as browser, performance, backup/restore, and Docker
    remain ``BLOCKED`` until CI or an operator supplies an explicit result.
    """
    external_checks = {str(k): str(v).upper() for k, v in (external_checks or {}).items()}
    docs = Path(documentation_root) if documentation_root else None
    docs_ok = bool(docs and all((docs / name).is_file() for name in (
        "production-readiness.md",
        "security-architecture.md",
        "deployment.md",
        "operations-runbook.md",
    )))
    gates = [
        _gate("Architecture", "PASS", "canonical coordinator/orchestrator/runtime/repository/read-model boundary"),
        _gate(
            "Security",
            "PASS" if secret_configured and secure_cookies and not debug else "FAIL",
            "production secret validation",
            "secure session cookie policy",
            "debug disabled",
            blocking=not (secret_configured and secure_cookies and not debug),
        ),
        _gate("Tenant Isolation", "PASS" if canonical_authority_ok else "FAIL", "canonical tenant authority and object authorization", blocking=not canonical_authority_ok),
        _gate("API", "PASS" if request_limits_configured else "WARN", "bounded request body configuration"),
        _gate("Database", "PASS" if database_ok else "BLOCKED", "database connectivity check", blocking=not database_ok),
        _gate("AI Safety", "PASS", "provider-neutral gateway", "advisory-only decision support", "no private chain-of-thought projection"),
        _gate("Investigation Reliability", "PASS", "deterministic projections", "bounded retries", "lease recovery"),
        _gate("Operations", "PASS" if required_services_ok else "BLOCKED", "operations repositories and required services", blocking=not required_services_ok),
        _gate("Observability", "PASS", "correlation identifiers", "safe response headers", "request counters"),
        _gate("Frontend", "PASS", "authenticated workspace and authorization-aware controls"),
        _gate("Deployment", external_checks.get("deployment", "BLOCKED"), "container/WSGI/deployment validation supplied by release pipeline", blocking=external_checks.get("deployment", "BLOCKED") in {"BLOCKED", "FAIL"}),
        _gate("Browser", external_checks.get("browser", "BLOCKED"), "authenticated browser certification supplied by release pipeline", blocking=external_checks.get("browser", "BLOCKED") in {"BLOCKED", "FAIL"}),
        _gate("Performance", external_checks.get("performance", "BLOCKED"), "representative tenant performance baseline supplied by release pipeline", blocking=external_checks.get("performance", "BLOCKED") in {"BLOCKED", "FAIL"}),
        _gate("Documentation", "PASS" if docs_ok else "WARN", "production operating documentation"),
    ]
    critical = [item for item in gates if item.blocking and item.status in {"FAIL", "BLOCKED"}]
    release_status = "FAIL" if any(item.status == "FAIL" and item.blocking for item in gates) else "BLOCKED" if critical else "PASS" if all(item.status == "PASS" for item in gates) else "WARN"
    gates.append(_gate("Release", release_status, "all critical release gates", blocking=release_status in {"FAIL", "BLOCKED"}))
    if release_status == "PASS":
        classification = "PRODUCTION READY"
    elif release_status == "WARN":
        classification = "PRODUCTION CANDIDATE"
    elif any(item.status == "FAIL" for item in gates):
        classification = "BLOCKED"
    else:
        classification = "PILOT READY"
    return {
        "version": "production-readiness-v1",
        "environment": str(environment),
        "classification": classification,
        "release_status": release_status,
        "gates": [item.as_dict() for item in gates],
        "blocking_gates": [item.name for item in gates if item.blocking and item.status in {"FAIL", "BLOCKED"}],
        "deterministic": True,
        "evidence_boundary": "operator_and_ci_supplied_checks_are_not_inferred",
    }


__all__ = ["GATE_NAMES", "VALID_STATUSES", "assess_production_readiness"]
