"""Read-only projection from investigation intelligence to analyst workspace data."""

from __future__ import annotations

from typing import Any

from services.core.serialization import serialize

from .models import AnalystWorkspaceV2
from services.intelligence.workspace.explainability_projection import ExplainabilityProjectionBuilder


class AnalystWorkspaceV2Builder:
    """Build an evidence-first workspace projection without becoming a source of truth."""

    def build(
        self,
        report: Any,
        *,
        result: Any = None,
        decision_intelligence: Any = None,
        attack_sequence: Any = None,
        mitre_context: Any = None,
        evidence_metadata: Any = None,
        tenant_id: str | None = None,
        analyst_feedback: Any = None,
        explainability: Any = None,
    ) -> AnalystWorkspaceV2:
        report_data = self._data(report)
        result_data = self._data(result)
        decision = self._data(decision_intelligence) or self._data(report_data.get("decision_intelligence")) or self._data(result_data.get("decision_intelligence"))
        sequence = self._data(attack_sequence) or self._data(report_data.get("attack_sequence")) or self._data(result_data.get("attack_sequence"))
        owner = self._owner(report_data, result_data, decision, sequence)
        if tenant_id and owner and str(tenant_id) != owner:
            raise PermissionError("workspace tenant does not match investigation tenant")
        scoped_tenant = str(tenant_id or owner) if tenant_id or owner else None
        self._validate_component_tenants(scoped_tenant, decision, sequence)

        evidence = self._evidence(
            evidence_metadata if evidence_metadata is not None else report_data.get("evidence", result_data.get("artifacts", [])),
            scoped_tenant,
        )
        evidence_ids = {item["reference_id"] for item in evidence}
        missing = self._missing(sequence, decision)
        timeline = self._timeline(sequence, evidence_ids)
        mitre = self._mitre(mitre_context if mitre_context is not None else report_data.get("mitre", result_data.get("mitre", [])), sequence, evidence_ids)
        confidence = self._confidence(decision, sequence, report_data, result_data)
        risk = self._risk(report_data, result_data)
        investigation_id = str(report_data.get("investigation_id") or result_data.get("investigation_id") or report_data.get("case_id") or result_data.get("case_id") or "") or None
        feedback = self._feedback(analyst_feedback)
        header = self._incident_header(report_data, result_data, decision, scoped_tenant)
        journey = self._journey(report_data, result_data, sequence, decision, evidence, mitre)
        evidence_explanations = self._evidence_explanations(evidence, report_data, result_data, decision)
        intelligence_panel = self._intelligence(report_data, result_data, scoped_tenant)
        attack_story = self._attack_story(sequence, report_data, result_data)
        reasoning_chain = self._reasoning(report_data, result_data, decision, evidence_ids)
        report_sections = self._report_sections(report_data, result_data, decision, sequence, intelligence_panel, attack_story, reasoning_chain, feedback)
        # Keep choices aligned with the canonical AnalystDecision contract.
        analyst_actions = tuple({"action": action, "label": label} for action, label in (("accepted", "Accepted"), ("false_positive", "False positive"), ("escalated", "Escalated"), ("modified", "Modified"), ("rejected", "Rejected")))
        disposition_lifecycle = tuple({"disposition": value, "label": label} for value, label in (("confirmed_threat", "Confirmed threat"), ("benign", "Benign"), ("false_positive", "False positive"), ("requires_review", "Requires review"), ("escalated", "Escalated"), ("closed", "Closed")))
        explainability = explainability if isinstance(explainability, dict) else ExplainabilityProjectionBuilder().build({"investigation": {"id": investigation_id, "case_id": report_data.get("case_id") or result_data.get("case_id"), "tenant_id": scoped_tenant}, "summary": {"decision": decision.get("verdict", decision.get("decision")), "risk": decision.get("risk_score", risk.get("score")), "confidence": decision.get("confidence", confidence.get("score"))}, "findings": report_data.get("findings", result_data.get("findings", [])), "evidence": evidence, "iocs": intelligence_panel.get("observations", []), "mitre": mitre, "timeline": timeline, "provider_observations": intelligence_panel.get("observations", []), "quality": {}}, now=None)

        return AnalystWorkspaceV2(
            investigation={"investigation_id": investigation_id, "case_id": report_data.get("case_id") or result_data.get("case_id"), "tenant_id": scoped_tenant, "status": report_data.get("status") or result_data.get("status", "unknown")},
            incident_header=header,
            journey_stages=tuple(journey),
            verdict_summary={"verdict": decision.get("verdict", decision.get("decision", "unavailable")), "rationale": decision.get("rationale"), "risk_score": decision.get("risk_score"), "source": "decision_intelligence" if decision else "unavailable"},
            confidence_visualization=confidence,
            risk_explanation=risk,
            evidence_references=tuple(evidence),
            evidence_explanations=tuple(evidence_explanations),
            intelligence_panel=intelligence_panel,
            attack_story=attack_story,
            reasoning_chain=tuple(reasoning_chain),
            missing_evidence=tuple(missing),
            attack_sequence_timeline=tuple(timeline),
            mitre_mappings=tuple(mitre),
            report_sections=report_sections,
            analyst_actions=analyst_actions,
            disposition_lifecycle=disposition_lifecycle,
            provenance={"projection": "analyst_workspace_v2", "report_metadata": serialize(report_data.get("metadata", {})), "decision": serialize(decision.get("provenance", {})), "attack_sequence": serialize(sequence.get("provenance", {}))},
            analyst_feedback=feedback,
            explainability=explainability,
            decision_support=explainability.get("decision_support", {}),
        )

    @staticmethod
    def _data(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        if hasattr(value, "to_dict"):
            converted = value.to_dict()
            return dict(converted) if isinstance(converted, dict) else {}
        return {}

    @staticmethod
    def _items(value: Any) -> list[Any]:
        return list(value) if isinstance(value, (list, tuple, set)) else ([] if value is None else [value])

    @staticmethod
    def _owner(report: dict[str, Any], result: dict[str, Any], decision: dict[str, Any], sequence: dict[str, Any]) -> str | None:
        report_context = report.get("tenant_context") if isinstance(report.get("tenant_context"), dict) else {}
        result_context = result.get("tenant_context") if isinstance(result.get("tenant_context"), dict) else {}
        return str(report_context.get("tenant_id") or result_context.get("tenant_id") or decision.get("tenant_id") or sequence.get("tenant_id") or "") or None

    @staticmethod
    def _validate_component_tenants(tenant_id: str | None, *components: dict[str, Any]) -> None:
        if not tenant_id:
            return
        for component in components:
            component_tenant = component.get("tenant_id") if isinstance(component, dict) else None
            if component_tenant and str(component_tenant) != tenant_id:
                raise PermissionError("workspace component tenant does not match investigation tenant")

    def _evidence(self, values: Any, tenant_id: str | None) -> list[dict[str, Any]]:
        items: dict[str, dict[str, Any]] = {}
        for item in self._items(values):
            if not isinstance(item, dict) or (tenant_id and item.get("tenant_id") not in (None, tenant_id)):
                continue
            reference = next((item.get(key) for key in ("evidence_id", "artifact_id", "id", "reference_id", "reference") if item.get(key)), None)
            if not reference:
                continue
            reference_id = str(reference)
            normalized = {
                "reference_id": reference_id,
                "source": item.get("source", "unknown"),
                "type": item.get("type", item.get("artifact_type", "unknown")),
                "metadata": serialize(item.get("metadata", {})),
            }
            for key, value in (("timestamp", item.get("timestamp", item.get("created_at", item.get("observed_at")))), ("confidence", item.get("confidence", item.get("confidence_score"))), ("integrity", serialize(item.get("integrity", item.get("integrity_metadata", {})))), ("provenance", self._provenance(item.get("provenance")))):
                if value not in (None, "", {}): normalized[key] = value
            items.setdefault(reference_id, normalized)
        return [items[key] for key in sorted(items)]

    def _missing(self, sequence: dict[str, Any], decision: dict[str, Any]) -> list[dict[str, Any]]:
        values = [item for item in self._items(sequence.get("missing_evidence")) + self._items(decision.get("missing_evidence")) if isinstance(item, dict)]
        return sorted((serialize(item) for item in values), key=lambda item: (str(item.get("event_id", "")), str(item.get("reason", ""))))

    def _timeline(self, sequence: dict[str, Any], evidence_ids: set[str]) -> list[dict[str, Any]]:
        events = []
        for item in self._items(sequence.get("events")):
            if not isinstance(item, dict):
                continue
            refs = sorted(str(ref) for ref in self._items(item.get("evidence_references")) if str(ref) in evidence_ids)
            # An event without existing evidence references is not promoted into
            # the analyst workspace as evidence-backed activity.
            if not refs:
                continue
            events.append({"event_id": item.get("event_id"), "timestamp": item.get("timestamp"), "stage": item.get("stage"), "description": item.get("description"), "evidence_references": refs, "ioc_references": sorted(str(ref) for ref in self._items(item.get("ioc_references")) if ref), "mitre_techniques": sorted(str(value) for value in self._items(item.get("mitre_techniques")) if value), "confidence": item.get("confidence"), "provenance": serialize(item.get("provenance", {}))})
        return sorted(events, key=lambda item: (str(item.get("timestamp", "")), str(item.get("event_id", ""))))

    def _mitre(self, context: Any, sequence: dict[str, Any], evidence_ids: set[str]) -> list[dict[str, Any]]:
        mapped: dict[str, set[str]] = {}
        for item in self._items(context):
            if isinstance(item, str) and item:
                mapped.setdefault(item, set())
            elif isinstance(item, dict) and item.get("technique_id"):
                mapped.setdefault(str(item["technique_id"]), set()).update(str(ref) for ref in self._items(item.get("evidence_references", item.get("evidence_refs", []))) if str(ref) in evidence_ids)
        for item in self._items(sequence.get("mitre_summary")):
            if isinstance(item, dict) and item.get("technique_id"):
                mapped.setdefault(str(item["technique_id"]), set()).update(str(ref) for ref in self._items(item.get("evidence_references")) if str(ref) in evidence_ids)
        return [{"technique_id": technique, "evidence_references": sorted(refs)} for technique, refs in sorted(mapped.items())]

    @staticmethod
    def _confidence(decision: dict[str, Any], sequence: dict[str, Any], report: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        value = decision.get("confidence", sequence.get("confidence", report.get("confidence", result.get("confidence"))))
        try:
            score = float(value)
            score = score * 100 if 0 <= score <= 1 else score
            score = max(0.0, min(100.0, score))
        except (TypeError, ValueError):
            score = None
        return {"score": score, "scale": "0-100", "source": "decision_intelligence" if decision.get("confidence") is not None else "attack_sequence" if sequence.get("confidence") is not None else "investigation_report"}

    @staticmethod
    def _risk(report: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        risk = report.get("risk") if isinstance(report.get("risk"), dict) else result.get("risk") if isinstance(result.get("risk"), dict) else {}
        return {"score": risk.get("score", report.get("risk_score", result.get("risk_score"))), "severity": risk.get("severity", risk.get("level")), "reasons": serialize(risk.get("reasons", [])), "source": "investigation_report" if isinstance(report.get("risk"), dict) else "investigation_result"}

    def _feedback(self, feedback: Any) -> dict[str, Any]:
        items = [serialize(item) for item in self._items(feedback) if isinstance(item, dict)]
        # Preserve repository order: timestamps are not guaranteed monotonic.
        return {"items": items, "placeholder": {"status": "ready_for_analyst_feedback", "supported_decisions": ["accepted", "rejected", "modified", "false_positive", "escalated"]}}

    @staticmethod
    def _provenance(value: Any) -> dict[str, Any]:
        source = value if isinstance(value, dict) else {"source": value} if value else {}
        return {key: serialize(source.get(key)) for key in ("source", "provider", "reference", "record_id", "status") if source.get(key) is not None}

    @staticmethod
    def _incident_header(report, result, decision, tenant_id):
        risk = report.get("risk") if isinstance(report.get("risk"), dict) else result.get("risk") if isinstance(result.get("risk"), dict) else {}
        return {"incident_id": report.get("case_id") or result.get("case_id"), "title": report.get("title") or "AI Investigation", "severity": report.get("severity") or risk.get("severity", "unknown"), "risk_level": risk.get("level", risk.get("severity", "unknown")), "status": report.get("status") or result.get("status", "unknown"), "assigned_analyst": report.get("assigned_analyst") or result.get("analyst_assignment"), "affected_assets": serialize(report.get("affected_assets", result.get("affected_assets", []))), "affected_users": serialize(report.get("affected_users", result.get("affected_users", []))), "indicators": serialize(report.get("iocs", result.get("iocs", []))), "created_at": report.get("created_at") or result.get("created_at"), "tenant_id": tenant_id}

    @staticmethod
    def _journey(report, result, sequence, decision, evidence, mitre):
        status = str(report.get("status") or result.get("status", "unknown")).lower()
        has_intel = bool(report.get("threat_intelligence") or result.get("threat_intelligence_report"))
        has_attack = bool(sequence.get("events") or report.get("attack_story") or result.get("attack_story"))
        has_reasoning = bool(report.get("reasoning") or result.get("reasoning_report"))
        has_verdict = bool(decision.get("verdict") or decision.get("decision"))
        stages = (("alert_received", "Alert received", True), ("evidence_collected", "Evidence collected", bool(evidence)), ("intelligence_enriched", "Intelligence enriched", has_intel), ("attack_reconstructed", "Attack reconstructed", has_attack), ("mitre_mapped", "MITRE mapped", bool(mitre)), ("ai_verdict_generated", "AI verdict generated", has_reasoning and has_verdict))
        return [{"stage": key, "label": label, "status": "completed" if complete and status in {"completed", "reviewed", "closed"} else "available" if complete else "pending", "timestamp": report.get("created_at") or result.get("created_at"), "confidence": decision.get("confidence")} for key, label, complete in stages]

    def _evidence_explanations(self, evidence, report, result, decision):
        refs = {str(item["reference_id"]): item for item in evidence}
        reasoning = report.get("reasoning_report") if isinstance(report.get("reasoning_report"), dict) else result.get("reasoning_report")
        finding_items = self._items(report.get("findings", result.get("findings", []))) + self._items((reasoning or {}).get("findings")) + self._items(decision.get("supporting_evidence"))
        for finding in finding_items:
            if not isinstance(finding, dict): continue
            for ref in self._items(finding.get("evidence_refs", finding.get("evidence_references", []))):
                if str(ref) in refs: refs[str(ref)]["supports"] = finding.get("title") or finding.get("finding") or finding.get("description")
        return sorted(refs.values(), key=lambda item: item["reference_id"])

    def _intelligence(self, report, result, tenant_id):
        raw = report.get("threat_intelligence") or result.get("threat_intelligence_report") or {}
        data = raw if isinstance(raw, dict) else {"summary": str(raw)}
        observations = []
        for item in self._items(data.get("observations", data.get("provider_results", []))):
            if isinstance(item, dict): observations.append({key: serialize(item.get(key)) for key in ("ioc", "value", "provider", "reputation", "confidence", "status", "availability_state", "latency_ms", "policy_decision", "unavailable_reason", "observed_at", "timestamp", "provenance") if item.get(key) is not None})
        return {"summary": data.get("summary", data.get("disposition", "unavailable")), "observations": observations, "conflicts": serialize(data.get("conflicts", data.get("conflicting_providers", []))), "tenant_id": tenant_id}

    def _attack_story(self, sequence, report, result):
        return {"narrative": sequence.get("attack_story") or report.get("attack_story") or result.get("attack_story") or "No evidence-backed attack story recorded.", "stages": [{"stage": item.get("stage"), "action": item.get("description"), "evidence_references": item.get("evidence_references", []), "confidence": item.get("confidence"), "affected_entity": item.get("affected_entity")} for item in self._items(sequence.get("events")) if isinstance(item, dict)]}

    def _reasoning(self, report, result, decision, evidence_ids):
        raw = report.get("reasoning_report") or report.get("reasoning") or result.get("reasoning_report") or {}
        data = self._data(raw)
        chain = []
        for item in self._items(data.get("findings")):
            if isinstance(item, dict):
                refs = [str(ref) for ref in self._items(item.get("evidence_refs", item.get("evidence_references", []))) if str(ref) in evidence_ids]
                chain.append({"observation": item.get("title") or item.get("description"), "evidence": refs, "reasoning": item.get("reasoning_type") or item.get("description"), "impact": item.get("severity"), "confidence": item.get("confidence")})
        if not chain and decision.get("rationale"): chain.append({"observation": "Investigation conclusion", "evidence": sorted(evidence_ids), "reasoning": decision.get("rationale"), "impact": decision.get("verdict"), "confidence": decision.get("confidence")})
        return chain

    @staticmethod
    def _report_sections(report, result, decision, sequence, intelligence, attack_story, reasoning, feedback):
        return {"executive_summary": report.get("summary") or report.get("analyst_summary") or result.get("summary") or "No executive summary recorded.", "incident_overview": {"status": report.get("status") or result.get("status"), "severity": report.get("severity"), "risk": report.get("risk") or result.get("risk")}, "evidence_summary": {"count": len(report.get("evidence", result.get("artifacts", [])) or [])}, "threat_intelligence": intelligence, "attack_reconstruction": attack_story, "mitre_mapping": report.get("mitre", result.get("mitre", [])), "ai_reasoning": reasoning, "verdict": decision, "recommended_actions": serialize(decision.get("recommended_actions", decision.get("actions", report.get("recommendations", [])))), "analyst_decision": {"status": "recorded" if feedback.get("items") else "pending", "history": feedback.get("items", [])}, "governance": {"tenant_scoped": True, "auditable": True, "reproducible": True}}
