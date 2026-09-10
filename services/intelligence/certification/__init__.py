"""Unified Sentinel DNA enterprise readiness certification."""

from .models import (
    CertificationControl,
    CertificationEvidence,
    CertificationFinding,
    CertificationMetric,
    CertificationReport,
)
from .report import CertificationReportGenerator
from .runner import EnterpriseCertificationRunner


_EVIDENCE_CLOSURE_EXPORTS = {
    "EnterpriseEvidenceClosureRunner",
    "EvidenceClosureReport",
    "EvidenceClosureReportGenerator",
}


def __getattr__(name):
    if name in _EVIDENCE_CLOSURE_EXPORTS:
        from . import evidence_closure

        value = getattr(evidence_closure, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "CertificationControl",
    "CertificationEvidence",
    "CertificationFinding",
    "CertificationMetric",
    "CertificationReport",
    "CertificationReportGenerator",
    "EnterpriseCertificationRunner",
    "EnterpriseEvidenceClosureRunner",
    "EvidenceClosureReport",
    "EvidenceClosureReportGenerator",
]
