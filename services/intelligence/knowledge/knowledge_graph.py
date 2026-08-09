"""
Sentinel DNA Knowledge Graph

Central intelligence graph used by:

- Threat correlation
- IOC enrichment
- Investigation reasoning
- Relationship traversal
- Intelligence context retrieval
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Entity:
    """
    Intelligence graph entity.
    """

    id: str
    entity_type: str
    value: str
    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class Relationship:
    """
    Entity relationship edge.
    """

    source: str
    target: str
    relation_type: str


class KnowledgeGraph:
    """
    Shared enterprise knowledge graph.

    Supports:

    - entity creation
    - entity lookup
    - entity search
    - relationship storage
    - relationship traversal
    - entity deletion
    """

    def __init__(self):

        self.entities: list[Entity] = []

        self.relationships: list[Relationship] = []


    # =====================================================
    # ENTITY MANAGEMENT
    # =====================================================

    def add_entity(
        self,
        entity: Entity,
    ):
        """
        Add entity to graph.
        """

        self.entities.append(
            entity
        )

        return entity


    def get_entity(
        self,
        entity_id: str,
    ) -> Optional[Entity]:
        """
        Retrieve entity by ID.
        """

        for entity in self.entities:

            if entity.id == entity_id:
                return entity

        return None


    def find_entity(
        self,
        value: str,
        entity_type: str | None = None,
    ) -> Optional[Entity]:
        """
        Find single entity by value.
        """

        for entity in self.entities:

            if entity.value != value:
                continue

            if (
                entity_type
                and entity.entity_type != entity_type
            ):
                continue

            return entity

        return None


    def find_entities(
        self,
        entity_type: str | None = None,
        value: str | None = None,
    ) -> list[Entity]:
        """
        Search multiple entities.

        Compatibility API used by GraphQuery.
        """

        results = []

        for entity in self.entities:

            if (
                entity_type
                and entity.entity_type != entity_type
            ):
                continue

            if (
                value
                and entity.value != value
            ):
                continue

            results.append(
                entity
            )

        return results


    def remove_entity(
        self,
        entity_id: str,
    ) -> bool:
        """
        Remove entity and attached relationships.
        """

        before = len(
            self.entities
        )


        self.entities = [
            entity
            for entity in self.entities
            if entity.id != entity_id
        ]


        self.relationships = [
            relationship
            for relationship in self.relationships
            if (
                relationship.source != entity_id
                and
                relationship.target != entity_id
            )
        ]


        return len(self.entities) < before


    # =====================================================
    # RELATIONSHIP MANAGEMENT
    # =====================================================

    def add_relationship(
        self,
        relationship: Relationship,
    ):
        """
        Add relationship edge.
        """

        self.relationships.append(
            relationship
        )

        return relationship


    def get_relationships(
        self,
        entity_id: str,
    ) -> list[Entity]:
        """
        Return related entities.

        Maintains existing correlation engine
        compatibility.
        """

        results = []

        for relationship in self.relationships:

            if relationship.source != entity_id:
                continue


            target = self.get_entity(
                relationship.target
            )


            if target:

                results.append(
                    target
                )


        return results


    def find_relationships(
        self,
        entity_id: str,
    ) -> list[Relationship]:
        """
        Return relationship objects.

        Used by GraphQuery.
        """

        return [
            relationship
            for relationship in self.relationships
            if (
                relationship.source == entity_id
                or
                relationship.target == entity_id
            )
        ]


    # =====================================================
    # SEARCH
    # =====================================================

    def search(
        self,
        value: str,
    ) -> list[Entity]:
        """
        Search entities by value.
        """

        return [
            entity
            for entity in self.entities
            if entity.value == value
        ]


    def clear(
        self,
    ):
        """
        Reset graph.
        """

        self.entities.clear()

        self.relationships.clear()

        return True


# =========================================================
# Compatibility Alias
# =========================================================

EntityGraph = KnowledgeGraph