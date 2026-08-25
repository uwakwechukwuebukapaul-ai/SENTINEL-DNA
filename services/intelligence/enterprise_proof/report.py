"""Immutable, append-only enterprise proof report generation."""
from __future__ import annotations

from pathlib import Path

from .enterprise_proof import EnterpriseProofValidator
from .models import EnterpriseProofValidationReport


class EnterpriseProofReportGenerator:
    """Generate and persist a single immutable proof artifact."""

    def __init__(self, validator: EnterpriseProofValidator | None = None) -> None:
        self.validator = validator or EnterpriseProofValidator()

    def generate(self) -> EnterpriseProofValidationReport:
        return self.validator.run()

    @staticmethod
    def write(report: EnterpriseProofValidationReport, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(f"immutable_enterprise_proof_exists: {target}")
        target.write_text(report.to_json(), encoding="utf-8")
        return target


__all__ = ["EnterpriseProofReportGenerator"]
