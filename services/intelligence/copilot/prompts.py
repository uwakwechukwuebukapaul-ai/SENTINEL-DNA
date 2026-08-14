"""
Sentinel DNA AI SOC Copilot Prompt Contracts.

These prompt builders remain provider-independent.
An external LLM adapter can consume them later.
"""


SYSTEM_PROMPT = """
You are Sentinel DNA, an enterprise AI SOC investigation copilot.

Your role is to help security analysts understand investigations,
evaluate evidence, explain risk, and determine appropriate next actions.

Never invent evidence.

Clearly distinguish:
- observed evidence
- inferred conclusions
- analyst recommendations

Prefer concise, technically accurate security reasoning.

Prioritize:
1. Evidence
2. Risk
3. Confidence
4. MITRE ATT&CK context
5. Recommended response actions
"""


def build_investigation_prompt(
    question: str,
    investigation: dict,
) -> str:
    """
    Build a provider-neutral investigation prompt.
    """

    return (
        f"{SYSTEM_PROMPT}\n\n"
        "Investigation context:\n"
        f"{investigation}\n\n"
        "Analyst question:\n"
        f"{question}\n\n"
        "Provide an evidence-grounded answer."
    )


def _structured(context, result, reasoning, decision, memory):
    def data(value):
        if hasattr(value, "to_dict"): return value.to_dict()
        return value or {}
    c, r = data(context), data(result)
    return {"investigation_objective": c.get("alert", {}).get("objective", "investigate security event"), "evidence_summary": c.get("evidence", []), "ioc_information": c.get("iocs", []), "timeline_information": c.get("timeline", []), "reasoning_findings": data(reasoning), "decision_output": data(decision), "historical_memory_reference": memory, "result": r}


def build_summary_prompt(context, result, reasoning=None, decision=None, memory=None):
    return "Summarize this investigation for a SOC analyst.\n" + str(_structured(context, result, reasoning, decision, memory))


def build_reasoning_prompt(question, context, result, reasoning=None, decision=None, memory=None):
    return "Answer the analyst question with evidence-backed context. Question: " + question + "\n" + str(_structured(context, result, reasoning, decision, memory))


def build_recommendation_prompt(context, result, reasoning=None, decision=None, memory=None):
    return "Recommend safe analyst next steps; do not execute actions.\n" + str(_structured(context, result, reasoning, decision, memory))
