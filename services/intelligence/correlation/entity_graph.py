"""
Sentinel DNA Knowledge Graph

Stores entities and relationships
for threat intelligence correlation.

Supports:
- Modern Entity API
- Legacy dictionary API
"""

from dataclasses import dataclass, asdict
from typing import Any



@dataclass
class Entity:

    id: str

    entity_type: str

    value: str

    metadata: dict[str, Any] | None = None


    def __getitem__(self, key):

        return asdict(self)[key]



@dataclass
class Relationship:

    source: str

    target: str

    relation_type: str



class KnowledgeGraph:


    def __init__(self):

        self.entities = []

        self.relationships = []



    def add_entity(
        self,
        entity,
        value=None,
    ):

        if isinstance(entity, Entity):

            self.entities.append(entity)

            return entity



        if isinstance(entity, str) and value:

            created = Entity(

                id=f"{entity.upper()}-{len(self.entities)+1}",

                entity_type=entity,

                value=value,

            )


            self.entities.append(
                created
            )


            return created



        raise TypeError(
            "Invalid entity format"
        )



    def add_relationship(
        self,
        relationship,
    ):

        self.relationships.append(
            relationship
        )



    def find_entity(
        self,
        value,
        entity_type=None,
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
        entity_id,
    ):

        for entity in self.entities:

            if entity.id == entity_id:

                return entity


        return None



    def get_relationships(
        self,
        entity_id,
    ):

        results = []


        for relationship in self.relationships:

            if relationship.source == entity_id:

                target = self.get_entity(
                    relationship.target
                )


                if target:

                    results.append(
                        target
                    )


        return results



EntityGraph = KnowledgeGraph