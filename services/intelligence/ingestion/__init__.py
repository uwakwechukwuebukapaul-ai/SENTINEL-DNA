"""
Sentinel DNA - Intelligence Ingestion

Handles ingestion and normalization
of external security events.
"""

from .event_normalizer import EventNormalizer
from .event_gateway import EventGateway


__all__ = [
    "EventNormalizer",
    "EventGateway",
]