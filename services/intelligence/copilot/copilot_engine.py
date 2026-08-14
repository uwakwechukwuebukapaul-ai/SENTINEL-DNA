"""Analyst-facing, advisory investigation copilot."""
from __future__ import annotations
import json
from typing import Any
from .models import CopilotResponse
from .prompts import build_summary_prompt, build_reasoning_prompt, build_recommendation_prompt


class InvestigationCopilot:
    def __init__(self, ai_runtime: Any = None) -> None:
        self.ai_runtime = ai_runtime

    @staticmethod
    def _data(value: Any) -> dict[str, Any]:
        if value is None: return {}
        if hasattr(value, "to_dict"): return dict(value.to_dict())
        if hasattr(value, "snapshot"): return dict(value.snapshot())
        return dict(value) if isinstance(value, dict) else dict(vars(value))

    def _answer(self, context: Any, result: Any, reasoning_report: Any, decision_report: Any, memory_reference: str | None, question: str, prompt: str) -> CopilotResponse:
        ctx, res, reasoning, decision = self._data(context), self._data(result), self._data(reasoning_report), self._data(decision_report)
        refs = [str(x.get("id") or x.get("evidence_id")) for x in ctx.get("evidence", []) if isinstance(x, dict)]
        findings = reasoning.get("findings", []) or []
        answer = reasoning.get("summary") or decision.get("rationale") or "No evidence-backed conclusion is available."
        if question.lower().startswith("what happened"): answer = f"Investigation outcome: {answer}"
        elif "mitre" in question.lower(): answer = "MITRE techniques involved: " + ", ".join(res.get("mitre", []) or reasoning.get("mitre_techniques", []) or ["none identified"])
        elif "before" in question.lower(): answer = f"Historical memory reference: {memory_reference or 'none available'}."
        metadata = {"synthetic_only": True, "provider": "deterministic_copilot", "prompt": prompt, "finding_count": len(findings)}
        if self.ai_runtime is not None:
            ai = self.ai_runtime.reason(type("CopilotContext", (), {"snapshot": lambda _: {**ctx, "evidence": ctx.get("evidence", []), "iocs": ctx.get("iocs", []), "timeline": ctx.get("timeline", [])}})())
            metadata.update({"provider": ai.metadata.get("provider", "unknown"), "synthetic_only": bool(ai.metadata.get("synthetic", True)), "ai_confidence": ai.confidence})
        return CopilotResponse(case_id=str(ctx.get("case_id") or res.get("case_id") or "unknown"), answer=answer, confidence=int(float(res.get("confidence") or reasoning.get("confidence") or 0) * 100), evidence_used=refs, evidence_refs=refs, reasoning_refs=[str(f.get("finding_id")) for f in findings if isinstance(f, dict)], recommended_actions=list(res.get("recommendations", []) or decision.get("recommended_actions", []) or []), mitre_techniques=list(res.get("mitre", []) or []), metadata=metadata)

    def summarize_investigation(self, context, result, reasoning_report=None, decision_report=None, memory_reference=None):
        return self._answer(context, result, reasoning_report, decision_report, memory_reference, "What happened?", build_summary_prompt(context, result, reasoning_report, decision_report, memory_reference))

    def answer_question(self, question, context, result, reasoning_report=None, decision_report=None, memory_reference=None):
        return self._answer(context, result, reasoning_report, decision_report, memory_reference, question, build_reasoning_prompt(question, context, result, reasoning_report, decision_report, memory_reference))

    def recommend_next_steps(self, context, result, reasoning_report=None, decision_report=None, memory_reference=None):
        return self._answer(context, result, reasoning_report, decision_report, memory_reference, "What should I investigate next?", build_recommendation_prompt(context, result, reasoning_report, decision_report, memory_reference))
