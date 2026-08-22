"""Evidence-linked, analyst-safe explainability projections.

This module is deliberately read-only. It does not reproduce investigator
reasoning or expose private model chain-of-thought; it presents auditable
decision factors already present in canonical investigation records.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

from services.core.serialization import serialize


SENSITIVE = {"password", "token", "secret", "api_key", "authorization", "credential", "private_key"}


def _safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items() if str(k).lower() not in SENSITIVE and not str(k).startswith("_")}
    if isinstance(value, (list, tuple, set)):
        return [_safe(item) for item in value]
    return value


def _items(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple, set)) else ([] if value is None else [value])


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _unit(value: Any) -> float | None:
    number = _number(value)
    if number is None:
        return None
    return max(0.0, min(1.0, number / 100.0 if number > 1 else number))


def _timestamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


class ExplainabilityProjectionBuilder:
    VERSION = "investigation-explainability-v1"
    CONFIDENCE_VERSION = "investigation-confidence-decomposition-v1"
    DECISION_VERSION = "investigation-decision-support-v1"
    PRODUCTIVITY_VERSION = "investigation-productivity-v1"

    def build(self, view: dict[str, Any], *, audit_timeline=None, now=None) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        investigation = view.get("investigation") or {}
        summary = view.get("summary") or {}
        findings = [item for item in view.get("findings", []) if isinstance(item, dict)]
        evidence = [self._evidence(item) for item in view.get("evidence", []) if isinstance(item, dict)]
        iocs = [self._ioc(item) for item in view.get("iocs", []) if isinstance(item, dict)]
        mitre = [self._mitre(item) for item in view.get("mitre", []) if isinstance(item, dict)]
        observations = [self._observation(item) for item in view.get("provider_observations", []) if isinstance(item, dict)]
        evidence_ids = {item["evidence_id"] for item in evidence}
        support, contradictions = self._factors(findings, evidence_ids)
        confidence = self._confidence(evidence, findings, observations, mitre, contradictions, view.get("quality") or {})
        reasoning = self._reasoning(summary, support, contradictions, evidence_ids, iocs, mitre)
        intelligence = self._intelligence(iocs, observations, now=now)
        decision_support = self._decision_support(summary, evidence, support, contradictions, intelligence, mitre, confidence)
        timeline = self._timeline(view.get("timeline", []), audit_timeline or [], evidence_ids)
        return {
            "version": self.VERSION,
            "investigation": {"case_id": investigation.get("case_id"), "investigation_id": investigation.get("id") or investigation.get("investigation_id"), "tenant_id": investigation.get("tenant_id"), "status": investigation.get("status")},
            "conclusion": reasoning,
            "confidence_decomposition": confidence,
            "evidence": evidence,
            "threat_intelligence": intelligence,
            "mitre": mitre,
            "timeline": timeline,
            "decision_support": decision_support,
            "provenance": {"projection": self.VERSION, "source": "canonical_investigation_read_model", "evidence_first": True},
        }

    @staticmethod
    def _evidence(item):
        value = _safe(item)
        evidence_id = str(value.get("evidence_id") or value.get("id") or value.get("artifact_id") or value.get("reference") or value.get("reference_id") or "")
        refs = value.get("finding_refs") or value.get("finding_references") or []
        return {"evidence_id": evidence_id, "case_id": value.get("case_id"), "type": value.get("type", value.get("artifact_type", "unknown")), "source": value.get("source", "unknown"), "collected_at": value.get("timestamp") or value.get("created_at") or value.get("observed_at"), "integrity": value.get("integrity") or value.get("integrity_metadata") or {"status": "unavailable"}, "provenance": value.get("provenance") or {}, "confidence": _unit(value.get("confidence", value.get("confidence_score"))), "relevance": _unit(value.get("relevance", value.get("relevance_score"))), "finding_refs": [str(ref) for ref in _items(refs) if ref], "ioc_refs": [str(ref) for ref in _items(value.get("ioc_refs", value.get("ioc_references", []))) if ref], "timeline_refs": [str(ref) for ref in _items(value.get("timeline_refs", [])) if ref], "mitre_refs": [str(ref) for ref in _items(value.get("mitre_refs", value.get("mitre_techniques", []))) if ref], "review_state": value.get("review_state", "unreviewed")}

    @staticmethod
    def _ioc(item):
        value = _safe(item)
        return {"indicator": value.get("value", value.get("indicator", "")), "type": value.get("ioc_type", value.get("type", "unknown")), "provider": value.get("provider", value.get("source", "unknown")), "reputation": value.get("reputation", value.get("verdict")), "confidence": _unit(value.get("confidence", value.get("confidence_score"))), "freshness": value.get("freshness"), "first_seen": value.get("first_seen"), "last_seen": value.get("last_seen"), "verdict": value.get("verdict", value.get("status")), "evidence_refs": [str(ref) for ref in _items(value.get("evidence_refs", value.get("evidence_references", []))) if ref], "provenance": value.get("provenance") or {}}

    @staticmethod
    def _observation(item):
        value = _safe(item)
        return {key: value.get(key) for key in ("provider", "status", "availability_state", "confidence", "latency_ms", "observed_at", "timestamp", "policy_decision", "unavailable_reason", "provenance") if value.get(key) is not None}

    @staticmethod
    def _mitre(item):
        value = _safe(item)
        return {"technique_id": value.get("technique_id", value.get("id")), "technique": value.get("name", value.get("technique", value.get("technique_id"))), "subtechnique": value.get("subtechnique", value.get("sub_technique")), "tactic": value.get("tactic", value.get("tactics")), "evidence_refs": [str(ref) for ref in _items(value.get("evidence_refs", value.get("evidence_references", value.get("evidence", [])))) if ref], "confidence": _unit(value.get("confidence", value.get("confidence_score"))), "reasoning_factor": value.get("reasoning_factor", value.get("reason")), "detection_relevance": value.get("detection_relevance")}

    @staticmethod
    def _factors(findings, evidence_ids):
        support, contradictions = [], []
        for item in findings:
            refs = [str(ref) for ref in _items(item.get("evidence_refs", item.get("evidence_references", item.get("evidence", [])))) if str(ref) in evidence_ids]
            factor = {"finding_id": item.get("finding_id") or item.get("id"), "factor": item.get("finding") or item.get("title") or item.get("description"), "evidence_refs": refs, "confidence": _unit(item.get("confidence", item.get("confidence_score"))), "provenance": _safe(item.get("provenance", {}))}
            is_contradiction = bool(item.get("contradiction") or item.get("contradicting") or item.get("is_contradiction"))
            (contradictions if is_contradiction else support).append(factor)
        return support, contradictions

    def _confidence(self, evidence, findings, observations, mitre, contradictions, quality):
        components = {}
        evidence_values = [item["confidence"] for item in evidence if item.get("confidence") is not None]
        if evidence_values: components["evidence_quality"] = round(mean(evidence_values), 4)
        if evidence:
            linked = sum(bool(item.get("finding_refs") or item.get("ioc_refs") or item.get("mitre_refs")) for item in evidence)
            components["evidence_coverage"] = round(linked / len(evidence), 4)
        intel_values = [item.get("confidence") for item in observations + [{"confidence": item.get("confidence")} for item in []] if _unit(item.get("confidence")) is not None]
        if intel_values: components["threat_intelligence_confidence"] = round(mean(_unit(value) for value in intel_values), 4)
        if observations:
            usable = [item for item in observations if str(item.get("status", item.get("availability_state", ""))).upper() not in {"UNAVAILABLE", "FAILED", "BLOCKED"}]
            components["corroboration"] = round(len(usable) / len(observations), 4)
        timestamps = [_timestamp(item.get("collected_at")) for item in evidence if item.get("collected_at")]
        if len(timestamps) >= 2: components["temporal_consistency"] = 1.0 if timestamps == sorted(timestamps) else 0.5
        if mitre: components["mitre_alignment"] = round(sum(bool(item.get("evidence_refs")) for item in mitre) / len(mitre), 4)
        penalty = round(min(1.0, len(contradictions) / max(1, len(findings))), 4)
        components["contradiction_penalty"] = penalty
        if not components:
            overall = None
        else:
            positive = {key: value for key, value in components.items() if key != "contradiction_penalty"}
            overall = round(max(0.0, min(1.0, (mean(list(positive.values())) if positive else 0.0) - penalty * 0.2)), 4)
        return {"version": self.CONFIDENCE_VERSION, "overall_confidence": overall, "display_percent": round(overall * 100, 2) if overall is not None else None, "components": components, "formula": "mean(available positive components) - contradiction_penalty * 0.2", "missing_components": [key for key in ("evidence_quality", "evidence_coverage", "threat_intelligence_confidence", "corroboration", "temporal_consistency", "mitre_alignment") if key not in components], "bounded": True}

    @staticmethod
    def _reasoning(summary, support, contradictions, evidence_ids, iocs, mitre):
        conclusion = summary.get("decision") or summary.get("verdict") or "Needs analyst review"
        return {"conclusion": conclusion, "risk": summary.get("risk"), "confidence": summary.get("confidence"), "supporting_factors": support, "contradicting_factors": contradictions, "evidence_references": sorted({ref for factor in support + contradictions for ref in factor.get("evidence_refs", [])}), "threat_intelligence_references": [item.get("indicator") for item in iocs if item.get("indicator")], "mitre_references": [item.get("technique_id") for item in mitre if item.get("technique_id")], "uncertainty": ["No linked evidence" if not evidence_ids else "Contradictory factors require analyst review" if contradictions else "Model conclusion is advisory and bounded to available evidence"]}

    @staticmethod
    def _intelligence(iocs, observations, *, now):
        providers = sorted({str(item.get("provider")) for item in iocs if item.get("provider") and item.get("provider") != "unknown"} | {str(item.get("provider")) for item in observations if item.get("provider")})
        statuses = [str(item.get("status", item.get("availability_state", ""))).upper() for item in observations]
        stale = []
        for item in iocs:
            timestamp = _timestamp(item.get("last_seen"))
            if timestamp and timestamp < now - timedelta(days=30): stale.append(item.get("indicator"))
        verdicts = {}
        for item in iocs:
            if item.get("indicator") and item.get("verdict") is not None:
                verdicts.setdefault(str(item["indicator"]), set()).add(str(item["verdict"]))
        conflicts = [{"indicator": indicator, "verdicts": sorted(values), "reason": "provider verdict disagreement"} for indicator, values in verdicts.items() if len(values) > 1]
        return {"version": "threat-intelligence-visualization-v1", "indicators": iocs, "provider_observations": observations, "providers": providers, "provider_agreement": {"observation_count": len(observations), "available_count": sum(status not in {"UNAVAILABLE", "FAILED", "BLOCKED"} for status in statuses), "unavailable_count": sum(status in {"UNAVAILABLE", "FAILED", "BLOCKED"} for status in statuses)}, "stale_indicators": [item for item in stale if item], "conflicts": conflicts, "safe_payload": True}

    @staticmethod
    def _decision_support(summary, evidence, support, contradictions, intelligence, mitre, confidence):
        recommendations = []
        if not evidence: recommendations.append({"action": "review_evidence", "reason": "No evidence references are available", "advisory_only": True})
        if contradictions: recommendations.append({"action": "review_contradictions", "reason": "Contradictory factors are present", "advisory_only": True})
        if intelligence.get("stale_indicators"): recommendations.append({"action": "enrich_ioc", "reason": "Threat intelligence is stale", "advisory_only": True})
        if not mitre: recommendations.append({"action": "validate_mitre_mapping", "reason": "No evidence-linked ATT&CK mapping is available", "advisory_only": True})
        if confidence.get("overall_confidence") is not None and confidence["overall_confidence"] < 0.6: recommendations.append({"action": "request_additional_evidence", "reason": "Confidence is below the review threshold", "advisory_only": True})
        if not recommendations: recommendations.append({"action": "review_and_disposition", "reason": "Evidence-backed assessment is ready for analyst decision", "advisory_only": True})
        return {"version": ExplainabilityProjectionBuilder.DECISION_VERSION, "current_assessment": {"risk": summary.get("risk"), "confidence": summary.get("confidence"), "disposition": summary.get("decision") or "requires_review"}, "evidence_strength": {"supporting_count": len(support), "contradicting_count": len(contradictions), "evidence_count": len(evidence), "stale_intelligence_count": len(intelligence.get("stale_indicators", []))}, "recommended_actions": recommendations, "uncertainty": confidence.get("missing_components", []) + (["contradictory_evidence"] if contradictions else []), "destructive_actions": False}

    @staticmethod
    def _timeline(technical, audit, evidence_ids):
        events = []
        for item in _items(technical):
            if isinstance(item, dict): events.append({"kind": "technical", "event": item.get("event") or item.get("stage") or item.get("event_type", "technical_event"), "timestamp": item.get("timestamp") or item.get("created_at"), "evidence_refs": [str(ref) for ref in _items(item.get("evidence_refs", item.get("evidence_references", []))) if str(ref) in evidence_ids], "provenance": _safe(item.get("provenance", {}))})
        for item in _items(audit):
            if isinstance(item, dict): events.append({"kind": "analyst" if str(item.get("event", "")).startswith(("analyst_", "disposition", "evidence_review", "assignment", "escalation")) else "technical", "event": item.get("event", "audit_event"), "timestamp": item.get("timestamp"), "actor_id": item.get("actor_id"), "evidence_refs": [str(ref) for ref in _items(item.get("evidence_refs", [])) if str(ref) in evidence_ids], "state": item.get("new_state", item.get("state"))})
        return sorted(events, key=lambda item: (str(item.get("timestamp") or ""), str(item.get("event") or "")))

    def productivity(self, coordinator, *, tenant_id: str, now=None):
        reports = coordinator.report_repository.list_for_tenant(str(tenant_id))
        cases = {str(item.get("case_id")) for item in reports if isinstance(item, dict) and item.get("case_id")}
        reviews = coordinator.evidence_review_repository.list_for_tenant(tenant_id=str(tenant_id))
        feedback = coordinator.feedback_repository.list_for_investigation(str(tenant_id), "") if False else []
        escalations = 0
        reopened = 0
        for case_id in cases:
            events = coordinator.case_lifecycle_repository.list_for_case(case_id, tenant_id=str(tenant_id))
            escalations += sum(item.get("event_kind") == "escalation" for item in events)
            reopened += sum(item.get("event_kind") == "case_reopened" for item in events)
        return {"version": self.PRODUCTIVITY_VERSION, "tenant_id": str(tenant_id), "investigations_handled": len(cases), "evidence_reviewed": sum(item.get("new_state") in {"reviewed", "accepted", "rejected", "completed"} for item in reviews), "escalations": escalations, "reopened_cases": reopened, "workload_scope": "tenant", "punitive_scoring": False, "derived_from": "canonical_case_lifecycle_and_evidence_review_records"}
