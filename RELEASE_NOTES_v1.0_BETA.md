# Sentinel DNA v1.0 Beta — Release Notes

## Commercial-validation release

Sentinel DNA v1.0 Beta provides deterministic, evidence-backed SOC investigations with explainable reasoning, graph intelligence, MITRE mapping, risk and confidence assessment, analyst-ready reports, and a browser-based review workspace.

## What is new in this release

- Investigation Intelligence Layer: graph lineage, relationship confidence, graph insights, reasoning trace, and enhanced reporting.
- Analyst Experience: dashboard, investigation detail page, and audited analyst decisions.
- Safe response foundation: approval-required containment recommendations only; no automatic destructive action is performed.
- Detection outputs: IOC searches, hunt queries, and Sigma-style detection representations.
- Operational hardening: centralized environment configuration, case-ID path validation, atomic case persistence, security headers, and health/readiness endpoints.
- Deployment: non-root Docker image with health check and persistent data directory configuration.

## Upgrade and demo

1. Install with `pip install -r requirements.txt` and `pip install -e .`.
2. Run tests with `python -m pytest -q`.
3. Run a demo using `python -m sentinel_dna.workspace.cli --demo`.
4. Start the workspace with `python -m sentinel_dna.workspace.web_app`.
5. Verify `GET /healthz` and `GET /readyz` before a customer demonstration.

## Important beta boundaries

Results are local deterministic analysis, not external threat-intelligence verdicts. Customer deployment requires access control, tenant isolation, secrets management, central logging, backup/retention policy, and integrated SIEM/EDR/identity sources.
