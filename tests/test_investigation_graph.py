from sentinel_dna.investigation.graph import (
    InvestigationGraph,
)


def test_graph_creation():

    graph = InvestigationGraph()

    evidence = graph.add_node(
        "evidence",
        "EV-001",
    )

    ioc = graph.add_node(
        "ioc",
        "evil.com",
    )

    graph.add_edge(
        evidence,
        ioc,
        "contains",
    )

    result = graph.to_dict()

    assert len(result["nodes"]) == 2
    assert len(result["edges"]) == 1