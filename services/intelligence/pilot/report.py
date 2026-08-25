"""Immutable operational pilot report persistence."""
from __future__ import annotations

from pathlib import Path

from .models import OperationalPilotReport


class OperationalPilotReportGenerator:
    """Persist one pilot report without allowing artifact replacement."""

    @staticmethod
    def write(report: OperationalPilotReport, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(f"immutable_operational_pilot_exists: {target}")
        target.write_text(report.to_json(), encoding="utf-8")
        return target


__all__ = ["OperationalPilotReportGenerator"]
