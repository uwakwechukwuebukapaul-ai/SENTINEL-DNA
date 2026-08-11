"""
Sentinel DNA Investigation Orchestrator Compatibility Layer.

Legacy import path:

    services.intelligence.orchestration.investigation._orchestrator

Canonical implementation:

    services.intelligence.orchestration.investigation_orchestrator
"""

from __future__ import annotations

from services.intelligence.orchestration.investigation_orchestrator import (
    InvestigationOrchestrator,
)


__all__ = [
    "InvestigationOrchestrator",
]