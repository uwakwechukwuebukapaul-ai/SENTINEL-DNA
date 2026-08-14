"""Deterministic conversion of investigation intelligence into SOC decisions."""
from __future__ import annotations
import hashlib
import json
from typing import Any
from .models import InvestigationDecision


class DecisionEngine:
    def decide(self, result: Any, reasoning_report: Any = None, memory_reference: str | None = None) -> InvestigationDecision:
        data = self._data(result)
        reasoning = self._data(reasoning_report or data.get("reasoning_report"))
        case_id = str(data.get("case_id") or "unknown")
        evidence = data.get("evidence", data.get("artifacts", [])) or []
        text = json.dumps({"result": data, "reasoning": reasoning}, default=str).lower()
        confidence = float(data.get("confidence") or reasoning.get("confidence") or 0.0)
        severity = str((data.get("risk") or {}).get("severity", "") if isinstance(data.get("risk"), dict) else data.get("risk") or "unknown").lower()
        malicious = any(term in text for term in ("phishing", "malicious", "credential harvesting", "suspicious"))
        benign = any(term in text for term in ("benign", "legitimate", "false positive", "no threat"))
        conflicting = malicious and benign
        if confidence < 0.4:
            verdict, rationale = "insufficient_evidence", "Confidence is too low to support a reliable SOC verdict."
        elif conflicting:
            verdict, rationale = "needs_review", "Evidence contains conflicting malicious and benign indicators."
        elif malicious and severity in {"critical", "high"}:
            verdict, rationale = "true_positive", "Critical or high-severity evidence includes malicious indicators."
        elif benign:
            verdict, rationale = "false_positive", "Evidence is consistent with a benign or legitimate activity."
        elif malicious:
            verdict, rationale = "needs_review", "Malicious indicators exist, but evidence is not critical or strong enough for automatic confirmation."
        else:
            verdict, rationale = "needs_review", "Evidence does not establish a sufficiently strong benign or malicious conclusion."
        payload = f"{case_id}|{verdict}|{memory_reference or ''}|{json.dumps(reasoning, sort_keys=True, default=str)}"
        return InvestigationDecision(
            decision_id="DEC-" + hashlib.sha256(payload.encode()).hexdigest()[:20], case_id=case_id,
            verdict=verdict, severity=severity, confidence=confidence, rationale=rationale,
            recommended_actions=["Escalate for analyst review"] if verdict in {"true_positive", "needs_review"} else ["Close as benign"],
            evidence_summary={"count": len(evidence), "memory_reference": memory_reference},
            mitre_summary=list(data.get("mitre", []) or reasoning.get("mitre_techniques", []) or []), synthetic_only=True)

    @staticmethod
    def _data(value: Any) -> dict[str, Any]:
        if value is None: return {}
        if hasattr(value, "to_dict"): return dict(value.to_dict())
        return dict(value) if isinstance(value, dict) else dict(vars(value))
