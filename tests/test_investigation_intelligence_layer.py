from sentinel_dna.investigation.graph import InvestigationGraph
from sentinel_dna.investigation.graph_insights import GraphInsightsEngine
from sentinel_dna.investigation import InvestigationContext, InvestigationOrchestrator


def test_graph_relationships_preserve_confidence_and_evidence_lineage():
    graph = InvestigationGraph()
    evidence = graph.add_node("Evidence", "EV-001", {"source": "email"})
    ioc = graph.add_node("IOC", "login.example", {"type": "domain"})
    edge = graph.add_edge(evidence, ioc, "contains", confidence=0.95, lineage=["EV-001"])

    assert edge.confidence == 0.95
    assert graph.evidence_lineage(ioc) == ["EV-001"]
    assert graph.high_confidence_relationships() == [edge]


def test_graph_insights_identifies_confident_relationships():
    graph = InvestigationGraph()
    evidence = graph.add_node("Evidence", "EV-001")
    ioc = graph.add_node("IOC", "login.example")
    graph.add_edge(evidence, ioc, "contains", confidence=0.9, lineage=["EV-001"])

    insights = GraphInsightsEngine().analyze(graph)

    assert insights["node_count"] == 2
    assert insights["relationship_count"] == 1
    assert insights["high_confidence_relationships"][0]["confidence"] == 0.9


def test_orchestrator_emits_explainable_intelligence_layer(tmp_path):
    context = InvestigationContext(case_id="intelligence-001", alert={
        "subject": "Verify password", "body": "Open https://example-login.com now.",
    })
    result = InvestigationOrchestrator(tmp_path).run(context).results

    assert result["graph_insights"]["node_count"] > 0
    assert result["confidence"]["factors"]
    assert result["reasoning"]["trace"]["supporting_evidence"]
    assert result["report"]["graph_relationships"]
