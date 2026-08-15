"""Unified, provenance-preserving AI SOC intelligence convergence layer."""
from .models import IntelligenceRecord, IntelligenceRelationship, AttentionItem, PlatformSnapshot
from .repository import PlatformFabricRepository
from .service import PlatformIntelligenceService
__all__=["IntelligenceRecord","IntelligenceRelationship","AttentionItem","PlatformSnapshot","PlatformFabricRepository","PlatformIntelligenceService"]
