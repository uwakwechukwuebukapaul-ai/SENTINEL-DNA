from __future__ import annotations
from typing import Any

class InvestigationCopilot:
    """Deterministic analyst assistance over the canonical intelligence snapshot."""
    def explain(self, intelligence: dict[str, Any]) -> str:
        findings = "; ".join(str(item) for item in intelligence.get("findings", [])[:3]) or "No findings recorded."
        return f"Risk is {intelligence.get('risk_score', 0)} ({intelligence.get('risk_severity', 'unknown')}) with {float(intelligence.get('confidence', 0)):.0%} confidence. Findings: {findings}"
    def summarize_attack_story(self, intelligence: dict[str, Any]) -> str:
        return str(intelligence.get("attack_story") or "No attack story has been recorded for this investigation.")
    def suggest_actions(self, intelligence: dict[str, Any]) -> list[str]:
        return list(intelligence.get("recommendations", [])) or ["Validate the highest-risk indicators and preserve supporting evidence.", "Review the investigation timeline with the case owner."]
    def questions(self, intelligence: dict[str, Any]) -> list[str]:
        return [f"What evidence supports the {intelligence.get('risk_severity', 'current')} risk assessment?", "Which MITRE techniques are confirmed versus suspected?", "What is the next containment or validation step?"]
    def answer(self, prompt: str, intelligence: dict[str, Any]) -> dict[str, Any]:
        key = (prompt or "explain").strip().lower()
        if key in {"attack story", "summarize", "summary"}: result = self.summarize_attack_story(intelligence)
        elif key in {"actions", "next actions", "recommendations"}: result = self.suggest_actions(intelligence)
        elif key in {"questions", "investigation questions"}: result = self.questions(intelligence)
        else: result = self.explain(intelligence)
        return {"prompt": prompt, "result": result}

    def ai_answer(self, prompt: str, intelligence: dict[str, Any], fabric=None, organization_id: str | None = None) -> dict[str, Any]:
        """Optional AI Fabric path; legacy methods remain deterministic and unchanged."""
        if fabric is None or not organization_id:
            return self.answer(prompt, intelligence)
        return {"prompt": prompt, "result": fabric.investigate(organization_id, prompt, intelligence.get("evidence", []))}
