# Sentinel DNA v0.1

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

Current limitations: v1 does not yet connect to enterprise SIEM, EDR, identity, ticketing, or external threat-intelligence platforms. Local deterministic findings are labeled as local rules rather than external intelligence.

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
