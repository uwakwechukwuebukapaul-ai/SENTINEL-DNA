"""Structured SOC scenarios for enterprise pilot demonstrations."""
from __future__ import annotations
from dataclasses import asdict, dataclass

@dataclass(frozen=True)
class PilotScenario:
    scenario_id: str
    name: str
    description: str
    alert: dict
    evidence_requirements: tuple[str, ...]
    expected_flow: tuple[str, ...]
    review_points: tuple[str, ...]
    investigation_objectives: tuple[str, ...]
    mitre_techniques: tuple[str, ...]
    expected_outcome: str
    def to_dict(self): return asdict(self)

_FLOW = ("alert_intake", "investigation_creation", "evidence_collection", "ioc_enrichment", "mitre_mapping", "ai_reasoning", "report_generation", "analyst_review", "feedback_submission", "metrics_evaluation")
PILOT_SCENARIOS = {item.scenario_id: item for item in (
    PilotScenario("phishing_compromise", "Phishing compromise", "Suspicious message leads to a credential capture attempt.", {"title": "Suspicious credential-capture email", "type": "phishing"}, ("message metadata", "mail headers", "linked indicator"), _FLOW, ("validate malicious link", "review affected identity", "decide whether the finding is actionable"), ("correlate message and indicator evidence", "map phishing behavior", "confirm analyst disposition"), ("T1566", "T1078"), "Evidence-backed phishing investigation ready for analyst review."),
    PilotScenario("suspicious_authentication", "Suspicious authentication activity", "Authentication behavior indicates possible account misuse.", {"title": "Impossible-travel authentication", "type": "authentication"}, ("authentication events", "source context", "identity metadata"), _FLOW, ("confirm user context", "review authentication confidence", "decide whether to escalate"), ("correlate authentication evidence", "assess identity risk", "confirm analyst disposition"), ("T1078",), "Authentication anomaly investigation ready for analyst review."),
    PilotScenario("malware_execution", "Malware execution", "Endpoint activity suggests execution of a suspicious payload.", {"title": "Suspicious executable observed", "type": "malware"}, ("process telemetry", "endpoint metadata", "file or hash indicator"), _FLOW, ("validate execution chain", "review affected endpoint", "decide containment recommendation"), ("establish endpoint execution evidence", "map execution behavior", "confirm analyst disposition"), ("T1059", "T1204"), "Execution evidence investigation ready for analyst review."),
    PilotScenario("credential_theft", "Credential theft", "Telemetry indicates possible credential access or collection.", {"title": "Credential access behavior", "type": "credential_theft"}, ("process activity", "identity events", "credential-access indicator"), _FLOW, ("verify evidence sufficiency", "review credential scope", "decide analyst outcome"), ("correlate credential-access evidence", "map credential behavior", "confirm analyst disposition"), ("T1003",), "Credential-access investigation ready for analyst review."),
    PilotScenario("cloud_account_compromise", "Cloud account compromise", "Cloud identity activity suggests unauthorized access.", {"title": "Unusual cloud account activity", "type": "cloud_account"}, ("cloud audit events", "identity context", "resource access evidence"), _FLOW, ("validate tenant and actor", "review resource impact", "decide escalation path"), ("correlate cloud audit evidence", "map cloud account behavior", "confirm analyst disposition"), ("T1078.004",), "Cloud-account investigation ready for analyst review."),
)}

def get_scenario(scenario_id):
    try: return PILOT_SCENARIOS[str(scenario_id)]
    except KeyError as exc: raise ValueError("unknown_pilot_scenario") from exc
