"""
Sentinel DNA Intelligence Correlation Layer

Provides:
- IOC matching
- Threat correlation
- Attack story generation
- Correlation engine
"""

from .ioc_matcher import IOCMatcher
from .threat_correlator import ThreatCorrelator
from .correlation_result import CorrelationResult
from .correlation_engine import CorrelationEngine


__all__ = [
    "IOCMatcher",
    "ThreatCorrelator",
    "CorrelationResult",
    "CorrelationEngine",
]