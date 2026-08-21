"""Deterministic, evidence-backed Investigator V1 relationship graph.

This module is deliberately a traceability layer.  It does not perform
enrichment, fusion, reasoning, scoring, recommendation generation, or
response actions.  It only materializes relationships already represented by
trusted Investigator V1 contracts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from .canonical import canonical_json, freeze, sha256_digest, thaw


class InvestigationNodeType(StrEnum):
    EVIDENCE = "EVIDENCE"
    IOC = "IOC"
    PROVIDER_OBSERVATION = "PROVIDER_OBSERVATION"
    FINDING = "FINDING"
    TIMELINE_EVENT = "TIMELINE_EVENT"
    MITRE_TECHNIQUE = "MITRE_TECHNIQUE"
    RECOMMENDATION = "RECOMMENDATION"
    CONCLUSION = "CONCLUSION"


class InvestigationRelationshipType(StrEnum):
    EVIDENCE_SUPPORTS_FINDING = "EVIDENCE_SUPPORTS_FINDING"
    EVIDENCE_SUPPORTS_IOC = "EVIDENCE_SUPPORTS_IOC"
    EVIDENCE_SUPPORTS_MITRE = "EVIDENCE_SUPPORTS_MITRE"
    PROVIDER_OBSERVATION_SUPPORTS_FINDING = "PROVIDER_OBSERVATION_SUPPORTS_FINDING"
    PROVIDER_OBSERVATION_ENRICHES_IOC = "PROVIDER_OBSERVATION_ENRICHES_IOC"
    IOC_APPEARS_IN_TIMELINE = "IOC_APPEARS_IN_TIMELINE"
    FINDING_REFERENCES_MITRE = "FINDING_REFERENCES_MITRE"
    FINDING_SUPPORTED_BY_EVIDENCE = "FINDING_SUPPORTED_BY_EVIDENCE"
    FINDING_SUPPORTS_CONCLUSION = "FINDING_SUPPORTS_CONCLUSION"
    FINDING_SUPPORTS_RECOMMENDATION = "FINDING_SUPPORTS_RECOMMENDATION"
    TIMELINE_SUPPORTS_FINDING = "TIMELINE_SUPPORTS_FINDING"


@dataclass(frozen=True)
class _LifecycleAwareProviderObservation:
    """Internal graph input wrapper; ProviderObservation remains unchanged."""

    observation: Any
    lifecycle_status: str

    def verify(self) -> bool:
        verifier = getattr(self.observation, "verify", None)
        return bool(callable(verifier) and verifier())

    def to_dict(self) -> dict[str, Any]:
        serializer = getattr(self.observation, "to_dict", None)
        value = dict(serializer()) if callable(serializer) else {}
        value["lifecycle_status"] = self.lifecycle_status
        return value


_NODE_TYPES = {item.value for item in InvestigationNodeType}
_RELATIONSHIP_TYPES = {item.value for item in InvestigationRelationshipType}
_LIFECYCLE_ACTIVE = "ACTIVE"
_LIFECYCLE_STALE = "STALE"
_LIFECYCLE_TERMINAL = {"INVALIDATED", "EXPIRED"}
_PUBLIC_NODE_METADATA_KEYS = {
    "source",
    "source_type",
    "evidence_type",
    "status",
    "severity",
    "risk",
    "evidence_status",
    "reasoning_type",
    "ioc_type",
    "technique_id",
    "event_type",
    "provider",
    "observation_type",
}
_PUBLIC_RELATIONSHIP_METADATA_KEYS = {"basis", "status", "technique_id"}
_PUBLIC_PROVENANCE_KEYS = {
    "source",
    "source_type",
    "source_identifier",
    "provider",
    "provider_version",
    "observation_id",
    "observation_type",
    "status",
    "provenance_status",
    "integrity_status",
    "verified",
    "digest",
    "reasoning_type",
    "providers",
    "disposition",
}
_SENSITIVE_KEYS = {
    "authorization",
    "authorization_header",
    "api_key",
    "bearer",
    "credential",
    "credentials",
    "password",
    "secret",
    "token",
    "raw_provider_payload",
    "raw_provider_response",
    "raw_response",
    "provider_payload",
    "payload",
    "response",
    "headers",
    "authorization_headers",
}


def _text(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        candidate = value.to_dict()
        if isinstance(candidate, Mapping):
            return dict(candidate)
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    return {}


def _safe(value: Any, *, depth: int = 0) -> Any:
    """Allowlist-safe scalar metadata without copying payloads."""
    if depth > 3:
        return None
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            key_text = _text(key)
            if not key_text or key_text.lower() in _SENSITIVE_KEYS:
                continue
            safe = _safe(item, depth=depth + 1)
            if safe is not None:
                result[key_text] = safe
        return result
    if isinstance(value, (list, tuple, set, frozenset)):
        values = [_safe(item, depth=depth + 1) for item in value]
        return [item for item in values if item is not None]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return _text(value)


def _timestamp(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("timestamp", "observed_at", "created_at", "captured_at"):
            candidate = _text(value.get(key))
            if candidate:
                return candidate
        return None
    for key in ("timestamp", "observed_at", "created_at", "captured_at"):
        candidate = _text(getattr(value, key, None))
        if candidate:
            return candidate
    return None


def _confidence(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _values(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set, frozenset)):
        return list(value)
    return [value]


def _references(value: Mapping[str, Any], *keys: str) -> list[str]:
    result = []
    for key in keys:
        for item in _values(value.get(key)):
            if isinstance(item, Mapping):
                item = item.get("finding_id") or item.get("recommendation_id") or item.get("ioc_id") or item.get("id") or item.get("value")
            reference = _text(item)
            if reference:
                result.append(reference)
    return list(dict.fromkeys(result))


def _reference_scope(value: Mapping[str, Any]) -> tuple[str | None, str | None]:
    tenant = value.get("tenant_id") or value.get("organization_id")
    case = value.get("case_id") or value.get("investigation_id")
    context = value.get("tenant_context")
    if isinstance(context, Mapping):
        tenant = tenant or context.get("tenant_id") or context.get("organization_id")
        case = case or context.get("case_id") or context.get("investigation_id")
    return _text(tenant), _text(case)


def _authorized_evidence_reference(
    reference: Any,
    *,
    tenant_id: str,
    case_id: str,
    evidence_ids: set[str],
) -> str | None:
    if isinstance(reference, Mapping):
        reference_tenant, reference_case = _reference_scope(reference)
        if reference_tenant != tenant_id or reference_case != case_id:
            return None
        identifier = reference.get("evidence_id") or reference.get("artifact_id")
    elif isinstance(reference, str):
        identifier = reference
    else:
        return None
    identifier = _text(identifier)
    return identifier if identifier in evidence_ids else None


def _ioc_id(value: Any) -> str | None:
    data = _mapping(value)
    ioc = data.get("ioc") if isinstance(data.get("ioc"), Mapping) else data
    ioc_type = _text(ioc.get("type") or ioc.get("ioc_type")) if isinstance(ioc, Mapping) else None
    ioc_value = _text(ioc.get("value") or ioc.get("indicator")) if isinstance(ioc, Mapping) else None
    if ioc_type and ioc_value:
        return f"IOC:{ioc_type}:{ioc_value}"
    explicit = _text(data.get("ioc_id") or data.get("indicator_id") or data.get("id"))
    if explicit:
        return f"IOC:{explicit}"
    return None


@dataclass(frozen=True)
class InvestigationNode:
    node_type: str
    node_id: str
    tenant_id: str
    case_id: str
    actor_id: str | None = None
    correlation_id: str | None = None
    provenance: Mapping[str, Any] = freeze({})
    timestamp: str | None = None
    metadata: Mapping[str, Any] = freeze({})

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_type": self.node_type,
            "node_id": self.node_id,
            "tenant_id": self.tenant_id,
            "case_id": self.case_id,
            "actor_id": self.actor_id,
            "correlation_id": self.correlation_id,
            "provenance": thaw(self.provenance),
            "timestamp": self.timestamp,
            "metadata": thaw(self.metadata),
        }


@dataclass(frozen=True)
class InvestigationRelationship:
    relationship_id: str
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relationship_type: str
    tenant_id: str
    case_id: str
    actor_id: str | None = None
    correlation_id: str | None = None
    timestamp: str | None = None
    provenance: Mapping[str, Any] = freeze({})
    confidence: int | float | None = None
    evidence_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = freeze({})

    def to_dict(self) -> dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "tenant_id": self.tenant_id,
            "case_id": self.case_id,
            "actor_id": self.actor_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "provenance": thaw(self.provenance),
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
            "metadata": thaw(self.metadata),
        }


@dataclass(frozen=True)
class InvestigationRelationshipGraph:
    tenant_id: str
    case_id: str
    actor_id: str | None = None
    correlation_id: str | None = None
    nodes: tuple[InvestigationNode, ...] = ()
    relationships: tuple[InvestigationRelationship, ...] = ()
    schema_version: str = "investigation-relationship-graph-v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tenant_id": self.tenant_id,
            "case_id": self.case_id,
            "actor_id": self.actor_id,
            "correlation_id": self.correlation_id,
            "nodes": [node.to_dict() for node in self.nodes],
            "relationships": [relationship.to_dict() for relationship in self.relationships],
        }


def project_relationship_graph(
    value: Any,
    *,
    tenant_id: str | None = None,
    case_id: str | None = None,
    actor_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any] | None:
    """Return the approved, scope-valid graph projection for API/UI use.

    This is serialization and integrity filtering only. Authorization remains
    owned by the existing investigation boundary.
    """
    data = _mapping(value)
    graph_tenant = _text(data.get("tenant_id"))
    graph_case = _text(data.get("case_id"))
    expected_tenant = _text(tenant_id)
    expected_case = _text(case_id)
    expected_actor = _text(actor_id)
    expected_correlation = _text(correlation_id)
    if not graph_tenant or not graph_case:
        return None
    if expected_tenant and graph_tenant != expected_tenant:
        return None
    if expected_case and graph_case != expected_case:
        return None
    if expected_actor and _text(data.get("actor_id")) != expected_actor:
        return None
    if expected_correlation and _text(data.get("correlation_id")) != expected_correlation:
        return None

    def public_mapping(value: Any, allowed_keys: set[str]) -> dict[str, Any]:
        safe = _safe(value or {})
        return {
            str(key): item
            for key, item in safe.items()
            if str(key) in allowed_keys
        } if isinstance(safe, Mapping) else {}

    nodes_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for item in _values(data.get("nodes")):
        node = _mapping(item)
        node_type = _text(node.get("node_type"))
        node_id = _text(node.get("node_id"))
        if node_type not in _NODE_TYPES or not node_id:
            continue
        if _text(node.get("tenant_id")) != graph_tenant or _text(node.get("case_id")) != graph_case:
            continue
        if expected_actor and node.get("actor_id") is not None and _text(node.get("actor_id")) != expected_actor:
            continue
        if expected_correlation and node.get("correlation_id") is not None and _text(node.get("correlation_id")) != expected_correlation:
            continue
        nodes_by_key[(node_type, node_id)] = {
            "node_type": node_type,
            "node_id": node_id,
            "tenant_id": graph_tenant,
            "case_id": graph_case,
            "actor_id": _text(node.get("actor_id")),
            "correlation_id": _text(node.get("correlation_id")),
            "provenance": public_mapping(node.get("provenance"), _PUBLIC_PROVENANCE_KEYS),
            "timestamp": _text(node.get("timestamp")),
            "metadata": public_mapping(node.get("metadata"), _PUBLIC_NODE_METADATA_KEYS),
        }
    evidence_ids = {
        node_id
        for node_type, node_id in nodes_by_key
        if node_type == InvestigationNodeType.EVIDENCE.value
    }

    relationships_by_id: dict[str, dict[str, Any]] = {}
    for item in _values(data.get("relationships")):
        relationship = _mapping(item)
        relationship_id = _text(relationship.get("relationship_id"))
        source_type = _text(relationship.get("source_type"))
        source_id = _text(relationship.get("source_id"))
        target_type = _text(relationship.get("target_type"))
        target_id = _text(relationship.get("target_id"))
        relationship_type = _text(relationship.get("relationship_type"))
        if (
            not relationship_id
            or source_type not in _NODE_TYPES
            or target_type not in _NODE_TYPES
            or relationship_type not in _RELATIONSHIP_TYPES
            or not source_id
            or not target_id
            or (source_type, source_id) not in nodes_by_key
            or (target_type, target_id) not in nodes_by_key
        ):
            continue
        if _text(relationship.get("tenant_id")) != graph_tenant or _text(relationship.get("case_id")) != graph_case:
            continue
        if expected_actor and relationship.get("actor_id") is not None and _text(relationship.get("actor_id")) != expected_actor:
            continue
        if expected_correlation and relationship.get("correlation_id") is not None and _text(relationship.get("correlation_id")) != expected_correlation:
            continue
        confidence = relationship.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            confidence = None
        evidence_refs = []
        for reference in _values(relationship.get("evidence_refs")):
            authorized_reference = _authorized_evidence_reference(
                reference,
                tenant_id=graph_tenant,
                case_id=graph_case,
                evidence_ids=evidence_ids,
            )
            if authorized_reference:
                evidence_refs.append(authorized_reference)
        relationships_by_id[relationship_id] = {
            "relationship_id": relationship_id,
            "source_type": source_type,
            "source_id": source_id,
            "target_type": target_type,
            "target_id": target_id,
            "relationship_type": relationship_type,
            "tenant_id": graph_tenant,
            "case_id": graph_case,
            "actor_id": _text(relationship.get("actor_id")),
            "correlation_id": _text(relationship.get("correlation_id")),
            "timestamp": _text(relationship.get("timestamp")),
            "provenance": public_mapping(relationship.get("provenance"), _PUBLIC_PROVENANCE_KEYS),
            "confidence": confidence,
            "evidence_refs": list(dict.fromkeys(evidence_refs)),
            "metadata": public_mapping(relationship.get("metadata"), _PUBLIC_RELATIONSHIP_METADATA_KEYS),
        }

    nodes = sorted(nodes_by_key.values(), key=lambda item: (item["node_type"], item["node_id"]))
    relationships = sorted(
        relationships_by_id.values(),
        key=lambda item: (
            item["tenant_id"],
            item["case_id"],
            item["source_type"],
            item["source_id"],
            item["relationship_type"],
            item["target_type"],
            item["target_id"],
            item["timestamp"] or "",
            item["relationship_id"],
        ),
    )
    return {
        "schema_version": _text(data.get("schema_version")) or "investigation-relationship-graph-v1",
        "tenant_id": graph_tenant,
        "case_id": graph_case,
        "actor_id": expected_actor or _text(data.get("actor_id")),
        "correlation_id": expected_correlation or _text(data.get("correlation_id")),
        "nodes": nodes,
        "relationships": relationships,
    }


class DeterministicRelationshipBuilder:
    """Materialize only explicit, scope-valid traceability relationships."""

    def build(
        self,
        *,
        tenant_id: str | None,
        case_id: str | None,
        actor_id: str | None = None,
        correlation_id: str | None = None,
        evidence: Sequence[Any] | None = None,
        findings: Sequence[Any] | None = None,
        provider_observations: Sequence[Any] | None = None,
        iocs: Sequence[Any] | None = None,
        timeline: Sequence[Any] | None = None,
        recommendations: Sequence[Any] | None = None,
        conclusion: Any = None,
    ) -> InvestigationRelationshipGraph:
        tenant = _text(tenant_id)
        case = _text(case_id)
        if not tenant or not case:
            return InvestigationRelationshipGraph(tenant or "", case or "", actor_id, correlation_id)

        nodes: dict[tuple[str, str], InvestigationNode] = {}
        relationships: dict[str, InvestigationRelationship] = {}
        evidence_ids: set[str] = set()
        provider_by_evidence: dict[str, InvestigationNode] = {}
        evidence_data: dict[str, dict[str, Any]] = {}
        finding_data: dict[str, dict[str, Any]] = {}
        ioc_nodes: dict[str, InvestigationNode] = {}
        timeline_data: dict[str, dict[str, Any]] = {}
        recommendation_data: dict[str, dict[str, Any]] = {}
        conclusion_data: dict[str, dict[str, Any]] = {}

        def add_node(node: InvestigationNode) -> None:
            if node.node_type not in _NODE_TYPES or not node.node_id:
                return
            nodes.setdefault((node.node_type, node.node_id), node)

        def scoped(data: Mapping[str, Any]) -> bool:
            if data.get("tenant_id") is not None and str(data.get("tenant_id")) != tenant:
                return False
            if data.get("case_id") is not None and str(data.get("case_id")) != case:
                return False
            if actor_id and data.get("actor_id") is not None and str(data.get("actor_id")) != str(actor_id):
                return False
            if correlation_id and data.get("correlation_id") is not None and str(data.get("correlation_id")) != str(correlation_id):
                return False
            return True

        def add_relationship(
            *,
            source: InvestigationNode,
            target: InvestigationNode,
            relationship_type: str,
            evidence_refs: Sequence[str] = (),
            provenance: Mapping[str, Any] | None = None,
            timestamp: str | None = None,
            confidence: int | float | None = None,
            metadata: Mapping[str, Any] | None = None,
        ) -> None:
            if relationship_type not in _RELATIONSHIP_TYPES:
                return
            refs = tuple(sorted({ref for ref in (_text(item) for item in evidence_refs) if ref and ref in evidence_ids}))
            safe_provenance = _safe(provenance or {})
            if not isinstance(safe_provenance, Mapping):
                safe_provenance = {}
            identity = {
                "tenant_id": tenant,
                "case_id": case,
                "source_type": source.node_type,
                "source_id": source.node_id,
                "relationship_type": relationship_type,
                "target_type": target.node_type,
                "target_id": target.node_id,
                "evidence_refs": refs,
                "provenance": safe_provenance,
            }
            relationship_id = f"REL-{sha256_digest(identity)[:24]}"
            relationship = InvestigationRelationship(
                relationship_id=relationship_id,
                source_type=source.node_type,
                source_id=source.node_id,
                target_type=target.node_type,
                target_id=target.node_id,
                relationship_type=relationship_type,
                tenant_id=tenant,
                case_id=case,
                actor_id=actor_id,
                correlation_id=correlation_id,
                timestamp=timestamp,
                provenance=freeze(safe_provenance),
                confidence=_confidence(confidence),
                evidence_refs=refs,
                metadata=freeze(_safe(metadata or {})),
            )
            relationships.setdefault(relationship_id, relationship)

        def add_evidence(item: Any) -> None:
            data = _mapping(item)
            reference = _text(data.get("evidence_id") or data.get("artifact_id") or data.get("reference") or data.get("id"))
            provenance = data.get("provenance")
            if not reference or not isinstance(provenance, Mapping) or not provenance or not scoped(data):
                return
            node = InvestigationNode(
                InvestigationNodeType.EVIDENCE.value,
                reference,
                tenant,
                case,
                _text(data.get("actor_id")) or actor_id,
                _text(data.get("correlation_id")) or correlation_id,
                freeze(_safe(provenance)),
                _timestamp(data),
                freeze(_safe({
                    "source": data.get("source"),
                    "source_type": data.get("source_type"),
                    "evidence_type": data.get("evidence_type"),
                    "status": data.get("status"),
                })),
            )
            add_node(node)
            evidence_ids.add(reference)
            evidence_data[reference] = data

        for item in evidence or ():
            add_evidence(item)

        def add_provider_observation(observation: Any) -> None:
            verify = getattr(observation, "verify", None)
            try:
                if not callable(verify) or not verify():
                    return
            except Exception:
                return
            data = _mapping(observation)
            if not data:
                data = {
                    key: getattr(observation, key, None)
                    for key in (
                        "observation_id", "tenant_id", "case_id", "actor_id", "correlation_id",
                        "provider_name", "observation_type", "source", "source_reference",
                        "observed_at", "status", "provenance", "evidence_references", "invalidated",
                    )
                }
            lifecycle_status = data.get("lifecycle_status")
            lifecycle = data.get("lifecycle")
            if lifecycle_status is None and isinstance(lifecycle, Mapping):
                lifecycle_status = lifecycle.get("status")
            if lifecycle_status is not None:
                lifecycle_status = str(lifecycle_status).upper()
                if lifecycle_status in _LIFECYCLE_TERMINAL:
                    return
                if lifecycle_status not in {_LIFECYCLE_ACTIVE, _LIFECYCLE_STALE}:
                    return
            if data.get("invalidated") or str(data.get("status", "")).lower() in {"invalidated", "expired", "invalid"}:
                return
            if not scoped(data) or str(data.get("tenant_id")) != tenant or str(data.get("case_id")) != case:
                return
            observation_id = _text(data.get("observation_id"))
            provenance = data.get("provenance")
            if not observation_id or not isinstance(provenance, Mapping) or not provenance:
                return
            node = InvestigationNode(
                InvestigationNodeType.PROVIDER_OBSERVATION.value,
                observation_id,
                tenant,
                case,
                _text(data.get("actor_id")) or actor_id,
                _text(data.get("correlation_id")) or correlation_id,
                freeze(_safe(provenance)),
                _timestamp(data),
                freeze(_safe({
                    "provider": data.get("provider_name"),
                    "observation_type": data.get("observation_type"),
                    "status": data.get("status"),
                    "source": data.get("source"),
                })),
            )
            add_node(node)
            refs = [ref for ref in _values(data.get("evidence_references")) if _text(ref)]
            for ref in refs:
                ref = _text(ref)
                synthetic = {
                    "evidence_id": ref,
                    "tenant_id": tenant,
                    "case_id": case,
                    "actor_id": data.get("actor_id"),
                    "correlation_id": data.get("correlation_id"),
                    "source": data.get("source"),
                    "evidence_type": "provider_observation",
                    "status": data.get("status"),
                    "provenance": {
                        "source": data.get("source"),
                        "source_type": "provider_observation",
                        "observation_id": observation_id,
                    },
                }
                add_evidence(synthetic)
                provider_by_evidence[ref] = node

            normalized = data.get("normalized_observation")
            ioc_data = normalized.get("ioc") if isinstance(normalized, Mapping) else None
            ioc_key = _ioc_id(ioc_data)
            if ioc_key:
                ioc_node = ioc_nodes.get(ioc_key)
                if ioc_node is None:
                    ioc_node = InvestigationNode(
                        InvestigationNodeType.IOC.value,
                        ioc_key,
                        tenant,
                        case,
                        actor_id=actor_id,
                        correlation_id=correlation_id,
                        provenance=freeze(_safe(provenance)),
                        metadata=freeze(_safe({"ioc_type": _mapping(ioc_data).get("type")})),
                    )
                    ioc_nodes[ioc_key] = ioc_node
                    add_node(ioc_node)
                add_relationship(
                    source=node,
                    target=ioc_node,
                    relationship_type=InvestigationRelationshipType.PROVIDER_OBSERVATION_ENRICHES_IOC.value,
                    evidence_refs=refs,
                    provenance=provenance,
                    timestamp=_timestamp(data),
                )

        for observation in provider_observations or ():
            add_provider_observation(observation)

        def add_ioc(item: Any) -> None:
            data = _mapping(item)
            if not data or not scoped(data):
                return
            key = _ioc_id(data)
            if not key:
                return
            node = ioc_nodes.get(key)
            if node is None:
                node = InvestigationNode(
                    InvestigationNodeType.IOC.value,
                    key,
                    tenant,
                    case,
                    _text(data.get("actor_id")) or actor_id,
                    _text(data.get("correlation_id")) or correlation_id,
                    freeze(_safe(data.get("provenance") or {})),
                    _timestamp(data),
                    freeze(_safe({"ioc_type": data.get("type") or data.get("ioc_type")})),
                )
                ioc_nodes[key] = node
                add_node(node)

        for item in iocs or ():
            add_ioc(item)

        for evidence_id, data in evidence_data.items():
            evidence_node = nodes.get((InvestigationNodeType.EVIDENCE.value, evidence_id))
            if evidence_node is None:
                continue
            evidence_provenance = data.get("provenance") or {}
            raw_ioc_refs = []
            for key in ("ioc_refs", "ioc_ids", "indicator", "ioc"):
                raw_ioc_refs.extend(_values(data.get(key)))
            for ioc_ref in raw_ioc_refs:
                ioc_key = _ioc_id(ioc_ref)
                if ioc_key is None:
                    reference = _text(ioc_ref)
                    ioc_key = reference if reference and reference.startswith("IOC:") else None
                ioc_node = ioc_nodes.get(ioc_key) if ioc_key else None
                if ioc_node is not None:
                    add_relationship(
                        source=evidence_node,
                        target=ioc_node,
                        relationship_type=InvestigationRelationshipType.EVIDENCE_SUPPORTS_IOC.value,
                        evidence_refs=(evidence_id,),
                        provenance=evidence_provenance,
                        timestamp=evidence_node.timestamp or ioc_node.timestamp,
                    )
            for technique_id in _references(data, "mitre_refs", "mitre_techniques", "techniques"):
                technique_id = _text(technique_id)
                if not technique_id:
                    continue
                mitre = nodes.get((InvestigationNodeType.MITRE_TECHNIQUE.value, technique_id))
                if mitre is None:
                    mitre = InvestigationNode(
                        InvestigationNodeType.MITRE_TECHNIQUE.value,
                        technique_id,
                        tenant,
                        case,
                        actor_id=actor_id,
                        correlation_id=correlation_id,
                        provenance=freeze(_safe(evidence_provenance)),
                        metadata=freeze({"technique_id": technique_id}),
                    )
                    add_node(mitre)
                add_relationship(
                    source=evidence_node,
                    target=mitre,
                    relationship_type=InvestigationRelationshipType.EVIDENCE_SUPPORTS_MITRE.value,
                    evidence_refs=(evidence_id,),
                    provenance=evidence_provenance,
                    timestamp=evidence_node.timestamp or mitre.timestamp,
                )

        for item in findings or ():
            data = _mapping(item)
            finding_id = _text(data.get("finding_id") or data.get("id"))
            if not finding_id or not scoped(data):
                continue
            evidence_refs = _references(data, "evidence_refs", "evidence_references")
            provider_refs = _references(data, "provider_observation_refs", "provider_observation_references")
            valid_basis = set(evidence_refs).intersection(evidence_ids)
            valid_provider_basis = {
                reference
                for reference in provider_refs
                if (InvestigationNodeType.PROVIDER_OBSERVATION.value, reference) in nodes
            }
            if not valid_basis and not valid_provider_basis:
                continue
            provenance = data.get("intelligence_provenance") or data.get("provenance") or {}
            node = InvestigationNode(
                InvestigationNodeType.FINDING.value,
                finding_id,
                tenant,
                case,
                _text(data.get("actor_id")) or actor_id,
                _text(data.get("correlation_id")) or correlation_id,
                freeze(_safe(provenance)),
                _timestamp(data),
                freeze(_safe({
                    "severity": data.get("severity"),
                    "risk": data.get("risk"),
                    "evidence_status": data.get("evidence_status"),
                    "reasoning_type": data.get("reasoning_type"),
                })),
            )
            add_node(node)
            finding_data[finding_id] = data

        for item in timeline or ():
            data = _mapping(item)
            event_id = _text(data.get("event_id"))
            if not event_id or not scoped(data):
                continue
            node = InvestigationNode(
                InvestigationNodeType.TIMELINE_EVENT.value,
                event_id,
                tenant,
                case,
                _text(data.get("actor_id")) or actor_id,
                _text(data.get("correlation_id")) or correlation_id,
                freeze(_safe(data.get("provenance") or {})),
                _timestamp(data),
                freeze(_safe({"event_type": data.get("event_type"), "source": data.get("source")})),
            )
            add_node(node)
            timeline_data[event_id] = data

        for item in recommendations or ():
            data = _mapping(item)
            recommendation_id = _text(data.get("recommendation_id") or data.get("id"))
            if not recommendation_id or not scoped(data):
                continue
            node = InvestigationNode(
                InvestigationNodeType.RECOMMENDATION.value,
                recommendation_id,
                tenant,
                case,
                _text(data.get("actor_id")) or actor_id,
                _text(data.get("correlation_id")) or correlation_id,
                freeze(_safe(data.get("provenance") or {})),
                _timestamp(data),
                freeze(_safe({"status": data.get("status")})),
            )
            add_node(node)
            recommendation_data[recommendation_id] = data

        conclusion_mapping = _mapping(conclusion)
        conclusion_id = _text(conclusion_mapping.get("conclusion_id") or conclusion_mapping.get("id"))
        if conclusion_id and scoped(conclusion_mapping):
            node = InvestigationNode(
                InvestigationNodeType.CONCLUSION.value,
                conclusion_id,
                tenant,
                case,
                _text(conclusion_mapping.get("actor_id")) or actor_id,
                _text(conclusion_mapping.get("correlation_id")) or correlation_id,
                freeze(_safe(conclusion_mapping.get("provenance") or {})),
                _timestamp(conclusion_mapping),
                freeze(_safe({"status": conclusion_mapping.get("status")})),
            )
            add_node(node)
            conclusion_data[conclusion_id] = conclusion_mapping

        def node_for(node_type: str, node_id: str) -> InvestigationNode | None:
            return nodes.get((node_type, node_id))

        def timeline_ioc_keys(data: Mapping[str, Any]) -> list[str]:
            candidates = []
            for key in ("ioc_refs", "ioc_ids", "related_iocs", "indicator"):
                candidates.extend(_values(data.get(key)))
            keys = []
            for candidate in candidates:
                candidate_key = _ioc_id(candidate)
                if candidate_key and candidate_key in ioc_nodes:
                    keys.append(candidate_key)
                    continue
                text_candidate = _text(candidate)
                if not text_candidate:
                    continue
                if text_candidate.startswith("IOC:") and text_candidate in ioc_nodes:
                    keys.append(text_candidate)
                    continue
                exact_matches = [
                    key
                    for key in ioc_nodes
                    if key.rsplit(":", 1)[-1] == text_candidate
                ]
                if len(exact_matches) == 1:
                    keys.append(exact_matches[0])
            return list(dict.fromkeys(keys))

        for finding_id, data in finding_data.items():
            finding = node_for(InvestigationNodeType.FINDING.value, finding_id)
            if finding is None:
                continue
            evidence_refs = _references(data, "evidence_refs", "evidence_references")
            mitre_refs = _references(data, "mitre_techniques", "mitre", "techniques")
            provider_refs = _references(data, "provider_observation_refs", "provider_observation_references")
            finding_provenance = data.get("intelligence_provenance") or data.get("provenance") or {}
            finding_confidence = data.get("confidence")

            for reference in evidence_refs:
                evidence_node = node_for(InvestigationNodeType.EVIDENCE.value, reference)
                if evidence_node is not None:
                    add_relationship(
                        source=evidence_node,
                        target=finding,
                        relationship_type=InvestigationRelationshipType.EVIDENCE_SUPPORTS_FINDING.value,
                        evidence_refs=(reference,),
                        provenance=evidence_node.provenance,
                        timestamp=evidence_node.timestamp or finding.timestamp,
                        confidence=finding_confidence,
                    )
                    add_relationship(
                        source=finding,
                        target=evidence_node,
                        relationship_type=InvestigationRelationshipType.FINDING_SUPPORTED_BY_EVIDENCE.value,
                        evidence_refs=(reference,),
                        provenance=finding_provenance,
                        timestamp=finding.timestamp or evidence_node.timestamp,
                        confidence=finding_confidence,
                    )
                provider_node = provider_by_evidence.get(reference)
                if provider_node is not None:
                    add_relationship(
                        source=provider_node,
                        target=finding,
                        relationship_type=InvestigationRelationshipType.PROVIDER_OBSERVATION_SUPPORTS_FINDING.value,
                        evidence_refs=(reference,),
                        provenance=provider_node.provenance,
                        timestamp=provider_node.timestamp or finding.timestamp,
                        confidence=finding_confidence,
                    )

            for reference in provider_refs:
                provider_node = node_for(InvestigationNodeType.PROVIDER_OBSERVATION.value, reference)
                if provider_node is not None:
                    refs = [ref for ref, source in provider_by_evidence.items() if source == provider_node]
                    add_relationship(
                        source=provider_node,
                        target=finding,
                        relationship_type=InvestigationRelationshipType.PROVIDER_OBSERVATION_SUPPORTS_FINDING.value,
                        evidence_refs=refs,
                        provenance=provider_node.provenance,
                        timestamp=provider_node.timestamp or finding.timestamp,
                        confidence=finding_confidence,
                    )

            for technique in mitre_refs:
                technique_id = _text(technique)
                if not technique_id:
                    continue
                mitre = node_for(InvestigationNodeType.MITRE_TECHNIQUE.value, technique_id)
                if mitre is None:
                    mitre = InvestigationNode(
                        InvestigationNodeType.MITRE_TECHNIQUE.value,
                        technique_id,
                        tenant,
                        case,
                        actor_id=actor_id,
                        correlation_id=correlation_id,
                        provenance=freeze(_safe(finding_provenance)),
                        metadata=freeze({"technique_id": technique_id}),
                    )
                    add_node(mitre)
                add_relationship(
                    source=finding,
                    target=mitre,
                    relationship_type=InvestigationRelationshipType.FINDING_REFERENCES_MITRE.value,
                    evidence_refs=evidence_refs,
                    provenance=finding_provenance,
                    timestamp=finding.timestamp,
                    confidence=finding_confidence,
                )

            for recommendation_id in _references(data, "recommendation_refs", "recommendation_ids"):
                recommendation = node_for(InvestigationNodeType.RECOMMENDATION.value, recommendation_id)
                if recommendation is not None:
                    add_relationship(
                        source=finding,
                        target=recommendation,
                        relationship_type=InvestigationRelationshipType.FINDING_SUPPORTS_RECOMMENDATION.value,
                        evidence_refs=evidence_refs,
                        provenance=finding_provenance,
                        timestamp=finding.timestamp or recommendation.timestamp,
                        confidence=finding_confidence,
                    )

            for conclusion_id in _references(data, "conclusion_refs", "conclusion_ids"):
                conclusion_node = node_for(InvestigationNodeType.CONCLUSION.value, conclusion_id)
                if conclusion_node is not None:
                    add_relationship(
                        source=finding,
                        target=conclusion_node,
                        relationship_type=InvestigationRelationshipType.FINDING_SUPPORTS_CONCLUSION.value,
                        evidence_refs=evidence_refs,
                        provenance=finding_provenance,
                        timestamp=finding.timestamp or conclusion_node.timestamp,
                        confidence=finding_confidence,
                    )

            for event_id, event in timeline_data.items():
                event_finding_refs = _references(event, "finding_refs", "finding_ids", "finding_id")
                event_ioc_refs = timeline_ioc_keys(event)
                event_node = node_for(InvestigationNodeType.TIMELINE_EVENT.value, event_id)
                if event_node is None:
                    continue
                if finding_id in event_finding_refs:
                    add_relationship(
                        source=event_node,
                        target=finding,
                        relationship_type=InvestigationRelationshipType.TIMELINE_SUPPORTS_FINDING.value,
                        evidence_refs=_references(event, "evidence_refs", "evidence_references"),
                        provenance=event.get("provenance") or {},
                        timestamp=event_node.timestamp or finding.timestamp,
                        confidence=_confidence(event.get("confidence")),
                    )
                for ioc_key in event_ioc_refs:
                    ioc_node = node_for(InvestigationNodeType.IOC.value, ioc_key)
                    if ioc_node is not None:
                        add_relationship(
                            source=ioc_node,
                            target=event_node,
                            relationship_type=InvestigationRelationshipType.IOC_APPEARS_IN_TIMELINE.value,
                            evidence_refs=_references(event, "evidence_refs", "evidence_references"),
                            provenance=event.get("provenance") or {},
                            timestamp=event_node.timestamp,
                        )

        for recommendation_id, data in recommendation_data.items():
            recommendation = node_for(InvestigationNodeType.RECOMMENDATION.value, recommendation_id)
            for finding_id in _references(data, "finding_refs", "finding_ids", "related_finding_ids"):
                finding = node_for(InvestigationNodeType.FINDING.value, finding_id)
                if finding is not None:
                    add_relationship(
                        source=finding,
                        target=recommendation,
                        relationship_type=InvestigationRelationshipType.FINDING_SUPPORTS_RECOMMENDATION.value,
                        evidence_refs=_references(data, "evidence_refs", "evidence_references"),
                        provenance=data.get("provenance") or finding.provenance,
                        timestamp=finding.timestamp or recommendation.timestamp,
                        confidence=_confidence(data.get("confidence")),
                    )

        for conclusion_id, data in conclusion_data.items():
            conclusion_node = node_for(InvestigationNodeType.CONCLUSION.value, conclusion_id)
            for finding_id in _references(data, "finding_refs", "finding_ids", "related_finding_ids"):
                finding = node_for(InvestigationNodeType.FINDING.value, finding_id)
                if finding is not None:
                    add_relationship(
                        source=finding,
                        target=conclusion_node,
                        relationship_type=InvestigationRelationshipType.FINDING_SUPPORTS_CONCLUSION.value,
                        evidence_refs=_references(data, "evidence_refs", "evidence_references"),
                        provenance=data.get("provenance") or finding.provenance,
                        timestamp=finding.timestamp or conclusion_node.timestamp,
                        confidence=_confidence(data.get("confidence")),
                    )

        ordered_nodes = tuple(sorted(nodes.values(), key=lambda item: (item.node_type, item.node_id)))
        ordered_relationships = tuple(
            sorted(
                relationships.values(),
                key=lambda item: (
                    item.tenant_id,
                    item.case_id,
                    item.source_type,
                    item.source_id,
                    item.relationship_type,
                    item.target_type,
                    item.target_id,
                    item.timestamp or "",
                    item.relationship_id,
                ),
            )
        )
        return InvestigationRelationshipGraph(
            tenant_id=tenant,
            case_id=case,
            actor_id=actor_id,
            correlation_id=correlation_id,
            nodes=ordered_nodes,
            relationships=ordered_relationships,
        )


__all__ = [
    "DeterministicRelationshipBuilder",
    "InvestigationNode",
    "InvestigationNodeType",
    "InvestigationRelationship",
    "InvestigationRelationshipGraph",
    "InvestigationRelationshipType",
    "project_relationship_graph",
]
