from __future__ import annotations
from copy import deepcopy

SCENARIOS = {
    "phishing": {
        "case_id": "CZ-PHISH-001",
        "alert": {"title": "Synthetic phishing alert", "severity": "HIGH", "description": "Synthetic credential phishing message."},
        "artifacts": [{"type": "email", "data": "synthetic sender and credential lure at example.invalid"}],
        "expected_findings": ["Credential phishing indicators observed"],
        "expected_mitre": ["T1566"], "expected_risk": "high",
    },
    "brute_force": {
        "case_id": "CZ-AUTH-001",
        "alert": {"title": "Synthetic authentication attack", "severity": "HIGH", "description": "Synthetic repeated authentication failures."},
        "artifacts": [{"type": "authentication", "data": "synthetic repeated failures for demo-user"}],
        "expected_findings": ["Repeated authentication failures observed"],
        "expected_mitre": ["T1110"], "expected_risk": "high",
    },
    "malware": {
        "case_id": "CZ-MALWARE-001",
        "alert": {"title": "Synthetic malware detection", "severity": "CRITICAL", "description": "Synthetic endpoint malware signal."},
        "artifacts": [{"type": "endpoint", "data": "synthetic malware sample marker; no executable content"}],
        "expected_findings": ["Synthetic malware indicator observed"],
        "expected_mitre": ["T1204"], "expected_risk": "critical",
    },
    "external_communication": {
        "case_id": "CZ-NET-001",
        "alert": {"title": "Synthetic external communication", "severity": "MEDIUM", "description": "Synthetic suspicious outbound communication."},
        "artifacts": [{"type": "network", "data": "synthetic connection to example.invalid"}],
        "expected_findings": ["Suspicious external communication observed"],
        "expected_mitre": ["T1071"], "expected_risk": "medium",
    },
}

def get_scenario(name: str) -> dict:
    try:
        return deepcopy(SCENARIOS[name])
    except KeyError as exc:
        raise ValueError(f"Unknown Customer Zero scenario: {name}") from exc
