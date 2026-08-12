# Sentinel DNA v1.0 Beta

Sentinel DNA is an AI Investigation Platform that produces evidence-backed security decisions. This v0.1 codebase evolves the earlier AI SOC Analyst prototype into a structured investigation layer between detection and decision.

## Architecture

- InvestigationCoordinator: canonical application/API entry point for `investigate(case_id, alert)`.
- InvestigationOrchestrator: canonical investigation workflow engine.
- RuntimeTaskExecutor: execution infrastructure for planned investigation tasks.
- Case Management Engine: creates and stores investigation cases.
- Evidence Engine: normalizes fragmented evidence into consistent records.
- Evidence Fusion Engine: fuses evidence, IOC intelligence, graph relationships, and MITRE mappings before risk calculation.
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

Current v1 capabilities are local and evidence-first: email evidence normalization, IOC extraction/enrichment, entity correlation, deterministic threat intelligence, MITRE ATT&CK mapping, evidence fusion, threat classification, risk scoring, confidence scoring, reasoning, recommendations, timeline construction, report generation, provenance lineage, replay records, and structured task/audit records.

Canonical investigation sequence:

```text
Alert
-> Context Loading
-> Evidence Collection
-> IOC Intelligence
-> Threat Intelligence Evaluation
-> Entity Correlation
-> MITRE Mapping
-> Evidence Fusion
-> Risk Assessment
-> Confidence Calculation
-> AI Reasoning
-> Decision Intelligence
-> Recommendations
-> Reporting
-> Lineage / Audit / Replay
```

## v1.0 Beta capabilities

- Evidence-first investigation with IOC enrichment, lineage, MITRE mapping, graph intelligence, explainable reasoning, confidence, risk, and decision output.
- Structured analyst report with overview, evidence, attack narrative, response recommendations, detection opportunities, and audit trail.
- Safe SOAR foundation: all containment actions are recommendations and explicitly require analyst approval.
- Analyst workspace dashboard and case-detail pages, including confirm, dismiss, escalate, and note actions recorded in case audit history.
- SaaS boundary foundation with identity, organizations, memberships, role checks, bearer-token authentication, tenant isolation primitives, and usage metering.
- Demo scenarios for phishing, account compromise, and malware are in `examples/demo_scenarios.json`.

## SaaS commercialization foundation

Milestones 1-3 are implemented as a boundary around the frozen investigation core:

- Identity + multi-tenancy: users, organizations, memberships, and roles (`OWNER`, `ADMIN`, `SOC_MANAGER`, `ANALYST`, `VIEWER`).
- Authentication + authorization: secure PBKDF2 password hashing, token sessions, authenticated identity, active organization context, membership verification, and reusable role checks.
- Usage metering: tenant-scoped usage events for investigation starts/completions, evidence processed, IOC enrichment, report generation, and API usage.

Billing, Stripe, payment processing, subscriptions, invoices, checkout, pricing enforcement, and billing UI are not implemented yet.

## Demo instructions

Start the workspace with `python -m sentinel_dna.workspace.web_app`, then submit an alert using `InvestigationCoordinator` as shown above. Open the dashboard at `http://127.0.0.1:5000` and select the investigation to review evidence and record analyst actions.

For a CLI-ready phishing example, run `python -m sentinel_dna.workspace.cli --demo`. The account-compromise and malware demo payloads are ready to pass to `InvestigationCoordinator.investigate` from `examples/demo_scenarios.json`.

## Production readiness assessment

Sentinel DNA v1.0 Beta is ready for controlled market-validation demonstrations and core-platform pilots: its outputs are deterministic, evidence-backed, serializable, replayable, and audit-oriented. It is not yet ready for broad commercial SaaS launch until the SaaS layer is added: authentication, organizations, tenants, subscriptions, billing, usage metering, and customer dashboard.

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

Operational checks are available at `/healthz` and `/readyz`. For container deployment, see [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md) and [RELEASE_NOTES_v1.0_BETA.md](RELEASE_NOTES_v1.0_BETA.md).

## Run Tests

```powershell
python -m pytest
```
