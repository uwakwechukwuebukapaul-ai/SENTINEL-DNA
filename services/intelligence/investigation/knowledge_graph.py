"""
Sentinel DNA Investigation Knowledge Graph

Builds relationships between investigation entities,
evidence, indicators, techniques, and events.
"""

from __future__ import annotations

from typing import Any


class KnowledgeNode:
    """
    Single graph entity.
    """

    def __init__(
        self,
        node_id: str,
        node_type: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:

        self.id = node_id
        self.type = node_type
        self.attributes = attributes or {}


class KnowledgeEdge:
    """
    Relationship between graph nodes.
    """

    def __init__(
        self,
        source: str,
        target: str,
        relation: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:

        self.source = source
        self.target = target
        self.relation = relation
        self.attributes = attributes or {}


class InvestigationKnowledgeGraph:
    """
    Enterprise investigation graph.

    Example:

    Email
      |
      contains
      |
    Malicious URL
      |
      maps_to
      |
    MITRE Technique
    """

    def __init__(self) -> None:

        self.nodes: dict[str, KnowledgeNode] = {}
        self.edges: list[KnowledgeEdge] = []


    def add_node(
        self,
        node_id: str,
        node_type: str,
        attributes: dict[str, Any] | None = None,
    ) -> KnowledgeNode:

        node = KnowledgeNode(
            node_id,
            node_type,
            attributes,
        )

        self.nodes[node_id] = node

        return node


    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        attributes: dict[str, Any] | None = None,
    ) -> KnowledgeEdge:

        edge = KnowledgeEdge(
            source,
            target,
            relation,
            attributes,
        )

        self.edges.append(edge)

        return edge


    def add_ioc(
        self,
        ioc: dict[str, Any],
    ) -> None:

        value = ioc.get(
            "value",
            "unknown",
        )

        self.add_node(
            value,
            "ioc",
            ioc,
        )


    def add_mitre(
        self,
        technique: str,
    ) -> None:

        self.add_node(
            technique,
            "mitre_technique",
        )


    def connect(
        self,
        source: str,
        target: str,
        relation: str,
    ) -> None:

        self.add_edge(
            source,
            target,
            relation,
        )


    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "nodes": [
                {
                    "id": node.id,
                    "type": node.type,
                    "attributes": node.attributes,
                }
                for node in self.nodes.values()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "relation": edge.relation,
                    "attributes": edge.attributes,
                }
                for edge in self.edges
            ],
        }