"""Controlled, read-only OIDC deployment diagnostics."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .oidc_config import OidcRuntimeConfiguration
from .oidc_readiness import OidcDeploymentReadiness, OidcDeploymentReadinessValidator

@dataclass(frozen=True)
class OidcDiagnosticResult:
    state: str
    ready: bool
    reason: str
    checks: tuple[tuple[str, str], ...]
    def as_dict(self) -> dict[str, Any]:
        return {"state": self.state, "ready": self.ready, "reason": self.reason, "checks": dict(self.checks)}

class OidcDeploymentDiagnostics:
    """Observe readiness without authentication, mutation, or caller-controlled URLs."""
    def __init__(self, configuration: OidcRuntimeConfiguration, readiness_validator: OidcDeploymentReadinessValidator) -> None:
        if not isinstance(configuration, OidcRuntimeConfiguration): raise TypeError("trusted_oidc_configuration_required")
        if not isinstance(readiness_validator, OidcDeploymentReadinessValidator): raise TypeError("oidc_readiness_validator_required")
        self._configuration, self._validator = configuration, readiness_validator
    def passive(self) -> OidcDiagnosticResult:
        return self._result(self._validator.validate(self._configuration))
    def validate_metadata(self, metadata_validator: Any) -> OidcDiagnosticResult:
        if metadata_validator is None or not callable(getattr(metadata_validator, "validate", None)): raise ValueError("oidc_metadata_validator_required")
        return self._result(self._validator.validate(self._configuration, metadata_validator))
    @staticmethod
    def _result(readiness: OidcDeploymentReadiness) -> OidcDiagnosticResult:
        checks = {"configuration":"PASS", "secret":"PASS", "cryptography":"PASS", "provider_tenant_trust":"PASS", "metadata":"PASS", "jwks":"PASS"}
        failed = {"CONFIGURATION_INCOMPLETE":"configuration", "CONFIGURATION_INVALID":"configuration", "TRUST_NOT_ESTABLISHED":"provider_tenant_trust", "CRYPTOGRAPHY_UNAVAILABLE":"cryptography", "METADATA_UNAVAILABLE":"metadata", "METADATA_INVALID":"metadata"}.get(readiness.status)
        if failed: checks[failed] = "FAIL"
        elif readiness.status != "READY": checks["configuration"] = "FAIL"
        return OidcDiagnosticResult(readiness.status, readiness.status == "READY", readiness.reason, tuple(checks.items()))
