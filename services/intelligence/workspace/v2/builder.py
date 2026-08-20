"""Read-only projection from investigation intelligence to analyst workspace data."""

from __future__ import annotations

from typing import Any

from services.core.serialization import serialize

from .models import AnalystWorkspaceV2


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

        return AnalystWorkspaceV2(
            investigation={"investigation_id": investigation_id, "case_id": report_data.get("case_id") or result_data.get("case_id"), "tenant_id": scoped_tenant, "status": report_data.get("status") or result_data.get("status", "unknown")},
            verdict_summary={"verdict": decision.get("verdict", decision.get("decision", "unavailable")), "rationale": decision.get("rationale"), "risk_score": decision.get("risk_score"), "source": "decision_intelligence" if decision else "unavailable"},
            confidence_visualization=confidence,
            risk_explanation=risk,
            evidence_references=tuple(evidence),
            missing_evidence=tuple(missing),
            attack_sequence_timeline=tuple(timeline),
            mitre_mappings=tuple(mitre),
            provenance={"projection": "analyst_workspace_v2", "report_metadata": serialize(report_data.get("metadata", {})), "decision": serialize(decision.get("provenance", {})), "attack_sequence": serialize(sequence.get("provenance", {}))},
            analyst_feedback=feedback,
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
            items.setdefault(reference_id, {
                "reference_id": reference_id,
                "source": item.get("source", "unknown"),
                "type": item.get("type", item.get("artifact_type", "unknown")),
                "metadata": serialize(item.get("metadata", {})),
            })
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
        return {"items": sorted(items, key=lambda item: (str(item.get("created_at", "")), str(item.get("feedback_id", "")))), "placeholder": {"status": "ready_for_analyst_feedback", "supported_decisions": ["accepted", "rejected", "needs_more_evidence"]}}
