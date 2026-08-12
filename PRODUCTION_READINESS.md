# Production Readiness Assessment

## Current assessment: ready for controlled commercial validation

Sentinel DNA is suitable for guided demos, proof-of-value sessions, and pricing discussions. It produces serializable evidence-backed investigations and keeps an audit trail for the workflow and analyst actions.

## Demonstration checklist

- Set `SENTINEL_DNA_DATA_DIR` to a writable demo-specific location.
- Start the workspace and confirm `/healthz` returns `200` and `/readyz` returns `200`.
- Use the phishing, account-compromise, and malware payloads in `examples/demo_scenarios.json`.
- Review an investigation in the dashboard and record an analyst action.
- Highlight that response actions require approval and remain recommendations.

## Deployment checklist

- Build: `docker build -t sentinel-dna:v1.0-beta .`
- Run: `docker run -p 5000:5000 -v sentinel-data:/var/lib/sentinel-dna sentinel-dna:v1.0-beta`
- Restrict the exposed service behind a reverse proxy with TLS and organization authentication.
- Persist and back up the data volume; avoid placing customer data in ephemeral containers.
- Set log collection, retention, backup, and incident response procedures before a pilot.

## Before production customer workloads

- Add SSO/RBAC and tenant isolation.
- Integrate managed secrets and encryption/key management.
- Add centralized structured logs, metrics, alerting, and disaster-recovery testing.
- Validate external SIEM, EDR, identity, and threat-intelligence integrations.
- Complete security review, load testing, privacy review, and retention controls.
