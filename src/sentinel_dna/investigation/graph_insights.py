"""Deterministic, auditable intelligence derived from an investigation graph."""

from typing import Any

from sentinel_dna.investigation.graph import InvestigationGraph


class GraphInsightsEngine:
    """Produces explainable graph metrics without introducing another workflow engine."""

    def analyze(self, graph: InvestigationGraph) -> dict[str, Any]:
        relationships = graph.high_confidence_relationships()
        degree = {node_id: len(graph.relationships_for(node_id)) for node_id in graph.nodes}
        critical = [
            {
                "node_id": node_id,
                "node_type": graph.nodes[node_id].node_type,
                "value": graph.nodes[node_id].value,
                "relationship_count": count,
                "evidence_lineage": graph.evidence_lineage(node_id),
            }
            for node_id, count in degree.items() if count >= 2
        ]
        attack_paths = []
        for edge in graph.edges:
            source = graph.nodes.get(edge.source)
            target = graph.nodes.get(edge.target)
            if source and target and edge.relationship in {"maps_to", "malicious_domain", "supports"}:
                attack_paths.append({
                    "from": source.value, "to": target.value,
                    "relationship": edge.relationship, "confidence": edge.confidence,
                    "evidence_lineage": edge.lineage or graph.evidence_lineage(source),
                })
        return {
            "node_count": len(graph.nodes),
            "relationship_count": len(graph.edges),
            "high_confidence_relationships": [
                {"relationship": edge.relationship, "source": edge.source, "target": edge.target,
                 "confidence": edge.confidence, "evidence_lineage": edge.lineage}
                for edge in relationships
            ],
            "critical_entities": critical,
            "attack_paths": attack_paths,
            "investigation_summary": (
                f"Graph contains {len(graph.nodes)} entities and {len(graph.edges)} relationships; "
                f"{len(relationships)} relationships meet the high-confidence threshold."
            ),
        }
