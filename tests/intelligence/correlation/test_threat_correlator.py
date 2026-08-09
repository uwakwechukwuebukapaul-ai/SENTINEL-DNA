"""
Threat Correlator Tests

Validates Sentinel DNA IOC correlation,
knowledge graph enrichment, and threat reasoning.
"""


from services.intelligence.correlation import (
    ThreatCorrelator,
)

from services.intelligence.knowledge import (
    KnowledgeGraph,
    Entity,
    Relationship,
)



def create_graph():

    return KnowledgeGraph()



def test_ioc_match():

    graph = create_graph()


    graph.add_entity(
        Entity(
            id="IOC-001",
            entity_type="domain",
            value="evil.com",
        )
    )


    correlator = ThreatCorrelator(
        graph
    )


    result = correlator.correlate(
        "evil.com",
        "domain",
    )


    assert result.matched is True

    assert result.risk == "high"

    assert result.confidence > 0



def test_unknown_ioc():

    graph = create_graph()


    correlator = ThreatCorrelator(
        graph
    )


    result = correlator.correlate(
        "unknown-domain.com",
        "domain",
    )


    assert result.matched is False

    assert result.risk == "unknown"

    assert result.confidence == 0.0



def test_relationship_correlation():

    graph = create_graph()


    graph.add_entity(
        Entity(
            id="IOC-001",
            entity_type="domain",
            value="malicious.com",
        )
    )


    graph.add_entity(
        Entity(
            id="MALWARE-001",
            entity_type="malware",
            value="DarkLoader",
        )
    )


    graph.add_relationship(
        Relationship(
            source="IOC-001",
            target="MALWARE-001",
            relation_type="associated_with",
        )
    )


    correlator = ThreatCorrelator(
        graph
    )


    result = correlator.correlate(
        "malicious.com"
    )


    assert result.matched is True

    assert (
        "DarkLoader"
        in result.entities
    )



def test_result_serialization():

    graph = create_graph()


    graph.add_entity(
        Entity(
            id="IOC-002",
            entity_type="ip",
            value="10.10.10.10",
        )
    )


    correlator = ThreatCorrelator(
        graph
    )


    result = correlator.correlate(
        "10.10.10.10",
        "ip",
    )


    output = result.to_dict()


    assert output["matched"] is True

    assert "risk" in output

    assert "confidence" in output



def test_entity_type_filtering():

    graph = create_graph()


    graph.add_entity(
        Entity(
            id="IOC-003",
            entity_type="domain",
            value="example.com",
        )
    )


    graph.add_entity(
        Entity(
            id="HOST-001",
            entity_type="host",
            value="example.com",
        )
    )


    correlator = ThreatCorrelator(
        graph
    )


    result = correlator.correlate(
        "example.com",
        "domain",
    )


    assert result.matched is True

    assert (
        "example.com"
        in result.entities
    )