"""Deterministic, offline-safe reasoning over investigation evidence."""

from __future__ import annotations

import json
from typing import Any

from .models import ReasoningFinding, ReasoningReport


class EvidenceReasoner:
    """Correlate existing context data without mutating it or making network calls."""

    def __init__(self, ai_runtime: Any = None) -> None:
        self.ai_runtime = ai_runtime

    @staticmethod
    def _data(context: Any) -> dict[str, Any]:
        if hasattr(context, "snapshot"):
            return dict(context.snapshot())
        if hasattr(context, "to_dict"):
            return dict(context.to_dict())
        return dict(vars(context))

    @staticmethod
    def _ref(item: Any, index: int) -> str:
        if isinstance(item, dict):
            return str(item.get("evidence_id") or item.get("id") or item.get("reference") or f"evidence-{index}")
        return f"evidence-{index}"

    def build_prompt(self, context: Any, plan: Any = None) -> str:
        data = self._data(context)
        payload = {
            "investigation_objective": getattr(plan, "objective", None) or getattr(plan, "name", None) or data.get("alert", {}).get("objective", "investigate observed security risk"),
            "evidence_summary": data.get("evidence", []),
            "ioc_summary": data.get("iocs", []),
            "timeline_summary": data.get("timeline", []),
            "enrichment_results": data.get("enrichment", data.get("enrichment_results", [])),
            "required_reasoning_task": "Identify evidence-backed findings, map applicable MITRE techniques, and state calibrated confidence. Do not execute actions.",
        }
        return json.dumps(payload, sort_keys=True, default=str)

    def reason(self, context: Any, plan: Any = None) -> ReasoningReport:
        data = self._data(context)
        evidence = list(data.get("evidence", []) or [])
        iocs = list(data.get("iocs", []) or [])
        haystack = json.dumps({"evidence": evidence, "iocs": iocs}, default=str).lower()
        refs = [self._ref(item, index) for index, item in enumerate(evidence)]
        findings: list[ReasoningFinding] = []
        if any(term in haystack for term in ("phishing", "credential", "malicious url", "credential harvesting")):
            confidence = 0.88
            findings.append(ReasoningFinding(
                finding_id="RF-PHISHING-001",
                title="Potential Credential Harvesting Attempt",
                description="Evidence and IOC indicators are consistent with a phishing attempt intended to capture credentials.",
                severity="high",
                confidence=confidence,
                evidence_refs=refs,
                mitre_techniques=["T1566", "T1566.002"],
            ))
        metadata: dict[str, Any] = {"provider": "deterministic_evidence_reasoner", "synthetic_only": True, "evidence_references": refs}
        if self.ai_runtime is not None:
            response = self.ai_runtime.reason(type("ReasoningPromptContext", (), {"snapshot": lambda _: {**data, "evidence": evidence, "iocs": iocs, "timeline": data.get("timeline", [])}})())
            ai_refs = list(response.evidence_references)
            if ai_refs and all(str(ref).isdigit() for ref in ai_refs) and refs:
                ai_refs = [refs[int(ref)] if int(ref) < len(refs) else ref for ref in ai_refs]
            metadata.update({"provider": response.metadata.get("provider", "unknown"), "synthetic_only": bool(response.metadata.get("synthetic", response.metadata.get("offline_only", False))), "ai_confidence": response.confidence, "ai_evidence_references": ai_refs, "prompt": self.build_prompt(context, plan)})
        confidence = findings[0].confidence if findings else 0.25
        return ReasoningReport(
            summary="Evidence supports a potential credential harvesting attempt." if findings else "No deterministic evidence-backed finding was identified.",
            findings=findings,
            confidence=confidence,
            metadata=metadata,
        )
