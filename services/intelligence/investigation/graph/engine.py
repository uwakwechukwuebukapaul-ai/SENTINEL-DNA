"""
Sentinel DNA Investigation Graph Intelligence Engine.

Builds a deterministic investigation graph from evidence,
IOC intelligence, and threat intelligence.

The implementation is intentionally provider-agnostic so the
same domain contract can later be backed by Neo4j, another
graph database, or a distributed correlation service.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Iterable

from .models import (
    InvestigationGraph,
    InvestigationGraphNode,
    InvestigationGraphRelationship,
)


class InvestigationGraphEngine:
    """
    Builds and analyzes investigation entity graphs.

    Responsibilities:
        - normalize graph inputs
        - create investigation nodes
        - create deterministic relationships
        - detect connected components
        - calculate graph risk
        - expose graph statistics
    """

    ENGINE_NAME = (
        "investigation_graph_intelligence"
    )

    RISK_ORDER = {
        "unknown": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }

    def __init__(self) -> None:
        self._active_nodes: dict[
            str,
            InvestigationGraphNode,
        ] = {}

    def build(
        self,
        case_id: str,
        evidence: Any = None,
        iocs: Any = None,
        threats: Any = None,
    ) -> InvestigationGraph:
        """
        Build a complete investigation graph.
        """

        nodes: dict[
            str,
            InvestigationGraphNode,
        ] = {}

        relationships: dict[
            str,
            InvestigationGraphRelationship,
        ] = {}

        normalized_evidence = (
            self._normalize_collection(
                evidence
            )
        )

        normalized_iocs = (
            self._normalize_collection(
                iocs
            )
        )

        normalized_threats = (
            self._normalize_collection(
                threats
            )
        )

        self._active_nodes = nodes

        evidence_nodes = (
            self._process_evidence(
                normalized_evidence,
                nodes,
            )
        )

        ioc_nodes = (
            self._process_iocs(
                normalized_iocs,
                nodes,
            )
        )

        threat_nodes = (
            self._process_threats(
                normalized_threats,
                nodes,
            )
        )

        self._connect_evidence_to_iocs(
            evidence_nodes,
            ioc_nodes,
            relationships,
        )

        self._connect_iocs_to_threats(
            ioc_nodes,
            threat_nodes,
            relationships,
        )

        self._connect_shared_attributes(
            nodes,
            relationships,
        )

        graph_risk = (
            self._calculate_graph_risk(
                nodes.values()
            )
        )

        connected_components = (
            self._connected_components(
                nodes,
                relationships,
            )
        )

        result = InvestigationGraph(
            case_id=case_id,
            nodes=list(
                nodes.values()
            ),
            relationships=list(
                relationships.values()
            ),
            risk=graph_risk,
            connected_components=(
                connected_components
            ),
            metadata={
                "engine": self.ENGINE_NAME,
                "node_count": len(nodes),
                "relationship_count": len(
                    relationships
                ),
                "component_count": len(
                    connected_components
                ),
                "evidence_count": len(
                    normalized_evidence
                ),
                "ioc_count": len(
                    normalized_iocs
                ),
                "threat_count": len(
                    normalized_threats
                ),
            },
        )

        self._active_nodes = {}

        return result

    def analyze(
        self,
        case_id: str,
        evidence: Any = None,
        iocs: Any = None,
        threats: Any = None,
    ) -> InvestigationGraph:
        """
        Public analysis interface.
        """

        return self.build(
            case_id=case_id,
            evidence=evidence,
            iocs=iocs,
            threats=threats,
        )

    def _process_evidence(
        self,
        evidence: list[dict[str, Any]],
        nodes: dict[
            str,
            InvestigationGraphNode,
        ],
    ) -> list[str]:

        node_ids: list[str] = []

        for index, item in enumerate(
            evidence
        ):

            value = self._first_value(
                item,
                "value",
                "indicator",
                "name",
                "id",
            )

            if value is None:
                value = (
                    f"evidence-{index}"
                )

            node_id = self._node_id(
                "evidence",
                value,
            )

            node = (
                InvestigationGraphNode(
                    node_id=node_id,
                    node_type="evidence",
                    value=str(value),
                    risk=self._normalize_risk(
                        item.get("risk")
                    ),
                    attributes=dict(
                        item
                    ),
                )
            )

            nodes[node_id] = node
            node_ids.append(node_id)

        return node_ids

    def _process_iocs(
        self,
        iocs: list[dict[str, Any]],
        nodes: dict[
            str,
            InvestigationGraphNode,
        ],
    ) -> list[str]:

        node_ids: list[str] = []

        for index, item in enumerate(
            iocs
        ):

            value = self._first_value(
                item,
                "indicator",
                "value",
                "ioc",
                "name",
                "id",
            )

            if value is None:
                value = (
                    f"ioc-{index}"
                )

            node_id = self._node_id(
                "ioc",
                value,
            )

            risk = self._normalize_risk(
                item.get("risk")
                or item.get("severity")
            )

            node = (
                InvestigationGraphNode(
                    node_id=node_id,
                    node_type="ioc",
                    value=str(value),
                    risk=risk,
                    attributes=dict(
                        item
                    ),
                )
            )

            nodes[node_id] = node
            node_ids.append(node_id)

        return node_ids

    def _process_threats(
        self,
        threats: list[dict[str, Any]],
        nodes: dict[
            str,
            InvestigationGraphNode,
        ],
    ) -> list[str]:

        node_ids: list[str] = []

        for index, item in enumerate(
            threats
        ):

            value = self._first_value(
                item,
                "threat_name",
                "campaign",
                "actor",
                "name",
                "indicator",
                "id",
            )

            if value is None:
                value = (
                    f"threat-{index}"
                )

            node_id = self._node_id(
                "threat",
                value,
            )

            risk = self._normalize_risk(
                item.get("severity")
                or item.get("risk")
            )

            node = (
                InvestigationGraphNode(
                    node_id=node_id,
                    node_type="threat",
                    value=str(value),
                    risk=risk,
                    attributes=dict(
                        item
                    ),
                )
            )

            nodes[node_id] = node
            node_ids.append(node_id)

        return node_ids

    def _connect_evidence_to_iocs(
        self,
        evidence_nodes: list[str],
        ioc_nodes: list[str],
        relationships: dict[
            str,
            InvestigationGraphRelationship,
        ],
    ) -> None:

        for evidence_id in (
            evidence_nodes
        ):

            evidence = self._node_value(
                evidence_id
            )

            for ioc_id in ioc_nodes:

                ioc = self._node_value(
                    ioc_id
                )

                if self._values_match(
                    evidence,
                    ioc,
                ):

                    self._add_relationship(
                        relationships,
                        evidence_id,
                        ioc_id,
                        "contains_ioc",
                        confidence=100,
                    )

    def _connect_iocs_to_threats(
        self,
        ioc_nodes: list[str],
        threat_nodes: list[str],
        relationships: dict[
            str,
            InvestigationGraphRelationship,
        ],
    ) -> None:

        for ioc_id in ioc_nodes:

            ioc_value = (
                self._node_value(
                    ioc_id
                )
            )

            for threat_id in (
                threat_nodes
            ):

                threat_node = (
                    self._find_node(
                        threat_id
                    )
                )

                if threat_node is None:
                    continue

                attributes = (
                    threat_node.attributes
                )

                threat_indicator = (
                    self._first_value(
                        attributes,
                        "indicator",
                        "value",
                        "ioc",
                    )
                )

                related_indicators = (
                    attributes.get(
                        "related_indicators",
                        [],
                    )
                    or []
                )

                matches = (
                    self._values_match(
                        ioc_value,
                        threat_indicator,
                    )
                    or any(
                        self._values_match(
                            ioc_value,
                            value,
                        )
                        for value in (
                            related_indicators
                        )
                    )
                )

                if matches:

                    self._add_relationship(
                        relationships,
                        ioc_id,
                        threat_id,
                        "associated_with_threat",
                        confidence=100,
                    )

    def _connect_shared_attributes(
        self,
        nodes: dict[
            str,
            InvestigationGraphNode,
        ],
        relationships: dict[
            str,
            InvestigationGraphRelationship,
        ],
    ) -> None:

        node_list = list(
            nodes.values()
        )

        for index, left in enumerate(
            node_list
        ):

            for right in node_list[
                index + 1 :
            ]:

                shared = (
                    self._shared_attributes(
                        left,
                        right,
                    )
                )

                if not shared:
                    continue

                confidence = min(
                    100,
                    50 + (
                        len(shared) * 10
                    ),
                )

                self._add_relationship(
                    relationships,
                    left.node_id,
                    right.node_id,
                    "shares_context",
                    confidence=confidence,
                    metadata={
                        "shared_attributes": (
                            shared
                        )
                    },
                )

    def _shared_attributes(
        self,
        left: InvestigationGraphNode,
        right: InvestigationGraphNode,
    ) -> list[str]:

        shared: list[str] = []

        for key in (
            "domain",
            "ip",
            "hostname",
            "user",
            "username",
            "account",
            "campaign",
            "actor",
        ):

            left_value = (
                left.attributes.get(
                    key
                )
            )

            right_value = (
                right.attributes.get(
                    key
                )
            )

            if (
                left_value is not None
                and right_value is not None
                and self._values_match(
                    left_value,
                    right_value,
                )
            ):

                shared.append(
                    key
                )

        return shared

    def _add_relationship(
        self,
        relationships: dict[
            str,
            InvestigationGraphRelationship,
        ],
        source: str,
        target: str,
        relationship_type: str,
        confidence: int = 50,
        metadata: dict[str, Any] | None = None,
    ) -> None:

        relationship_id = (
            f"{source}|"
            f"{relationship_type}|"
            f"{target}"
        )

        if relationship_id in (
            relationships
        ):
            return

        relationships[
            relationship_id
        ] = InvestigationGraphRelationship(
            relationship_id=(
                relationship_id
            ),
            source=source,
            target=target,
            relationship_type=(
                relationship_type
            ),
            confidence=max(
                0,
                min(
                    100,
                    int(confidence),
                ),
            ),
            metadata=dict(
                metadata or {}
            ),
        )

    def _calculate_graph_risk(
        self,
        nodes: Iterable[
            InvestigationGraphNode
        ],
    ) -> str:

        highest = "unknown"

        for node in nodes:

            if self.RISK_ORDER.get(
                node.risk,
                0,
            ) > self.RISK_ORDER.get(
                highest,
                0,
            ):

                highest = node.risk

        return highest

    def _connected_components(
        self,
        nodes: dict[
            str,
            InvestigationGraphNode,
        ],
        relationships: dict[
            str,
            InvestigationGraphRelationship,
        ],
    ) -> list[list[str]]:

        adjacency: dict[
            str,
            set[str],
        ] = defaultdict(set)

        for relationship in (
            relationships.values()
        ):

            adjacency[
                relationship.source
            ].add(
                relationship.target
            )

            adjacency[
                relationship.target
            ].add(
                relationship.source
            )

        visited: set[str] = set()

        components: list[
            list[str]
        ] = []

        for node_id in nodes:

            if node_id in visited:
                continue

            component: list[str] = []

            queue = deque(
                [node_id]
            )

            visited.add(
                node_id
            )

            while queue:

                current = (
                    queue.popleft()
                )

                component.append(
                    current
                )

                for neighbor in (
                    adjacency.get(
                        current,
                        set(),
                    )
                ):

                    if neighbor in visited:
                        continue

                    visited.add(
                        neighbor
                    )

                    queue.append(
                        neighbor
                    )

            components.append(
                sorted(component)
            )

        return components

    def _normalize_collection(
        self,
        value: Any,
    ) -> list[dict[str, Any]]:

        if value is None:
            return []

        if isinstance(
            value,
            dict,
        ):

            return [
                self._to_dict(value)
            ]

        if isinstance(
            value,
            (list, tuple, set),
        ):

            result: list[
                dict[str, Any]
            ] = []

            for item in value:

                normalized = (
                    self._to_dict(
                        item
                    )
                )

                if normalized:
                    result.append(
                        normalized
                    )

            return result

        normalized = (
            self._to_dict(value)
        )

        if normalized:
            return [normalized]

        return []

    def _to_dict(
        self,
        value: Any,
    ) -> dict[str, Any]:

        if isinstance(
            value,
            dict,
        ):
            return dict(value)

        to_dict = getattr(
            value,
            "to_dict",
            None,
        )

        if callable(to_dict):

            result = to_dict()

            if isinstance(
                result,
                dict,
            ):

                return dict(
                    result
                )

        attributes = getattr(
            value,
            "__dict__",
            None,
        )

        if isinstance(
            attributes,
            dict,
        ):

            return dict(
                attributes
            )

        return {}

    def _node_id(
        self,
        node_type: str,
        value: Any,
    ) -> str:

        normalized = (
            str(value)
            .strip()
            .lower()
        )

        return (
            f"{node_type}:{normalized}"
        )

    def _find_node(
        self,
        node_id: str,
    ) -> (
        InvestigationGraphNode | None
    ):

        return self._active_nodes.get(
            node_id
        )

    def _node_value(
        self,
        node_id: str,
    ) -> str:

        node = self._find_node(
            node_id
        )

        if node is None:
            return ""

        return str(
            node.value
        )

    def _values_match(
        self,
        left: Any,
        right: Any,
    ) -> bool:

        if left is None or right is None:
            return False

        return (
            str(left)
            .strip()
            .lower()
            ==
            str(right)
            .strip()
            .lower()
        )

    def _first_value(
        self,
        data: dict[str, Any],
        *keys: str,
    ) -> Any:

        for key in keys:

            value = data.get(
                key
            )

            if value is not None:
                return value

        return None

    def _normalize_risk(
        self,
        value: Any,
    ) -> str:

        normalized = (
            str(
                value or "unknown"
            )
            .strip()
            .lower()
        )

        if normalized not in (
            self.RISK_ORDER
        ):

            return "unknown"

        return normalized


__all__ = [
    "InvestigationGraphEngine",
]