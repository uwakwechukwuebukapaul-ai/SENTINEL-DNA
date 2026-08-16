"""Application-level execution boundary for controlled OIDC diagnostics."""
from __future__ import annotations

from typing import Any

from .oidc_diagnostics import OidcDeploymentDiagnostics, OidcDiagnosticResult


class OidcDeploymentDiagnosticsRunner:
    """Coordinate read-only diagnostics without owning security or network logic."""

    def __init__(self, diagnostics: OidcDeploymentDiagnostics) -> None:
        if not isinstance(diagnostics, OidcDeploymentDiagnostics):
            raise TypeError("oidc_diagnostics_required")
        self._diagnostics = diagnostics

    def run(self, metadata_validator: Any = None) -> OidcDiagnosticResult:
        """Run passive diagnostics, or explicit validation with an injected validator."""
        if metadata_validator is None:
            return self._diagnostics.passive()
        return self._diagnostics.validate_metadata(metadata_validator)
