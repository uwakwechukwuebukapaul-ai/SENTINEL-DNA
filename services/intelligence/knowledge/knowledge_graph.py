"""
Sentinel DNA Knowledge Graph

Central intelligence graph used by:
- Threat correlation
- IOC enrichment
- Investigation reasoning
- Relationship traversal
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Entity:
    id: str
    entity_type: str
    value: str
    metadata: dict[str, Any] | None = None


@dataclass
class Relationship:
    source: str
    target: str
    relation_type: str


class KnowledgeGraph:
    """
    Shared enterprise knowledge graph.
    """

    def __init__(self):

        self.entities: list[Entity] = []
        self.relationships: list[Relationship] = []


    def add_entity(
        self,
        entity: Entity,
    ):

        self.entities.append(entity)



    def add_relationship(
        self,
        relationship: Relationship,
    ):

        self.relationships.append(
            relationship
        )



    def find_entity(
        self,
        value: str,
        entity_type: str | None = None,
    ):

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



    def get_entity(
        self,
        entity_id: str,
    ):

        for entity in self.entities:

            if entity.id == entity_id:
                return entity

        return None



    def get_relationships(
        self,
        entity_id: str,
    ):

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



    def search(
        self,
        value: str,
    ):

        return [
            entity
            for entity in self.entities
            if entity.value == value
        ]



# compatibility

EntityGraph = KnowledgeGraph