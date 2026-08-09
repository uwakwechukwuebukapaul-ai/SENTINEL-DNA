"""
Sentinel DNA Correlation Intelligence Layer

Correlates IOC intelligence,
MITRE ATT&CK mappings,
and AI reasoning outputs.
"""

from .correlation_engine import (
    CorrelationEngine,
)

from .models import (
    CorrelationResult,
)

__all__ = [
    "CorrelationEngine",
    "CorrelationResult",
]