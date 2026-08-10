"""
Sentinel DNA Investigation Evidence Intelligence Layer.

Provides evidence normalization, artifact classification,
indicator extraction, and investigation context preparation.
"""

from .models import (
    EvidenceArtifact,
    EvidenceCollection,
)

from .engine import (
    EvidenceIntelligenceEngine,
)


__all__ = [
    "EvidenceArtifact",
    "EvidenceCollection",
    "EvidenceIntelligenceEngine",
]