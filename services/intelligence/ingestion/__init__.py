"""
Sentinel DNA - Intelligence Ingestion

Handles ingestion and normalization
of external security events.
"""

from .event_normalizer import EventNormalizer
from .event_gateway import EventGateway
from .models import IngestionBatch, IngestionMetrics, NormalizedSecurityEvent, SecurityEvent
from .collectors import APICollector, BaseCollector, SyntheticEventCollector, WebhookCollector
from .normalizer import SecurityEventNormalizer
from .repository import IngestionRepository
from .service import SecurityIngestionService


__all__ = [
    "EventNormalizer",
    "EventGateway",
    "SecurityEvent", "NormalizedSecurityEvent", "IngestionBatch", "IngestionMetrics",
    "BaseCollector", "SyntheticEventCollector", "WebhookCollector", "APICollector",
    "SecurityEventNormalizer", "IngestionRepository", "SecurityIngestionService",
]
