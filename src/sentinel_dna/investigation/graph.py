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
    ) -> GraphEdge:

        edge = GraphEdge(
            source=source.node_id,
            target=target.node_id,
            relationship=relationship,
            metadata=metadata or {},
        )

        self.edges.append(edge)

        return edge


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