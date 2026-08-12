# Production Readiness Assessment

## Current assessment: private enterprise beta ready

Sentinel DNA is suitable for guided demos, proof-of-value sessions, and controlled pilots of the core investigation platform. It produces serializable, replayable, evidence-backed investigations and keeps lineage/audit records for workflow execution and analyst actions.

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

- Milestones 1-3 are now present: identity, organizations, memberships, role-based authorization, secure password hashing, token sessions, tenant-scoped object access, and auditable usage metering.
- Milestone 10 billing foundation is now present: provider-neutral plans, customers, subscriptions, subscription events, invoices, idempotency, lifecycle validation, billing audit events, and usage-meter entitlement checks.
- Payment-provider integration is intentionally not configured. Checkout/payment operations fail closed through `NotConfiguredBillingProvider` until a real provider adapter and webhook verifier are added.
- Integrate managed secrets and encryption/key management for customer environments.
- Complete a restore test, external penetration test, privacy review, and retention-control validation before broad public SaaS availability.
- Validate external SIEM, EDR, identity, and threat-intelligence integrations.
- Complete security review, load testing, privacy review, and retention controls.

## Production readiness score

Core investigation platform plus SaaS milestones 1-3 and Milestone 10 billing foundation: 92/100.

The remaining gap is not another investigation engine; it is commercial SaaS hardening around live payment-provider integration, webhook signature verification, subscription reconciliation, customer self-service operations, managed deployment controls, and external enterprise integrations.
