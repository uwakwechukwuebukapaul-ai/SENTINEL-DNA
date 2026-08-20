"""Pure, deterministic transformation from investigation results to decisions."""
from __future__ import annotations
from typing import Any
from .models import DecisionResult

class DecisionIntelligenceEngine:
    """Produce evidence-backed decisions without providers, I/O, or randomness."""
    def evaluate(self, result: Any, *, tenant_id: str | None = None) -> DecisionResult:
        data = self._data(result)
        investigation_id = str(data.get("investigation_id") or data.get("case_id") or "") or None
        tenant = tenant_id or data.get("tenant_id") or (data.get("tenant_context") or {}).get("tenant_id")
        risk = self._score(data.get("risk_score", data.get("risk")))
        confidence = self._score(data.get("confidence", data.get("ai_confidence")))
        evidence, missing = self._evidence(data, tenant)
        if risk >= 75 and evidence: verdict = "malicious"
        elif risk >= 45: verdict = "suspicious" if evidence else "inconclusive"
        elif risk <= 20 and evidence and not missing: verdict = "benign"
        else: verdict = "inconclusive"
        if not evidence: confidence = min(confidence, 25.0)
        actions = self._actions(verdict)
        provenance = dict(data.get("provenance") or {})
        provenance.update({"engine": "decision_intelligence", "tenant_id": tenant, "investigation_id": investigation_id})
        return DecisionResult(
            verdict=verdict, confidence=confidence, risk_score=risk,
            rationale=self._rationale(verdict, risk, len(evidence), len(missing)),
            supporting_evidence=evidence, missing_evidence=missing,
            recommended_actions=actions,
            containment_guidance=["Isolate affected assets and preserve telemetry for analyst approval."] if verdict == "malicious" else [],
            provenance=provenance, investigation_id=investigation_id, tenant_id=tenant,
            metadata={"evidence_count": len(evidence), "missing_evidence_count": len(missing)},
        )

    transform = evaluate
    decide = evaluate

    @staticmethod
    def _data(value: Any) -> dict[str, Any]:
        if isinstance(value, dict): return dict(value)
        if hasattr(value, "to_dict"): return dict(value.to_dict())
        return {k: getattr(value, k) for k in ("investigation_id", "case_id", "tenant_id", "tenant_context", "risk", "risk_score", "confidence", "artifacts", "evidence", "provenance") if hasattr(value, k)}

    @staticmethod
    def _score(value: Any) -> float:
        if isinstance(value, dict): value = value.get("score", value.get("risk_score", value.get("confidence", 0)))
        try: number = float(value or 0)
        except (TypeError, ValueError): return 0.0
        if 0 <= number <= 1: number *= 100
        return max(0.0, min(100.0, number))

    @staticmethod
    def _evidence(data: dict[str, Any], tenant: str | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        raw = list(data.get("evidence") or []) + list(data.get("artifacts") or [])
        supporting, missing, seen = [], [], set()
        for item in raw:
            if not isinstance(item, dict):
                missing.append({"source": "unknown", "reason": "Evidence item has no stable identifier."}); continue
            reference = next((item.get(k) for k in ("reference_id", "evidence_id", "artifact_id", "id", "reference") if item.get(k) not in (None, "")), None)
            source = str(item.get("source") or item.get("provider") or "unknown")
            if reference is None:
                missing.append({"source": source, "reason": "Evidence item has no stable identifier."}); continue
            if tenant is not None and item.get("tenant_id") not in (None, tenant): continue
            reference = str(reference)
            if reference in seen: continue
            seen.add(reference)
            supporting.append({"reference_id": reference, "source": source, "reason": str(item.get("reason") or item.get("description") or "Recorded investigation evidence.")})
        return supporting, missing

    @staticmethod
    def _rationale(verdict: str, risk: float, supported: int, missing: int) -> str:
        return f"Decision is {verdict} from normalized risk score {risk:.0f}/100 with {supported} supporting evidence item(s) and {missing} item(s) lacking stable identifiers."

    @staticmethod
    def _actions(verdict: str) -> list[str]:
        return {"malicious": ["Escalate for incident response review."], "suspicious": ["Validate indicators and collect additional telemetry."], "benign": ["Continue monitoring under existing controls."], "inconclusive": ["Collect additional attributable evidence before disposition."]}[verdict]

InvestigationDecisionEngine = DecisionIntelligenceEngine
