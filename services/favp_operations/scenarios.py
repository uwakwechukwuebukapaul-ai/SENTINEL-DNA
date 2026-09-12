"""Synthetic SOC scenario catalog for the FAVP.

Evidence entries are references and sanitized observations only.  They are
not customer telemetry, credentials, production indicators, or test-run
evidence.  The catalog is read-only from the operations API.
"""

from copy import deepcopy


def _scenario(
    scenario_id,
    name,
    description,
    objectives,
    mitre,
    criteria,
    difficulty,
):
    return {
        "scenario_id": scenario_id,
        "name": name,
        "description": description,
        "synthetic": True,
        "evidence_package": {
            "classification": "synthetic_sanitized",
            "references": [
                f"{scenario_id}:observation-01",
                f"{scenario_id}:timeline-01",
                f"{scenario_id}:ioc-set-01",
            ],
            "contains_customer_data": False,
            "contains_credentials": False,
        },
        "expected_investigation_objectives": list(objectives),
        "mitre_attack_mapping": list(mitre),
        "evaluation_criteria": list(criteria),
        "difficulty": difficulty,
        "version": "scenario-catalog-v1",
    }


FAVP_SCENARIOS = {
    item["scenario_id"]: item
    for item in (
        _scenario(
            "FAVP-SCN-001",
            "Phishing investigation",
            "Trace a synthetic phishing message from delivery through analyst disposition.",
            ("establish delivery path", "identify affected identity", "preserve provenance"),
            ("T1566.002", "T1204.002"),
            ("message-to-identity linkage", "timeline completeness", "bounded disposition"),
            "introductory",
        ),
        _scenario(
            "FAVP-SCN-002",
            "Credential compromise",
            "Assess a synthetic credential misuse sequence and its evidence quality.",
            ("separate valid from anomalous use", "identify containment recommendation", "record uncertainty"),
            ("T1078", "T1110"),
            ("authentication evidence review", "uncertainty recorded", "human decision retained"),
            "intermediate",
        ),
        _scenario(
            "FAVP-SCN-003",
            "Suspicious authentication",
            "Review synthetic sign-in anomalies across time, geography, and device posture.",
            ("build sign-in timeline", "compare contextual signals", "avoid unsupported attribution"),
            ("T1078", "T1098"),
            ("signal correlation", "false assumptions avoided", "provenance clarity"),
            "introductory",
        ),
        _scenario(
            "FAVP-SCN-004",
            "Malware execution",
            "Investigate a synthetic endpoint execution chain without executing payloads.",
            ("identify execution event", "trace parent-child context", "state safe next steps"),
            ("T1204.002", "T1059"),
            ("execution chain", "evidence boundaries", "no autonomous action"),
            "intermediate",
        ),
        _scenario(
            "FAVP-SCN-005",
            "PowerShell abuse",
            "Analyze sanitized PowerShell telemetry and distinguish intent from evidence.",
            ("interpret command context", "map behavior to technique", "record limitations"),
            ("T1059.001", "T1027"),
            ("command interpretation", "MITRE mapping", "advisory output reviewed"),
            "intermediate",
        ),
        _scenario(
            "FAVP-SCN-006",
            "Cloud account compromise",
            "Review a synthetic cloud identity sequence and assess access scope.",
            ("identify identity events", "review privilege context", "recommend human-approved follow-up"),
            ("T1078.004", "T1098.003"),
            ("cloud event linkage", "least-privilege reasoning", "human approval boundary"),
            "advanced",
        ),
        _scenario(
            "FAVP-SCN-007",
            "Lateral movement",
            "Trace a synthetic host-to-host movement path from sanitized telemetry.",
            ("construct movement path", "identify missing telemetry", "bound the conclusion"),
            ("T1021", "T1046"),
            ("path accuracy", "missing evidence noted", "no production impact"),
            "advanced",
        ),
        _scenario(
            "FAVP-SCN-008",
            "Command and Control investigation",
            "Assess synthetic outbound communication patterns without contacting external infrastructure.",
            ("classify communication pattern", "review DNS and proxy context", "preserve evidence references"),
            ("T1071.001", "T1105"),
            ("communication reasoning", "source provenance", "external access prohibited"),
            "advanced",
        ),
        _scenario(
            "FAVP-SCN-009",
            "Multi-IOC correlation",
            "Correlate several sanitized indicators into a bounded investigation narrative.",
            ("link indicators", "rank evidence", "identify contradictory signals"),
            ("T1071", "T1059", "T1566"),
            ("multi-source linkage", "contradiction handling", "confidence explained"),
            "advanced",
        ),
        _scenario(
            "FAVP-SCN-010",
            "False positive investigation",
            "Determine whether a synthetic alert is benign and document the reasoning.",
            ("test benign explanation", "identify detection gap", "record analyst disposition"),
            ("T1071",),
            ("benign evidence", "reasoning transparency", "limitation captured"),
            "introductory",
        ),
    )
}


def get_scenario(scenario_id):
    """Return a copy so callers cannot mutate the catalog globally."""
    scenario = FAVP_SCENARIOS.get(str(scenario_id))
    return deepcopy(scenario) if scenario else None


__all__ = ["FAVP_SCENARIOS", "get_scenario"]
