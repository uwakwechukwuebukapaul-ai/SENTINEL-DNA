"""
Sentinel DNA Threat Intelligence Layer.
"""

try:
    from .ioc_extractor import IOCExtractor  # type: ignore[import-not-found]
except ImportError:
    IOCExtractor = None
try:
    from .enrichment_engine import EnrichmentEngine  # type: ignore[import-not-found]
except ImportError:
    EnrichmentEngine = None


__all__ = [

    "IOCExtractor",
    "EnrichmentEngine",
    "ThreatIndicator", "ThreatMatch", "ThreatIntelligenceReport",
    "ThreatIntelligenceRepository", "ThreatCorrelationEngine",

]

from .models import ThreatIndicator, ThreatMatch, ThreatIntelligenceReport
from .repository import ThreatIntelligenceRepository
from .correlation_engine import ThreatCorrelationEngine
