"""
Sentinel DNA Intelligence Knowledge Package

Provides shared knowledge graph primitives
used across threat intelligence, correlation,
investigation reasoning, and AI analysis.
"""

from .knowledge_graph import (
    KnowledgeGraph,
    Entity,
    Relationship,
)


__all__ = [
    "KnowledgeGraph",
    "Entity",
    "Relationship",
]