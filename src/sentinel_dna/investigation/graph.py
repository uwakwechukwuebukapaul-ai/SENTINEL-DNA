"""
Sentinel DNA Investigation Evidence Graph.

Provides:
- evidence relationship tracking
- entity correlation
- investigation graph serialization
"""

from dataclasses import dataclass, field, asdict
from typing import Any
from uuid import uuid4


@dataclass
class GraphNode:
    """
    Investigation graph node.
    """

    node_type: str
    value: str

    node_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class GraphEdge:
    """
    Relationship between investigation nodes.
    """

    source: str
    target: str
    relationship: str

    edge_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    confidence: float = 1.0

    lineage: list[str] = field(default_factory=list)


class InvestigationGraph:
    """
    Evidence relationship graph.

    Example:

        Evidence
            |
            contains
            |
            IOC
            |
            maps_to
            |
            MITRE Technique

    """

    def __init__(self) -> None:

        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []


    def add_node(
        self,
        node_type: str,
        value: str,
        metadata: dict[str, Any] | None = None,
    ) -> GraphNode:

        node = GraphNode(
            node_type=node_type,
            value=value,
            metadata=metadata or {},
        )

        self.nodes[node.node_id] = node

        return node


    def add_edge(
        self,
        source: GraphNode,
        target: GraphNode,
        relationship: str,
        metadata: dict[str, Any] | None = None,
        confidence: float = 1.0,
        lineage: list[str] | None = None,
    ) -> GraphEdge:

        edge = GraphEdge(
            source=source.node_id,
            target=target.node_id,
            relationship=relationship,
            metadata=metadata or {},
            confidence=max(0.0, min(1.0, confidence)),
            lineage=lineage or [],
        )

        self.edges.append(edge)

        return edge

    def relationships_for(self, node: GraphNode | str) -> list[GraphEdge]:
        """Return relationships touching a node, for explainable traversal."""
        node_id = node if isinstance(node, str) else node.node_id
        return [edge for edge in self.edges if node_id in (edge.source, edge.target)]

    def evidence_lineage(self, node: GraphNode | str) -> list[str]:
        """Return evidence IDs that support a node through direct relationships."""
        node_id = node if isinstance(node, str) else node.node_id
        lineage = []
        for edge in self.relationships_for(node_id):
            lineage.extend(edge.lineage)
            other_id = edge.target if edge.source == node_id else edge.source
            other = self.nodes.get(other_id)
            if other and other.node_type.lower() == "evidence":
                lineage.append(other.value)
        return list(dict.fromkeys(lineage))

    def high_confidence_relationships(self, threshold: float = 0.8) -> list[GraphEdge]:
        return [edge for edge in self.edges if edge.confidence >= threshold]


    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "nodes": [
                asdict(node)
                for node in self.nodes.values()
            ],
            "edges": [
                asdict(edge)
                for edge in self.edges
            ],
        }
