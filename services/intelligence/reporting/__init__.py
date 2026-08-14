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


__all__ = [
    "InvestigationReport",
    "InvestigationReportGenerator",
    "ReportBuilder",
]