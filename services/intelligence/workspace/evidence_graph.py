"""Deterministic, tenant-safe evidence graph and export projections."""
from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean, median
from typing import Any


_SECRET_KEYS = {"password", "secret", "token", "access_token", "refresh_token", "api_key", "authorization", "credential", "private_key", "database_path", "internal_path", "connection_string"}


def _safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items() if str(k).lower() not in _SECRET_KEYS and not str(k).startswith("_")}
    if isinstance(value, (list, tuple, set)):
        return [_safe(v) for v in value]
    return value


def _items(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple, set)) else ([] if value is None else [value])


def _bounded_items(value: Any, limit: int = 2000) -> list[Any]:
    """Cap untrusted projection collections before graph expansion."""
    return _items(value)[: max(1, min(2000, int(limit)))]


def _refs(value: Any) -> list[str]:
    return sorted({str(v) for v in _items(value) if v is not None and str(v)})


class EvidenceGraphProjectionBuilder:
    VERSION = "evidence-graph-v1"
    MAX_NODES = 500
    MAX_EDGES = 1000
    MAX_INPUT_ITEMS = 2000

    def build(self, view: dict[str, Any], explainability: dict[str, Any] | None = None, audit_timeline=None, approval=None) -> dict[str, Any]:
        exp = explainability or {}
        investigation = view.get("investigation") or {}
        case_id = str(investigation.get("case_id") or investigation.get("id") or "")
        nodes: dict[tuple[str, str], dict[str, Any]] = {}
        edges: dict[tuple[str, str, str], dict[str, Any]] = {}

        def node(kind: str, identifier: Any, label: Any = None, **data: Any) -> str:
            identifier = str(identifier or "")
            if not identifier:
                return ""
            key = (kind, identifier)
            nodes.setdefault(key, {"id": f"{kind}:{identifier}", "kind": kind, "label": str(label or identifier), "data": _safe(data)})
            return nodes[key]["id"]

        def edge(source: str, target: str, relation: str, source_ref: Any = None, **data: Any) -> None:
            if not source or not target or source == target:
                return
            key = (source, target, relation)
            edges.setdefault(key, {"id": f"{source}|{relation}|{target}", "source": source, "target": target, "type": relation, "provenance": _safe({"source": source_ref or "canonical_investigation_read_model", **data})})

        inv = node("investigation", case_id, case_id, status=investigation.get("status"))
        report = (view.get("report") or {}) if isinstance(view.get("report"), dict) else {}
        alert_id = report.get("alert_id") or report.get("metadata", {}).get("alert_id")
        if alert_id:
            alert = node("alert", alert_id, alert_id, source="canonical_investigation_read_model")
            edge(inv, alert, "investigation_alert", "report.alert_id")
        for item in _bounded_items(view.get("evidence", []), self.MAX_INPUT_ITEMS):
            if not isinstance(item, dict): continue
            eid = item.get("evidence_id") or item.get("id") or item.get("reference")
            en = node("evidence", eid, item.get("type") or item.get("artifact_type") or eid, source=item.get("source"), integrity=item.get("integrity"), provenance=item.get("provenance"))
            edge(inv, en, "investigation_evidence", "read_model.evidence")
            for ref in _refs(item.get("finding_refs") or item.get("finding_references") or item.get("evidence_refs")):
                fn = node("finding", ref, ref)
                edge(en, fn, "evidence_finding", "evidence.finding_refs")
            for ref in _refs(item.get("ioc_refs") or item.get("ioc_references")):
                inn = node("ioc", ref, ref)
                edge(en, inn, "evidence_ioc", "evidence.ioc_refs")
            for ref in _refs(item.get("mitre_refs") or item.get("mitre_techniques")):
                mn = node("mitre_technique", ref, ref)
                edge(en, mn, "evidence_mitre", "evidence.mitre_refs")
            for ref in _refs(item.get("timeline_refs")):
                tn = node("timeline_event", ref, ref)
                edge(en, tn, "evidence_timeline", "evidence.timeline_refs")
        for item in _bounded_items(view.get("findings", []), self.MAX_INPUT_ITEMS):
            if not isinstance(item, dict): continue
            fid = item.get("finding_id") or item.get("id") or item.get("finding")
            fn = node("finding", fid, item.get("finding") or item.get("title") or fid, confidence=item.get("confidence"))
            for ref in _refs(item.get("evidence_refs") or item.get("evidence_references") or item.get("evidence")):
                en = node("evidence", ref, ref)
                edge(en, fn, "evidence_finding", "finding.evidence_refs")
        for item in _bounded_items(exp.get("threat_intelligence", {}).get("indicators", []), self.MAX_INPUT_ITEMS):
            if not isinstance(item, dict): continue
            indicator = item.get("indicator")
            inn = node("ioc", indicator, indicator, type=item.get("type"), verdict=item.get("verdict"))
            for ref in _refs(item.get("evidence_refs")):
                edge(node("evidence", ref, ref), inn, "evidence_ioc", "threat_intelligence.indicators")
            provider = item.get("provider")
            if provider:
                obs = node("threat_intelligence_observation", f"{indicator}:{provider}", provider, provider=provider, verdict=item.get("verdict"), confidence=item.get("confidence"))
                edge(inn, obs, "ioc_intelligence_observation", "threat_intelligence.indicators")
        for item in _bounded_items(exp.get("mitre", []), self.MAX_INPUT_ITEMS):
            if not isinstance(item, dict): continue
            tid = item.get("technique_id") or item.get("technique")
            mn = node("mitre_technique", tid, item.get("technique") or tid, tactic=item.get("tactic"), confidence=item.get("confidence"))
            for ref in _refs(item.get("evidence_refs")):
                edge(node("evidence", ref, ref), mn, "evidence_mitre", "mitre.evidence_refs")
            tactic = item.get("tactic")
            if tactic:
                tn = node("mitre_tactic", tactic, tactic)
                edge(mn, tn, "technique_tactic", "mitre.tactic")
        for item in _bounded_items(exp.get("timeline", []), self.MAX_INPUT_ITEMS):
            if not isinstance(item, dict): continue
            tid = item.get("event_id") or f"{item.get('timestamp','')}:{item.get('event','')}"
            tn = node("timeline_event", tid, item.get("event") or tid, timestamp=item.get("timestamp"), event_kind=item.get("kind"))
            for ref in _refs(item.get("evidence_refs")):
                edge(node("evidence", ref, ref), tn, "evidence_timeline", "timeline.evidence_refs")
        for factor_type, factors in (("supporting_factor", exp.get("conclusion", {}).get("supporting_factors", [])), ("contradicting_factor", exp.get("conclusion", {}).get("contradicting_factors", []))):
            for index, factor in enumerate(_bounded_items(factors, self.MAX_INPUT_ITEMS)):
                if not isinstance(factor, dict): continue
                fid = factor.get("finding_id") or f"{case_id}:{factor_type}:{index}"
                fn = node(factor_type, fid, factor.get("factor") or fid, confidence=factor.get("confidence"))
                for ref in _refs(factor.get("evidence_refs")):
                    edge(node("evidence", ref, ref), fn, f"evidence_{factor_type}", "explainability.conclusion")
        for item in _bounded_items(view.get("recommendations", []), self.MAX_INPUT_ITEMS):
            if not isinstance(item, dict): continue
            rid = item.get("recommendation_id") or item.get("id") or item.get("recommendation")
            rn = node("decision_support_recommendation", rid, item.get("recommendation") or item.get("action") or rid, advisory_only=True)
            edge(inv, rn, "investigation_recommendation", "read_model.recommendations")
            for ref in _refs(item.get("evidence_refs")):
                edge(rn, node("evidence", ref, ref), "recommendation_evidence", "recommendation.evidence_refs")
        if approval:
            dn = node("analyst_disposition", approval.get("event_id") or f"{case_id}:disposition", approval.get("state"), actor_id=approval.get("actor_id"), timestamp=approval.get("created_at"))
            edge(inv, dn, "investigation_disposition", "case_lifecycle.report_approval")
        rn = node("report", f"{case_id}:report", "Investigation report", approval_state=(approval or {}).get("state"))
        edge(inv, rn, "investigation_report", "canonical_report_and_approval")
        ordered_nodes = sorted(nodes.values(), key=lambda x: (x["kind"], x["id"]))[: self.MAX_NODES]
        allowed = {item["id"] for item in ordered_nodes}
        ordered_edges = sorted((item for item in edges.values() if item["source"] in allowed and item["target"] in allowed), key=lambda x: (x["source"], x["type"], x["target"]))[: self.MAX_EDGES]
        return {"version": self.VERSION, "case_id": case_id, "investigation_id": investigation.get("id") or case_id, "nodes": ordered_nodes, "edges": ordered_edges, "statistics": {"node_count": len(ordered_nodes), "edge_count": len(ordered_edges), "node_types": {kind: sum(n["kind"] == kind for n in ordered_nodes) for kind in sorted({n["kind"] for n in ordered_nodes})}, "bounded": True}, "provenance": {"projection": self.VERSION, "source": "canonical_investigation_read_model", "tenant_scoped": True}}


class EvidenceGraphWorkspaceProjectionBuilder:
    """Presentation projection for bounded, interactive graph exploration."""

    VERSION = "evidence-graph-workspace-v1"

    def build(self, graph: dict[str, Any], contradictions: dict[str, Any] | None = None) -> dict[str, Any]:
        edges = list(graph.get("edges", []))
        degree = {}
        for edge in edges:
            degree[edge.get("source")] = degree.get(edge.get("source"), 0) + 1
            degree[edge.get("target")] = degree.get(edge.get("target"), 0) + 1
        contradiction_refs = {str(ref) for item in (contradictions or {}).get("items", []) for ref in (item.get("evidence_a"), item.get("evidence_b")) if ref}
        nodes = []
        for item in graph.get("nodes", []):
            value = dict(item)
            value["selectable"] = True
            value["relationship_count"] = degree.get(item.get("id"), 0)
            value["highlight"] = "contradiction" if str(item.get("id", "")).split(":", 1)[-1] in contradiction_refs else "normal"
            nodes.append(value)
        return {"version": self.VERSION, "graph_version": graph.get("version"), "case_id": graph.get("case_id"), "nodes": nodes, "edges": edges, "interaction": {"bounded_expansion": True, "selection": "node_and_relationship", "drilldown": {"evidence": "evidence-drilldown-v1", "intelligence": "threat-intelligence-visualization-v1", "mitre": "evidence-graph-v1"}}, "empty_state": not bool(nodes), "provenance": {"source": graph.get("provenance", {}).get("source", "canonical_investigation_read_model"), "presentation_only": True}}


class EvidenceComparisonProjectionBuilder:
    VERSION = "evidence-comparison-v1"

    def build(self, case_id: str, view: dict[str, Any], evidence_a: str, evidence_b: str) -> dict[str, Any]:
        def find(identifier):
            return next((item for item in view.get("evidence", []) if isinstance(item, dict) and str(item.get("evidence_id") or item.get("id") or item.get("reference")) == str(identifier)), None)
        a, b = find(evidence_a), find(evidence_b)
        if not a or not b:
            raise LookupError("evidence_not_found")
        fields = ("type", "source", "timestamp", "created_at", "integrity", "provenance", "review_state", "confidence", "relevance")
        differences = [field for field in fields if _safe(a.get(field)) != _safe(b.get(field))]
        shared = sorted(set(_refs(a.get("finding_refs") or a.get("evidence_refs"))) & set(_refs(b.get("finding_refs") or b.get("evidence_refs"))))
        return {"version": self.VERSION, "case_id": str(case_id), "evidence_a": _safe(a), "evidence_b": _safe(b), "comparison": {"shared_references": shared, "differences": differences, "corroborating": bool(shared), "contradictory": any(field in differences for field in ("integrity", "source", "timestamp")), "missing_information": [field for field in fields if not a.get(field) or not b.get(field)]}, "provenance": {"projection": self.VERSION, "source": "canonical_investigation_read_model"}}


class ContradictionProjectionBuilder:
    VERSION = "investigation-contradictions-v1"

    def build(self, case_id: str, explainability: dict[str, Any], view: dict[str, Any]) -> dict[str, Any]:
        items = []
        factors = explainability.get("conclusion", {}).get("contradicting_factors", [])
        for index, factor in enumerate(factors or []):
            if not isinstance(factor, dict): continue
            refs = _refs(factor.get("evidence_refs"))
            items.append({"contradiction_id": f"{case_id}:contradiction:{index}", "evidence_a": refs[0] if refs else None, "evidence_b": refs[1] if len(refs) > 1 else None, "conflicting_attributes": ["finding"], "impact": "confidence_reduction", "confidence_impact": explainability.get("confidence_decomposition", {}).get("components", {}).get("contradiction_penalty", 0), "resolution_state": "detected", "analyst_review_state": "unreviewed", "recommendation": "review_contradiction", "factor": factor.get("factor"), "provenance": {"source": "explainability.conclusion.contradicting_factors"}})
        return {"version": self.VERSION, "case_id": str(case_id), "items": sorted(items, key=lambda x: x["contradiction_id"]), "count": len(items), "deterministic": True}


class InvestigationReportExportBuilder:
    VERSION = "investigation-report-v1"

    def build(self, case_id: str, view: dict[str, Any], explainability: dict[str, Any], graph: dict[str, Any], audit_timeline=None, approval_history=None) -> dict[str, Any]:
        summary = view.get("summary") or {}
        approval_history = sorted([_safe(item) for item in (approval_history or []) if isinstance(item, dict)], key=lambda x: (str(x.get("created_at") or ""), str(x.get("event_id") or "")))
        approval = approval_history[-1] if approval_history else None
        return {"version": self.VERSION, "case_id": str(case_id), "executive_summary": {"incident_summary": summary.get("title"), "risk": summary.get("risk"), "confidence": summary.get("confidence"), "conclusion": explainability.get("conclusion", {}).get("conclusion"), "key_findings": _safe(list(view.get("findings", [])))}, "investigation_overview": _safe(view.get("investigation", {})), "evidence_summary": {"inventory": _safe(explainability.get("evidence", [])), "quality": explainability.get("confidence_decomposition", {}).get("components", {}).get("evidence_quality"), "coverage": explainability.get("confidence_decomposition", {}).get("components", {}).get("evidence_coverage")}, "threat_intelligence": _safe(explainability.get("threat_intelligence", {})), "mitre_attack": _safe(explainability.get("mitre", [])), "explainability": _safe({"conclusion": explainability.get("conclusion"), "confidence_decomposition": explainability.get("confidence_decomposition"), "decision_support": explainability.get("decision_support"), "advisory_only": True}), "analyst_decision": {"disposition": summary.get("decision"), "approval_state": approval.get("state") if approval else "draft", "approval_history": approval_history}, "timeline": _safe(explainability.get("timeline", [])), "audit_provenance": {"events": _safe(audit_timeline or []), "provenance": {"source": "canonical_investigation_read_model", "evidence_first": True}}, "evidence_graph": {"version": graph.get("version"), "statistics": graph.get("statistics")}, "deterministic": True, "export_generation": {"volatile": False, "canonical_timestamps_only": True}}


def productivity_latencies(coordinator, tenant_id: str) -> dict[str, Any]:
    """Aggregate review/disposition latency without employee surveillance."""
    reports = coordinator.report_repository.list_for_tenant(str(tenant_id))
    cases = sorted({str(item.get("case_id")) for item in reports if isinstance(item, dict) and item.get("case_id")})
    first_review, disposition = [], []
    reviewed = 0
    for case_id in cases:
        events = coordinator.get_audit_timeline(case_id, type("Context", (), {"tenant_id": str(tenant_id)})())
        timestamps = []
        for event in events:
            try: timestamps.append(datetime.fromisoformat(str(event.get("timestamp")).replace("Z", "+00:00")))
            except (TypeError, ValueError): pass
        if not timestamps: continue
        start = min(timestamps)
        reviews = [event for event in events if event.get("event") == "evidence_review_changed" and event.get("new_state") in {"reviewed", "accepted", "rejected", "completed"}]
        if reviews:
            reviewed += 1
            try: first_review.append(max(0.0, (datetime.fromisoformat(str(reviews[0]["timestamp"]).replace("Z", "+00:00")) - start).total_seconds()))
            except (TypeError, ValueError, KeyError): pass
        decisions = [event for event in events if event.get("event") == "disposition_changed"]
        if decisions:
            try: disposition.append(max(0.0, (datetime.fromisoformat(str(decisions[0]["timestamp"]).replace("Z", "+00:00")) - start).total_seconds()))
            except (TypeError, ValueError, KeyError): pass
    def stats(values):
        return {"median_seconds": round(median(values), 3) if values else None, "average_seconds": round(mean(values), 3) if values else None, "sample_size": len(values)}
    return {"version": "investigation-productivity-v1", "tenant_id": str(tenant_id), "investigations_handled": len(cases), "first_review_latency": stats(first_review), "disposition_latency": stats(disposition), "review_completion_rate": round(reviewed / len(cases), 4) if cases else None, "workload_scope": "tenant", "punitive_scoring": False, "derived_from": "canonical_audit_and_lifecycle_records"}
