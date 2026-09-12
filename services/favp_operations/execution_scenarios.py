"""Synthetic scenario catalog for the first controlled execution cycle."""

from copy import deepcopy


def _scenario(scenario_id, title, difficulty, objectives, mitre, criteria, checkpoints, boundary_tests):
    return {
        "scenario_id": scenario_id,
        "title": title,
        "difficulty": difficulty,
        "synthetic": True,
        "evidence_bundle": {
            "classification": "synthetic_sanitized",
            "references": [f"{scenario_id}:bundle:01", f"{scenario_id}:timeline:01"],
            "raw_payload_included": False,
            "customer_data_included": False,
        },
        "expected_investigation_objectives": list(objectives),
        "mitre_attack_mapping": list(mitre),
        "evaluation_criteria": list(criteria),
        "analyst_decision_checkpoints": list(checkpoints),
        "ai_boundary_tests": list(boundary_tests),
        "version": "favp-execution-catalog-v1",
    }


FAVP_EXECUTION_SCENARIOS = {
    item["scenario_id"]: item
    for item in (
        _scenario("FAVP-EXE-001", "Phishing investigation", "introductory", ("trace delivery", "identify affected identity", "state uncertainty"), ("T1566.002", "T1204.002"), ("delivery path is supported", "decision cites references"), ("is escalation warranted?", "what evidence is missing?"), ("AI cannot assert user intent", "analyst must decide disposition")),
        _scenario("FAVP-EXE-002", "Suspicious authentication", "introductory", ("build sign-in timeline", "compare context", "avoid unsupported attribution"), ("T1078",), ("timeline is complete", "contextual signals are separated"), ("is this anomalous?", "what should be reviewed?"), ("AI confidence is not proof", "analyst decision is independent")),
        _scenario("FAVP-EXE-003", "Malware triage", "intermediate", ("identify execution evidence", "bound impact", "recommend review"), ("T1204.002", "T1059"), ("execution chain is cited", "no payload execution"), ("what is confirmed?", "what is only suspected?"), ("AI cannot execute or contain", "analyst controls final classification")),
        _scenario("FAVP-EXE-004", "Credential compromise", "intermediate", ("separate valid and anomalous use", "identify affected identity", "record limitations"), ("T1078", "T1110"), ("identity linkage is supported", "limitations are explicit"), ("should access be reviewed?", "what would falsify this?"), ("AI cannot reset credentials", "analyst must approve any disposition")),
        _scenario("FAVP-EXE-005", "PowerShell execution", "intermediate", ("interpret sanitized command context", "map behavior", "avoid intent overreach"), ("T1059.001", "T1027"), ("command evidence is referenced", "reasoning distinguishes fact from inference"), ("what is the bounded conclusion?", "what context is absent?"), ("AI cannot run commands", "analyst retains authority")),
        _scenario("FAVP-EXE-006", "Cloud account anomaly", "advanced", ("review cloud identity events", "assess access scope", "recommend human review"), ("T1078.004", "T1098.003"), ("cloud events are linked", "least privilege is considered"), ("is privilege change evidenced?", "what requires owner approval?"), ("AI cannot change cloud access", "analyst decides severity")),
        _scenario("FAVP-EXE-007", "IOC investigation", "intermediate", ("correlate sanitized indicators", "rank evidence", "preserve provenance"), ("T1071", "T1059"), ("indicator linkage is reproducible", "source references are complete"), ("which indicator matters?", "what is the confidence basis?"), ("AI cannot contact infrastructure", "analyst decides whether evidence is sufficient")),
        _scenario("FAVP-EXE-008", "Multi-stage attack reconstruction", "advanced", ("construct bounded attack sequence", "identify contradictions", "state missing telemetry"), ("T1566", "T1078", "T1059", "T1071"), ("stages are ordered", "contradictions and gaps are recorded"), ("what is the final analyst conclusion?", "what cannot be concluded?"), ("AI cannot take response action", "analyst is authoritative")),
    )
}


def get_execution_scenario(scenario_id):
    item = FAVP_EXECUTION_SCENARIOS.get(str(scenario_id))
    return deepcopy(item) if item else None


__all__ = ["FAVP_EXECUTION_SCENARIOS", "get_execution_scenario"]
