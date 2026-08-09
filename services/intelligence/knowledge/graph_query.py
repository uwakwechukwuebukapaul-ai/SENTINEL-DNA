"""
Knowledge Graph Query Layer

Provides analyst-friendly graph searches.
"""


class GraphQuery:
    """
    Query interface over KnowledgeGraph.
    """


    def __init__(
        self,
        graph
    ):

        self.graph = graph



    def find_entity(
        self,
        entity_id
    ):

        return self.graph.get_entity(
            entity_id
        )



    def find_entities(
        self,
        entity_type=None
    ):

        return self.graph.find_entities(
            entity_type
        )



    def find_relationships(
        self,
        entity_id=None
    ):

        return self.graph.get_relationships(
            entity_id
        )



    def find_by_type(
        self,
        entity_type
    ):

        return self.graph.find_entities(
            entity_type
        )



    def connected_entities(
        self,
        entity_id
    ):

        relationships = (
            self.graph.get_relationships(
                entity_id
            )
        )


        results = []


        for relationship in relationships:

            if relationship.source == entity_id:

                target_id = (
                    relationship.target
                )

            else:

                target_id = (
                    relationship.source
                )


            entity = (
                self.graph.get_entity(
                    target_id
                )
            )


            if entity:

                results.append(
                    entity
                )


        return results