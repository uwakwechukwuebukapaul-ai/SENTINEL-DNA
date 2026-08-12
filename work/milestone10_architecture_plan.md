# Milestone 10 Architecture Plan

Audit findings:
- SaaS boundary lives under `src/sentinel_dna/saas` with SQLite default and PostgreSQL selected by `SENTINEL_DNA_SAAS_DATABASE_URL`.
- Current SaaS schema covers `users`, `organizations`, `memberships`, `sessions`, and `usage_events`; PostgreSQL uses versioned SQL in `src/sentinel_dna/saas/migrations` while SQLite is embedded in `SAAS_SCHEMA`.
- Tenant identifiers are organization IDs validated as `org-<uuidhex>` with legacy safe slug support such as `org-test`; request tenant context uses `X-Sentinel-Org` or `tenant_id`.
- Auth roles are `OWNER`, `ADMIN`, `SOC_MANAGER`, `ANALYST`, `VIEWER`; API authorization is enforced in `workspace/web_app.py` through `AuthService`.
- Existing usage metrics are `investigation_started`, `investigation_completed`, `evidence_processed`, `ioc_enrichment`, `report_generated`, `api_request`, and `security_event`.
- Compliance/audit currently archives via `UsageMeter`; billing audit events should use that existing SaaS audit surface.
- No billing, subscription, invoice, customer, provider, or entitlement domain exists yet.
- Frozen investigation core files are separate under `src/sentinel_dna/investigation` and will not be modified.

Implementation plan:
- Add provider-neutral billing models and a `BillingService` in `src/sentinel_dna/saas/billing.py`.
- Extend SQLite schema and add PostgreSQL migration `002_billing_schema.postgresql.sql`; update schema loader to apply all versioned PostgreSQL migrations.
- Keep payment operations fail-closed through a `NotConfiguredBillingProvider`; never mark payment success without a real provider.
- Add default plan seeding, billing customers, subscriptions, subscription events, invoices, idempotency keys, and tenant-scoped entitlements.
- Enforce commercial entitlements at the SaaS usage boundary by checking subscription status and usage totals before protected investigations start.
- Add authenticated billing APIs under `/billing/*`, scoped by tenant header and minimum roles; use OWNER/ADMIN for mutations and VIEWER for reads.
- Integrate billing lifecycle actions into audit via existing usage events using new billing-safe audit event types.
- Add focused tests for lifecycle validation, idempotency, provider fail-closed behavior, API authorization, tenant isolation, invoice creation, and entitlement enforcement.
- Update architecture/readiness documentation only where needed.
