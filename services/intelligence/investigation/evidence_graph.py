"""
Sentinel DNA Evidence Graph Engine

Builds investigation relationships between:

- Alerts
- IOCs
- Entities
- MITRE techniques
- Findings
"""

from __future__ import annotations

from typing import Any


class EvidenceGraph:

    def __init__(self) -> None:

        self.nodes: dict[str, dict[str, Any]] = {}

        self.edges: list[dict[str, Any]] = []


    def add_node(
        self,
        node_id: str,
        node_type: str,
        data: dict[str, Any],
    ) -> None:

        self.nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            "data": data,
        }


    def add_relationship(
        self,
        source: str,
        target: str,
        relation: str,
    ) -> None:

        self.edges.append(
            {
                "source": source,
                "target": target,
                "relation": relation,
            }
        )


    def build_from_result(
        self,
        result,
    ) -> dict[str, Any]:

        for ioc in result.iocs:

            value = ioc.get(
                "value"
            )

            self.add_node(
                value,
                "ioc",
                ioc,
            )


        for technique in result.mitre_attack:

            self.add_node(
                technique,
                "mitre",
                {
                    "technique": technique
                },
            )


        for ioc in result.iocs:

            for technique in result.mitre_attack:

                self.add_relationship(
                    ioc["value"],
                    technique,
                    "associated_with",
                )


        return self.to_dict()


    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "nodes": list(
                self.nodes.values()
            ),
            "edges": self.edges,
        }