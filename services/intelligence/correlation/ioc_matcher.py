"""
IOC matching engine.

Matches indicators against
Sentinel DNA knowledge graph entities.
"""


class IOCMatcher:


    def __init__(
        self,
        knowledge_graph
    ):

        self.graph = knowledge_graph



    def match(
        self,
        indicator: str,
        indicator_type: str | None = None,
    ):

        matches = []


        entities = (
            self.graph.find_entities()
        )


        for entity in entities:

            if entity.value == indicator:

                if (
                    indicator_type is None
                    or entity.entity_type
                    == indicator_type
                ):

                    matches.append(
                        entity
                    )


        return matches