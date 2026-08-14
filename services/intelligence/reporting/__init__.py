"""
Sentinel DNA Intelligence Reporting Package.

Provides:
- Investigation reports
- Report generation
- Backward compatibility exports
"""

from .investigation_report import (
    InvestigationReport,
    InvestigationReportGenerator,
)

from .report_builder import (
    ReportBuilder,
)
from .models import InvestigationNarrative
from .narrative_engine import InvestigationNarrativeEngine


__all__ = [
    "InvestigationReport",
    "InvestigationReportGenerator",
    "ReportBuilder",
    "InvestigationNarrative",
    "InvestigationNarrativeEngine",
]
