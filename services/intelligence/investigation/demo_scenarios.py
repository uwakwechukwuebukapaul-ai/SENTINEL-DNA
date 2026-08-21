"""Deterministic, synthetic AI Investigator V1 demo reports.

These fixtures are presentation inputs for the existing pilot simulation
boundary. They are not production records and do not execute investigations.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_SCENARIOS: dict[str, dict[str, Any]] = {
    "phishing": {
        "title": "Credential harvesting email",
        "summary": "An employee received a malicious email containing a credential-harvesting URL.",
        "severity": "HIGH", "status": "completed", "verdict": "true_positive", "confidence": .94,
        "alert": {"source": "email_gateway", "affected_users": ["maya.owusu@example.test"], "affected_assets": ["Corporate mailbox"], "indicators": ["login-secure.example.test", "credential harvesting"]},
        "evidence": [{"evidence_id": "DEMO-PHISH-E1", "type": "email", "source": "email_gateway", "timestamp": "2026-08-20T09:00:00Z", "provenance": "synthetic email gateway", "confidence": .98, "description": "Message contained a suspicious sign-in link."}, {"evidence_id": "DEMO-PHISH-E2", "type": "url", "source": "email_gateway", "timestamp": "2026-08-20T09:01:00Z", "provenance": "synthetic URL extraction", "confidence": .96, "description": "User followed a credential-harvesting URL."}],
        "threat_intelligence": {"ioc_reputation": "malicious", "provider_confidence": .96, "enrichment_timeline": [{"timestamp": "2026-08-20T09:01:00Z", "provider": "synthetic-intel", "status": "confirmed"}], "conflicts": []},
        "timeline": [{"timestamp": "2026-08-20T09:00:00Z", "description": "Email delivered"}, {"timestamp": "2026-08-20T09:02:00Z", "description": "IOC reputation confirmed"}],
        "attack_story": {"summary": "Initial access through a credential-harvesting link followed by credential theft.", "phases": ["initial_access", "credential_access"]},
        "mitre": [{"tactic": "Initial Access", "technique": "T1566.002", "name": "Spearphishing Link", "evidence_refs": ["DEMO-PHISH-E1", "DEMO-PHISH-E2"], "confidence": .94, "explanation": "The email and URL evidence support malicious link delivery."}],
        "reasoning": [{"observation": "Suspicious credential-harvesting email", "evidence": ["DEMO-PHISH-E1"], "reasoning": "The URL and message pattern match a known phishing delivery path.", "impact": "User credentials may be exposed.", "confidence": .94}],
        "uncertainty": "No endpoint click telemetry is available in this synthetic case.", "recommendations": ["Reset affected credentials", "Block the malicious domain"],
    },
    "powershell": {
        "title": "Unsigned PowerShell payload execution", "summary": "An endpoint executed an unsigned PowerShell command that downloaded a payload.",
        "severity": "HIGH", "status": "completed", "verdict": "true_positive", "confidence": .91,
        "alert": {"source": "endpoint_detection", "affected_users": ["daniel.ade@example.test"], "affected_assets": ["ENG-LAPTOP-042"], "indicators": ["powershell.exe", "cdn-update.example.test"]},
        "evidence": [{"evidence_id": "DEMO-PS-E1", "type": "process", "source": "endpoint", "timestamp": "2026-08-20T10:14:00Z", "provenance": "synthetic endpoint telemetry", "confidence": .93, "description": "Unsigned PowerShell downloaded an executable payload."}, {"evidence_id": "DEMO-PS-E2", "type": "persistence", "source": "endpoint", "timestamp": "2026-08-20T10:16:00Z", "provenance": "synthetic endpoint telemetry", "confidence": .86, "description": "Downloaded payload registered a scheduled task for persistence."}],
        "threat_intelligence": {"ioc_reputation": "suspicious", "provider_confidence": .89, "enrichment_timeline": [{"timestamp": "2026-08-20T10:15:00Z", "provider": "synthetic-intel", "status": "suspicious"}], "conflicts": ["One provider has no observation for the domain."]},
        "timeline": [{"timestamp": "2026-08-20T10:14:00Z", "description": "PowerShell command executed"}, {"timestamp": "2026-08-20T10:15:00Z", "description": "Payload download observed"}, {"timestamp": "2026-08-20T10:16:00Z", "description": "Scheduled task persistence observed"}],
        "attack_story": {"summary": "Execution progressed from PowerShell to payload delivery.", "phases": ["execution", "persistence"]},
        "mitre": [{"tactic": "Execution", "technique": "T1059.001", "name": "PowerShell", "evidence_refs": ["DEMO-PS-E1"], "confidence": .91, "explanation": "The process evidence directly identifies PowerShell execution."}],
        "reasoning": [{"observation": "Unsigned PowerShell execution", "evidence": ["DEMO-PS-E1"], "reasoning": "Command execution and payload download form a suspicious execution chain.", "impact": "Endpoint compromise is plausible.", "confidence": .91}],
        "uncertainty": "Payload detonation telemetry is not included in the demo.", "recommendations": ["Isolate the endpoint", "Review the downloaded payload"],
    },
    "credential_compromise": {
        "title": "Impossible-travel authentication anomaly", "summary": "A user account authenticated from geographically inconsistent locations within a short interval.",
        "severity": "MEDIUM", "status": "completed", "verdict": "needs_review", "confidence": .68,
        "alert": {"source": "identity_provider", "affected_users": ["amina.bello@example.test"], "affected_assets": ["Identity tenant"], "indicators": ["impossible travel", "new device"]},
        "evidence": [{"evidence_id": "DEMO-CRED-E1", "type": "authentication", "source": "identity_provider", "timestamp": "2026-08-20T11:00:00Z", "provenance": "synthetic identity telemetry", "confidence": .72, "description": "Successful logins from Lagos and Frankfurt within 18 minutes."}, {"evidence_id": "DEMO-CRED-E2", "type": "privilege_change", "source": "identity_provider", "timestamp": "2026-08-20T11:20:00Z", "provenance": "synthetic identity telemetry", "confidence": .63, "description": "A privileged group membership change followed the anomalous login."}],
        "threat_intelligence": {"ioc_reputation": "unknown", "provider_confidence": .55, "enrichment_timeline": [{"timestamp": "2026-08-20T11:02:00Z", "provider": "synthetic-intel", "status": "inconclusive"}], "conflicts": ["Travel context may explain the location difference."]},
        "timeline": [{"timestamp": "2026-08-20T11:00:00Z", "description": "Login from Lagos"}, {"timestamp": "2026-08-20T11:18:00Z", "description": "Login from Frankfurt"}],
        "attack_story": {"summary": "Authentication anomaly followed by a privilege change requires analyst confirmation.", "phases": ["credential_access", "privilege_escalation"]},
        "mitre": [{"tactic": "Credential Access", "technique": "T1078", "name": "Valid Accounts", "evidence_refs": ["DEMO-CRED-E1"], "confidence": .68, "explanation": "The anomaly is consistent with possible valid-account abuse but is not conclusive."}],
        "reasoning": [{"observation": "Impossible-travel authentication pattern", "evidence": ["DEMO-CRED-E1"], "reasoning": "The timing and locations are anomalous, but legitimate travel cannot be excluded.", "impact": "Account compromise is possible.", "confidence": .68}],
        "uncertainty": "Legitimate travel and VPN use are unresolved.", "recommendations": ["Request user confirmation", "Review MFA and device telemetry"],
    },
    "malware": {
        "title": "Known malware artifact execution", "summary": "A known malicious hash executed on a corporate endpoint.",
        "severity": "CRITICAL", "status": "completed", "verdict": "true_positive", "confidence": .97,
        "alert": {"source": "endpoint_detection", "affected_users": ["olumide.ade@example.test"], "affected_assets": ["FIN-LAPTOP-007"], "indicators": ["sha256:demo-malware-001", "payload.exe"]},
        "evidence": [{"evidence_id": "DEMO-MAL-E1", "type": "malware_artifact", "source": "endpoint", "timestamp": "2026-08-20T12:00:00Z", "provenance": "synthetic endpoint telemetry", "confidence": .99, "description": "Known malicious artifact executed from a temporary directory."}, {"evidence_id": "DEMO-MAL-E2", "type": "network_connection", "source": "endpoint", "timestamp": "2026-08-20T12:03:00Z", "provenance": "synthetic network telemetry", "confidence": .94, "description": "The process connected to a known malicious command-and-control indicator."}],
        "threat_intelligence": {"ioc_reputation": "malicious", "provider_confidence": .99, "enrichment_timeline": [{"timestamp": "2026-08-20T12:01:00Z", "provider": "synthetic-intel", "status": "confirmed"}], "conflicts": []},
        "timeline": [{"timestamp": "2026-08-20T12:00:00Z", "description": "Artifact created"}, {"timestamp": "2026-08-20T12:01:00Z", "description": "Malicious hash enriched"}, {"timestamp": "2026-08-20T12:02:00Z", "description": "Execution observed"}],
        "attack_story": {"summary": "Malware artifact execution progressed to confirmed impact risk.", "phases": ["execution", "impact"]},
        "mitre": [{"tactic": "Execution", "technique": "T1204", "name": "User Execution", "evidence_refs": ["DEMO-MAL-E1"], "confidence": .97, "explanation": "Artifact execution is directly supported by endpoint evidence."}],
        "reasoning": [{"observation": "Known malicious artifact executed", "evidence": ["DEMO-MAL-E1"], "reasoning": "The hash reputation and execution event provide mutually reinforcing evidence.", "impact": "Endpoint compromise is highly likely.", "confidence": .97}],
        "uncertainty": "No lateral movement evidence is present in this synthetic case.", "recommendations": ["Isolate the endpoint", "Begin malware containment procedure"],
    },
}


def available_demo_scenarios() -> list[dict[str, str]]:
    return [{"id": key, "title": value["title"], "expected_verdict": value["verdict"]} for key, value in _SCENARIOS.items()]


def get_demo_report(scenario: str, *, tenant_id: str, case_id: str) -> dict[str, Any]:
    # Preserve the existing pilot-management scenario name without exposing a
    # second scenario definition or workflow.
    scenario = {"credential_theft": "credential_compromise"}.get(scenario, scenario)
    if scenario not in _SCENARIOS:
        raise ValueError("unknown_demo_scenario")
    report = deepcopy(_SCENARIOS[scenario])
    report.update({"case_id": case_id, "tenant_context": {"tenant_id": tenant_id}, "metadata": {"tenant_id": tenant_id, "demo": True, "scenario": scenario, "correlation_id": f"demo-{scenario}-{case_id}"}})
    for collection in ("evidence", "findings", "timeline", "mitre"):
        for item in report.get(collection, []):
            if isinstance(item, dict):
                item.setdefault("tenant_id", tenant_id)
                item.setdefault("case_id", case_id)
    return report


__all__ = ["available_demo_scenarios", "get_demo_report"]
