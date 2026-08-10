"""
Sentinel DNA Investigation Graph Models.

Stable data contracts for investigation graph intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GraphNode:
    """
    Represents an entity in the investigation graph.
    """

    node_id: str
    node_type: str
    value: str

    risk: str = "unknown"

    attributes: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "value": self.value,
            "risk": self.risk,
            "attributes": dict(
                self.attributes
            ),
        }

    def __getitem__(
        self,
        key: str,
    ) -> Any:
        return self.to_dict()[key]


@dataclass
class GraphRelationship:
    """
    Represents a directed relationship between graph nodes.
    """

    relationship_id: str

    source: str
    target: str

    relationship_type: str

    confidence: int = 50

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "relationship_id": (
                self.relationship_id
            ),
            "source": self.source,
            "target": self.target,
            "relationship_type": (
                self.relationship_type
            ),
            "confidence": self.confidence,
            "metadata": dict(
                self.metadata
            ),
        }

    def __getitem__(
        self,
        key: str,
    ) -> Any:
        return self.to_dict()[key]


@dataclass
class InvestigationGraph:
    """
    Complete investigation graph result.
    """

    case_id: str

    nodes: list[GraphNode] = field(
        default_factory=list
    )

    relationships: list[GraphRelationship] = field(
        default_factory=list
    )

    risk: str = "unknown"

    connected_components: list[list[str]] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "nodes": [
                node.to_dict()
                if hasattr(
                    node,
                    "to_dict",
                )
                else node
                for node in self.nodes
            ],
            "relationships": [
                relationship.to_dict()
                if hasattr(
                    relationship,
                    "to_dict",
                )
                else relationship
                for relationship in self.relationships
            ],
            "risk": self.risk,
            "connected_components": [
                list(component)
                for component in (
                    self.connected_components
                )
            ],
            "metadata": dict(
                self.metadata
            ),
        }

    def __getitem__(
        self,
        key: str,
    ) -> Any:
        return self.to_dict()[key]


# Explicit aliases used by the investigation
# intelligence layer.
InvestigationGraphNode = GraphNode
InvestigationGraphRelationship = GraphRelationship


__all__ = [
    "GraphNode",
    "GraphRelationship",
    "InvestigationGraphNode",
    "InvestigationGraphRelationship",
    "InvestigationGraph",
]