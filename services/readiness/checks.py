from __future__ import annotations
import os
from typing import Any, Callable
from .models import ReadinessCheck
CHECK_DEFINITIONS = [("database_connectivity", "infrastructure", "Database connectivity is required."), ("migration_readiness", "infrastructure", "Apply and verify database migrations."), ("redis_availability", "infrastructure", "Configure and verify Redis."), ("worker_status", "infrastructure", "Start healthy background workers."), ("detection_engine", "soc_capabilities", "Register the detection engine."), ("investigation_coordinator", "soc_capabilities", "Register the investigation coordinator."), ("threat_hunting", "soc_capabilities", "Enable threat hunting services."), ("soar", "soc_capabilities", "Enable SOAR response services."), ("ai_reasoning", "soc_capabilities", "Enable AI reasoning services."), ("copilot", "soc_capabilities", "Enable Copilot services."), ("authentication", "security", "Enable authentication."), ("rbac", "security", "Enable RBAC enforcement."), ("csrf", "security", "Enable CSRF protection."), ("audit_logging", "security", "Enable audit logging."), ("tenant_isolation", "security", "Enable tenant isolation."), ("evidence_integrity", "security", "Enable evidence hashing and custody."), ("environment", "deployment", "Set a deployment environment."), ("version", "deployment", "Set an application version."), ("startup_timestamp", "deployment", "Record application startup time.")]
def default_checks(config: dict[str, Any] | None = None, service_lookup: Callable[[str], Any] | None = None) -> list[ReadinessCheck]:
    config = config or {}; service_lookup = service_lookup or (lambda name: None); results = []
    for name, category, recommendation in CHECK_DEFINITIONS:
        if name == "environment": value = bool(config.get("ENVIRONMENT") or os.getenv("SENTINEL_ENVIRONMENT"))
        elif name == "version": value = bool(config.get("VERSION") or os.getenv("SENTINEL_VERSION"))
        elif name == "startup_timestamp": value = bool(config.get("STARTUP_TIMESTAMP"))
        else: value = service_lookup(name) is not None or bool(config.get(name.upper()))
        results.append(ReadinessCheck(name, category, value, "available" if value else "not available", "" if value else recommendation))
    return results
