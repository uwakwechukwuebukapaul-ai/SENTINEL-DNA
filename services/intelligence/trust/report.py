"""Append-only trust closure report persistence."""
from __future__ import annotations

from pathlib import Path

from .models import TrustClosureReport


class TrustClosureReportGenerator:
    @staticmethod
    def write(report: TrustClosureReport, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(f"immutable_trust_closure_exists: {target}")
        target.write_text(report.to_json(), encoding="utf-8")
        return target


__all__ = ["TrustClosureReportGenerator"]
