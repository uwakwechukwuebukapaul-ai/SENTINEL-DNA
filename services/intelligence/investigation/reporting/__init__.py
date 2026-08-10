"""
Sentinel DNA Investigation Reporting Layer.

Generates structured analyst-ready investigation reports
from fused investigation intelligence.
"""

from .generator import (
    InvestigationReportGenerator,
)

from .models import (
    InvestigationReport,
)


__all__ = [
    "InvestigationReportGenerator",
    "InvestigationReport",
]