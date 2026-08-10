"""
Sentinel DNA Threat Intelligence Correlation Layer.

Provides structured threat context correlation for
investigation indicators.

The package is intentionally provider-agnostic so external
threat intelligence providers can be integrated later.
"""

from .models import (
    ThreatContext,
    ThreatIntelligenceCollection,
)

from .engine import (
    ThreatIntelligenceEngine,
)


__all__ = [
    "ThreatContext",
    "ThreatIntelligenceCollection",
    "ThreatIntelligenceEngine",
]