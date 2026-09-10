"""Immutable billing validation report output."""

from __future__ import annotations

import os
from pathlib import Path

from .models import BillingValidationReport


class BillingEvidenceReportGenerator:
    """Generate billing evidence without invoking production billing paths."""

    @staticmethod
    def generate(*, generated_at: str | None = None) -> BillingValidationReport:
        from .runner import BillingEntitlementValidationRunner

        return BillingEntitlementValidationRunner(generated_at=generated_at).run()

    @staticmethod
    def write(report: BillingValidationReport, output: str | Path, *, repository_root: str | Path) -> Path:
        return write_immutable_report(report, output, repository_root=repository_root)


def deterministic_replay_digest(report: BillingValidationReport) -> str:
    """Return the stable replay digest from a generated report."""

    return report.replay_digest


def write_immutable_report(report: BillingValidationReport, output: str | Path, *, repository_root: str | Path) -> Path:
    """Write once outside the repository; never replace an evidence artifact."""

    root = Path(repository_root).resolve()
    candidate = Path(output).expanduser()
    if candidate.is_symlink() or candidate.parent.is_symlink():
        raise ValueError("billing_evidence_output_reparse_point")
    target = candidate.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("billing_evidence_output_must_be_outside_repository")
    if target.exists() or target.is_symlink():
        raise FileExistsError("billing_immutable_evidence_already_exists")
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise ValueError("billing_evidence_output_parent_invalid")
    temporary = target.with_name(f".{target.name}.tmp")
    if temporary.exists() or temporary.is_symlink():
        raise FileExistsError("billing_immutable_evidence_temporary_already_exists")
    temporary.write_text(report.to_json(), encoding="utf-8", newline="\n")
    try:
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target
