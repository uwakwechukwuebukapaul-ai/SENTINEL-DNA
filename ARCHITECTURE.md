# Sentinel DNA Architecture

Sentinel DNA is an AI Investigation Platform that produces evidence-backed security decisions.

## Canonical components

- `InvestigationCoordinator` is the application/API entry point and preserves `investigate(case_id, alert)`.
- `InvestigationOrchestrator` is the canonical investigation workflow engine.
- `RuntimeTaskExecutor` executes planned investigation tasks and records success/failure into audit, trace, and replay streams.
- `InvestigationContext` is the shared state object for evidence, intelligence, graph relationships, MITRE mappings, fusion, risk, confidence, reasoning, decisions, recommendations, provenance, replay, and audit trace.
- `InvestigationResult` is the public output contract.

## Investigation workflow

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

Evidence fusion intentionally runs before risk calculation so the risk score can include the fused verdict and confidence signal.

## Production boundary

The core investigation platform is hardened for deterministic, evidence-backed investigations. Commercial SaaS capabilities live only at the SaaS/application boundary:

- authentication
- organizations
- tenants
- subscriptions
- billing
- usage metering
- customer dashboard

## SaaS boundary

Milestones 1-3 add a SaaS boundary above the application APIs without changing the investigation core:

```text
Sentinel DNA
-> SaaS Boundary
-> Authentication / Tenancy / Usage Metering
-> Application APIs
-> Investigation Core
-> AI Investigation Platform
```

Tenant ownership is enforced with defense in depth:

1. Authentication identifies the user.
2. Tenant context identifies the active organization.
3. Authorization verifies membership and role.
4. Data access scopes tenant-aware records to `tenant_id`.

Cases and evidence remain backward-compatible JSON records and now support optional `tenant_id` and `owner_user_id`. Usage, identities, organizations, memberships, and sessions are stored in `sentinel_dna_saas.db`. Existing investigation lineage remains in `investigation_lineage.db`.

## Commercial billing boundary

Milestone 10 adds provider-neutral billing under `sentinel_dna.saas.billing` without changing the frozen investigation core. Billing state is tenant-scoped by organization ID and stored in the SaaS database:

- `billing_plans` defines prices and extensible server-side entitlements.
- `billing_customers` maps organizations to future payment-provider customers.
- `billing_subscriptions` tracks lifecycle status and billing periods.
- `subscription_events` records idempotent lifecycle changes.
- `invoices` records provider-neutral invoice envelopes.

The default provider is `NotConfiguredBillingProvider`, which fails closed for checkout/payment operations. Sentinel DNA does not fake payment success; subscriptions created by the application are internal commercial state only until a real provider adapter is added. Entitlement checks run through the existing usage meter before protected tenant investigations start.

## Operations and migration boundary

The web boundary emits JSON logs and exposes `/healthz`, `/readyz`, `/version`, and Prometheus-text `/metrics`. These operational components wrap the API only; they do not alter the frozen investigation pipeline or its public contracts.

For horizontal deployment, replace the SaaS SQLite adapter with PostgreSQL, use Redis for shared caching/rate limiting, and move long-running application work to background workers. Those changes must continue to call the existing `InvestigationCoordinator.investigate(case_id, alert)` entry point. PostgreSQL schema changes are versioned in `src/sentinel_dna/saas/migrations`; SQLite compatibility is preserved in the embedded SaaS schema.
