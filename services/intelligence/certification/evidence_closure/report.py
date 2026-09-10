"""Append-only persistence for enterprise evidence closure artifacts."""
from __future__ import annotations

from pathlib import Path

from .models import EvidenceClosureReport


class EvidenceClosureReportGenerator:
    """Write one closure artifact and reject replacement."""

    @staticmethod
    def write(report: EvidenceClosureReport, path: str | Path) -> Path:
        target = Path(path)
        if target.is_symlink() or target.parent.is_symlink():
            raise ValueError("immutable_evidence_closure_reparse_point")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"immutable_evidence_closure_exists: {target}")
        with target.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(report.to_json())
        return target


__all__ = ["EvidenceClosureReportGenerator"]
