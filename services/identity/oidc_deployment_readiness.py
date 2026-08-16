"""Application-level OIDC deployment readiness composition boundary."""
from __future__ import annotations

from typing import Any

from .oidc_diagnostics import OidcDiagnosticResult
from .oidc_diagnostics_runner import OidcDeploymentDiagnosticsRunner


class OidcDeploymentReadinessService:
    """Expose existing diagnostics as a deployment-controlled readiness contract."""

    def __init__(self, runner: OidcDeploymentDiagnosticsRunner) -> None:
        if not isinstance(runner, OidcDeploymentDiagnosticsRunner):
            raise TypeError("oidc_diagnostics_runner_required")
        self._runner = runner

    def check(self, metadata_validator: Any = None) -> OidcDiagnosticResult:
        """Delegate passive or explicitly injected metadata readiness checking."""
        return self._runner.run(metadata_validator)
