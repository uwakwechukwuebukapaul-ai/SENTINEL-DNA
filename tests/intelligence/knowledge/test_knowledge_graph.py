"""
Knowledge Graph Tests

Validates:
- Entity management
- Relationship creation
- Graph queries
- Intelligence context retrieval
"""

from services.intelligence.knowledge.entity import Entity
from services.intelligence.knowledge.relationship import Relationship
from services.intelligence.knowledge.knowledge_graph import KnowledgeGraph
from services.intelligence.knowledge.graph_query import GraphQuery


def create_graph():
    return KnowledgeGraph()


def test_create_entity():

    graph = create_graph()

    entity = Entity(
        id="IOC-001",
        entity_type="ip",
        value="192.168.1.10",
    )

    graph.add_entity(entity)

    result = graph.get_entity(
        "IOC-001"
    )

    assert result.value == "192.168.1.10"


def test_create_relationship():

    graph = create_graph()

    source = Entity(
        id="HOST-001",
        entity_type="host",
        value="WORKSTATION-01",
    )

    target = Entity(
        id="IOC-001",
        entity_type="ip",
        value="10.10.10.5",
    )

    graph.add_entity(source)
    graph.add_entity(target)


    relationship = Relationship(
        source="HOST-001",
        target="IOC-001",
        relation_type="communicates_with",
    )


    graph.add_relationship(
        relationship
    )


    assert len(
        graph.relationships
    ) == 1



def test_query_entities():

    graph = create_graph()


    graph.add_entity(
        Entity(
            id="MALWARE-001",
            entity_type="malware",
            value="trojan.exe",
        )
    )


    query = GraphQuery(
        graph
    )


    results = query.find_entities(
        entity_type="malware"
    )


    assert len(results) == 1

    assert results[0].value == "trojan.exe"



def test_find_relationships():

    graph = create_graph()


    graph.add_entity(
        Entity(
            id="USER-001",
            entity_type="user",
            value="admin",
        )
    )


    graph.add_entity(
        Entity(
            id="IOC-002",
            entity_type="domain",
            value="evil.com",
        )
    )


    graph.add_relationship(
        Relationship(
            source="USER-001",
            target="IOC-002",
            relation_type="visited",
        )
    )


    query = GraphQuery(
        graph
    )


    relationships = query.find_relationships(
        "USER-001"
    )


    assert len(
        relationships
    ) == 1


    assert (
        relationships[0].relation_type
        ==
        "visited"
    )



def test_graph_entity_count():

    graph = create_graph()


    graph.add_entity(
        Entity(
            id="CASE-001",
            entity_type="incident",
            value="INC-001",
        )
    )


    graph.add_entity(
        Entity(
            id="IOC-003",
            entity_type="hash",
            value="abc123",
        )
    )


    assert (
        len(graph.entities)
        ==
        2
    )



def test_remove_entity():

    graph = create_graph()


    entity = Entity(
        id="IOC-DELETE",
        entity_type="ip",
        value="8.8.8.8",
    )


    graph.add_entity(
        entity
    )


    graph.remove_entity(
        "IOC-DELETE"
    )


    assert (
        graph.get_entity(
            "IOC-DELETE"
        )
        is None
    )