"""Immutable certification report persistence."""
from __future__ import annotations

from pathlib import Path

from .models import CertificationReport


class CertificationReportGenerator:
    """Write one certification artifact and reject replacement."""

    @staticmethod
    def write(report: CertificationReport, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(f"immutable_certification_report_exists: {target}")
        target.write_text(report.to_json(), encoding="utf-8")
        return target


__all__ = ["CertificationReportGenerator"]
