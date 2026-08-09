"""
Sentinel DNA Knowledge Graph Query Layer

Provides higher-level graph search operations.
"""

from typing import Any, Optional

from .knowledge_graph import KnowledgeGraph  # type: ignore[reportMissingImports]


class GraphQuery:
    """
    Query interface for KnowledgeGraph.
    """

    def __init__(
        self,
        graph: KnowledgeGraph,
    ):

        self.graph = graph


    # =====================================================
    # ENTITY QUERIES
    # =====================================================

    def find_entities(
        self,
        entity_type: Optional[str] = None,
        value: Optional[str] = None,
    ):
        """
        Find entities by filters.
        """

        return self.graph.find_entities(
            entity_type=entity_type,
            value=value,
        )


    def find_entity(
        self,
        value: str,
        entity_type: Optional[str] = None,
    ):
        """
        Find single entity.
        """

        return self.graph.find_entity(
            value,
            entity_type,
        )


    # =====================================================
    # RELATIONSHIP QUERIES
    # =====================================================

    def find_relationships(
        self,
        entity_id: str,
    ) -> list[Any]:
        """
        Return relationship objects.

        Important:
        Do not return target entities.
        Consumers need relationship metadata
        like relation_type.
        """

        return [
            relationship
            for relationship in self.graph.relationships
            if (
                relationship.source == entity_id
                or
                relationship.target == entity_id
            )
        ]


    # =====================================================
    # TRAVERSAL
    # =====================================================

    def related_entities(
        self,
        entity_id: str,
    ) -> list[Any]:
        """
        Return entities connected to an ID.
        """

        results = []

        for relationship in self.find_relationships(
            entity_id
        ):

            target_id = (
                relationship.target
                if relationship.source == entity_id
                else relationship.source
            )


            entity = self.graph.get_entity(
                target_id
            )


            if entity:
                results.append(entity)


        return results