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