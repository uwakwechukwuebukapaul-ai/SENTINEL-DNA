"""
Sentinel DNA Knowledge Graph Engine

Stores:
- Entities
- Relationships
- Intelligence connections
"""


from typing import Dict, List

from .entity import Entity
from .relationship import Relationship



class KnowledgeGraph:
    """
    Core graph storage engine.
    """


    def __init__(self):

        self.entities: Dict[str, Entity] = {}

        self.relationships: List[
            Relationship
        ] = []



    def add_entity(
        self,
        entity: Entity
    ):

        self.entities[
            entity.id
        ] = entity

        return entity



    def get_entity(
        self,
        entity_id: str
    ):

        return self.entities.get(
            entity_id
        )



    def remove_entity(
        self,
        entity_id: str
    ):

        if entity_id in self.entities:

            del self.entities[
                entity_id
            ]


        self.relationships = [
            relationship
            for relationship in self.relationships
            if relationship.source != entity_id
            and relationship.target != entity_id
        ]


        return True



    def add_relationship(
        self,
        relationship: Relationship
    ):

        self.relationships.append(
            relationship
        )

        return relationship



    def get_relationships(
        self,
        entity_id=None
    ):

        if entity_id is None:

            return self.relationships


        return [
            relationship
            for relationship in self.relationships
            if relationship.source == entity_id
            or relationship.target == entity_id
        ]



    def find_entities(
        self,
        entity_type=None
    ):

        entities = list(
            self.entities.values()
        )


        if entity_type is None:

            return entities


        return [
            entity
            for entity in entities
            if entity.entity_type
            == entity_type
        ]