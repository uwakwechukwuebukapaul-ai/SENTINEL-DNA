# Sentinel DNA v1.0 Beta

Sentinel DNA is an AI-native security investigation intelligence platform. This v0.1 codebase evolves the earlier AI SOC Analyst prototype into a structured investigation layer between detection and decision.

## Architecture

- InvestigationCoordinator: canonical application/API entry point for `investigate(case_id, alert)`.
- InvestigationOrchestrator: canonical investigation workflow engine.
- RuntimeTaskExecutor: execution infrastructure for planned investigation tasks.
- Case Management Engine: creates and stores investigation cases.
- Evidence Engine: normalizes fragmented evidence into consistent records.
- Risk Engine: scores investigation risk using explainable factors.
- AI Investigation Engine: generates analyst-ready investigation narratives.
- Analyst Workspace: provides CLI and web workflows.

## AI Investigator v1

AI Investigator v1 is the core deterministic investigation engine. It accepts a security alert, creates an investigation context, executes a planned task sequence, and returns evidence-backed findings, risk, confidence, recommendations, a report, and an audit trail.

Canonical flow:

```text
InvestigationCoordinator
-> InvestigationOrchestrator
-> Planning
-> RuntimeTaskExecutor
-> Investigation Tasks
-> Evidence / Intelligence / Reasoning
-> Decision Intelligence
-> Report + Audit Trail
```

```python
from sentinel_dna.investigation import InvestigationCoordinator

coordinator = InvestigationCoordinator(data_dir="data")
result = coordinator.investigate(
    "case-001",
    {
        "sender": "security-alert@example-login.com",
        "subject": "Urgent MFA password verification required",
        "body": "Verify at https://example-login.com/security",
        "severity": "high",
    },
)

print(result.plan_name)
print(result.results["decision_intelligence"])
print(result.to_dict())
```

Current v1 capabilities are local and evidence-first: email evidence normalization, IOC extraction/enrichment, entity correlation, timeline construction, deterministic threat intelligence, MITRE ATT&CK mapping, threat classification, risk scoring, confidence scoring, reasoning, recommendations, report generation, and structured task/audit records.

## v1.0 Beta capabilities

- Evidence-first investigation with IOC enrichment, lineage, MITRE mapping, graph intelligence, explainable reasoning, confidence, risk, and decision output.
- Structured analyst report with overview, evidence, attack narrative, response recommendations, detection opportunities, and audit trail.
- Safe SOAR foundation: all containment actions are recommendations and explicitly require analyst approval.
- Analyst workspace dashboard and case-detail pages, including confirm, dismiss, escalate, and note actions recorded in case audit history.
- Demo scenarios for phishing, account compromise, and malware are in `examples/demo_scenarios.json`.

## Demo instructions

Start the workspace with `python -m sentinel_dna.workspace.web_app`, then submit an alert using `InvestigationCoordinator` as shown above. Open the dashboard at `http://127.0.0.1:5000` and select the investigation to review evidence and record analyst actions.

For a CLI-ready phishing example, run `python -m sentinel_dna.workspace.cli --demo`. The account-compromise and malware demo payloads are ready to pass to `InvestigationCoordinator.investigate` from `examples/demo_scenarios.json`.

## Production readiness assessment

Sentinel DNA v1.0 Beta is ready for controlled market-validation demonstrations: its outputs are deterministic, evidence-backed, serializable, and audit-oriented. It is not yet production-deployment ready for autonomous response: integrations with live SIEM/EDR/identity systems, authentication/authorization, multi-user persistence, observability, external threat intelligence, and PDF export remain future hardening work.

## Install

```powershell
cd sentinel-dna-v0.1
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

## Run CLI Demo

```powershell
python -m sentinel_dna.workspace.cli --demo
```

## Run Web Workspace

```powershell
python -m sentinel_dna.workspace.web_app
```

Then open `http://127.0.0.1:5000`.

## Run Tests

```powershell
python -m pytest
```
