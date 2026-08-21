"""Tenant-safe detection intelligence projection for an investigation result."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from services.intelligence.detection_engineering.detection_service import DetectionEngineeringService

from .coverage import DetectionCoverage
from .recommendations import DetectionRecommendationEngine


class DetectionInvestigationIntelligenceBuilder:
    """Composes existing detection services without changing rules or telemetry."""

    @staticmethod
    def _mapping(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, Mapping) else {}

    @staticmethod
    def _scoped(item: Mapping[str, Any], tenant_id: str, case_id: str) -> bool:
        context = item.get("tenant_context") if isinstance(item.get("tenant_context"), Mapping) else {}
        return (item.get("tenant_id") or context.get("tenant_id")) == tenant_id and (item.get("case_id") or item.get("investigation_id") or case_id) == case_id

    def build(
        self,
        *,
        tenant_id: str | None,
        case_id: str,
        evidence: list[Any] | None = None,
        timeline: list[Any] | None = None,
        mitre_techniques: list[Any] | None = None,
    ) -> dict[str, Any]:
        if not tenant_id:
            return {"advisory_only": True, "status": "tenant_context_required", "rule_quality": [], "mitre_coverage": {}, "recommendations": [], "alert_fatigue": {}}

        scoped_evidence = []
        technique_refs: dict[str, list[str]] = {}
        for raw in evidence or []:
            item = self._mapping(raw)
            provenance = self._mapping(item.get("provenance"))
            reference = item.get("evidence_id") or item.get("id") or item.get("reference")
            if not reference or not provenance.get("source") or not self._scoped(item, tenant_id, case_id):
                continue
            scoped_evidence.append(item)
            for technique in item.get("mitre_techniques", []) or item.get("mitre", []) or []:
                technique_refs.setdefault(str(technique), []).append(str(reference))
        mapped = sorted({str(item) for item in mitre_techniques or []} | set(technique_refs))
        evidence_refs = sorted({str(item.get("evidence_id") or item.get("id") or item.get("reference")) for item in scoped_evidence})
        catalog = DetectionEngineeringService().get_detection_catalog()
        covered = sorted({technique for rule in catalog for technique in rule.get("mitre_techniques", [])})
        coverage = DetectionCoverage().analyze(covered, mapped)
        coverage.update({
            "tenant_id": tenant_id,
            "mapped_techniques": mapped,
            "covered_techniques": sorted(set(mapped) & set(covered)),
            "uncovered_techniques": list(coverage["visibility_gaps"]),
            "evidence_references": {technique: sorted(set(technique_refs.get(technique, []))) for technique in mapped},
            "provenance": {"source": "detection_rule_catalog", "basis": "canonical_investigation_evidence"},
        })
        rule_quality = []
        for rule in catalog:
            relevant = sorted(set(rule.get("mitre_techniques", [])) & set(mapped))
            rule_quality.append({
                "rule_id": rule["id"], "rule_name": rule["name"], "tenant_id": tenant_id,
                "effectiveness": "investigation_relevant" if relevant else "not_observed_in_current_investigation",
                "maturity": coverage["detection_maturity"], "confidence": rule["confidence"],
                "mapped_techniques": relevant, "evidence_references": sorted({ref for technique in relevant for ref in technique_refs.get(technique, [])}),
                "provenance": {"source": "detection_rule_catalog", "rule_id": rule["id"]},
            })

        recommendations = []
        for technique in coverage["uncovered_techniques"]:
            references = coverage["evidence_references"].get(technique, [])
            if not references:
                continue
            recommendations.append({
                "recommendation": f"Add coverage for {technique}",
                "category": "coverage_improvement", "reason": "Investigation evidence maps to a technique without an active catalog rule.",
                "tenant_id": tenant_id, "evidence_references": references,
                "provenance": {"source": "detection_coverage", "technique": technique},
                "confidence": 0.8, "advisory_only": True, "automatic_rule_change": False,
            })
        events = []
        for raw in timeline or []:
            item = self._mapping(raw)
            provenance = self._mapping(item.get("provenance"))
            refs = [str(ref) for ref in item.get("evidence_refs", []) if ref]
            if self._scoped(item, tenant_id, case_id) and refs and (provenance.get("source") or item.get("source")):
                events.append(item)
        counts = Counter(str(item.get("event_type") or "unknown") for item in events)
        duplicates = [{"signal": signal, "count": count, "tenant_id": tenant_id, "investigation_impact": "repeated evidence-linked signals may require rule tuning", "evidence_references": sorted({str(ref) for item in events if str(item.get("event_type") or "unknown") == signal for ref in item.get("evidence_refs", [])}), "provenance": {"source": "investigation_timeline"}, "confidence": 0.7} for signal, count in sorted(counts.items()) if count > 1]
        fatigue = {"tenant_id": tenant_id, "alert_volume_indicator": len(events), "duplicate_detection_signals": duplicates, "noisy_rule_indicators": [item for item in duplicates if item["count"] >= 3], "investigation_impact": "Advisory signal volume context; not analyst productivity measurement.", "provenance": {"source": "canonical_investigation_timeline"}}
        return {"advisory_only": True, "status": "available", "tenant_id": tenant_id, "rule_quality": rule_quality, "mitre_coverage": coverage, "recommendations": recommendations, "alert_fatigue": fatigue}
