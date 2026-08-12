# Sentinel DNA Enterprise Beta Admin Guide

This guide is for enterprise administrators operating Sentinel DNA during the private beta.

## Tenant Administration

Sentinel DNA uses organizations as tenant boundaries. Every tenant-scoped operation requires:

- An authenticated user.
- An active organization context through `X-Sentinel-Org`.
- Membership in the requested organization.
- Sufficient role for the requested operation.

Common tenant tasks:

- Create the first organization during owner registration.
- Add users to the organization.
- Assign roles according to least privilege.
- Monitor usage events and billing state per tenant.
- Review audit records for investigation and administrative activity.

Tenant isolation rule:

```text
User identity + Organization context + Membership check + Role check = Tenant access
```

## Users And Roles

Roles are hierarchical:

| Role | Intended Use |
| --- | --- |
| OWNER | Tenant owner, billing authority, role administration. |
| ADMIN | Operational administrator, user management except owner grants. |
| SOC_MANAGER | SOC workflow manager and investigation oversight. |
| ANALYST | Investigation review and analyst decision recording. |
| VIEWER | Read-only access to tenant data. |

Recommended beta setup:

- Keep at least two owners for each beta tenant.
- Use `ADMIN` for day-to-day platform operators.
- Use `ANALYST` for security analysts.
- Use `VIEWER` for executive or compliance reviewers.
- Avoid shared accounts.

## Configuration

Core production environment:

```text
SENTINEL_DNA_ENV=production
SENTINEL_DNA_DATA_DIR=/var/lib/sentinel-dna
SENTINEL_DNA_SAAS_DATABASE_URL=postgresql://sentinel:<password>@postgres:5432/sentinel
SENTINEL_DNA_REDIS_URL=redis://redis:6379/0
SENTINEL_DNA_SECRET_BACKEND=environment
SENTINEL_DNA_ENCRYPTION_KEY=<base64-encoded-32-byte-key>
SENTINEL_DNA_RATE_LIMIT_PER_MINUTE=120
```

Metrics configuration:

```text
SENTINEL_DNA_METRICS_PRIVATE=false
SENTINEL_DNA_METRICS_TOKEN=
```

Use private metrics mode when `/metrics` is not already protected by a private network, service mesh, ingress policy, or Kubernetes NetworkPolicy:

```text
SENTINEL_DNA_METRICS_PRIVATE=true
SENTINEL_DNA_METRICS_TOKEN=<monitoring-token>
```

Optional Stripe test-mode billing configuration:

```text
STRIPE_SECRET_KEY=<stripe-test-secret>
STRIPE_WEBHOOK_SECRET=<stripe-webhook-secret>
STRIPE_PRICE_IDS={"plan-free":"price_...","plan-team":"price_..."}
```

## Operations

Health endpoints:

- `/healthz`: liveness and storage availability.
- `/readyz`: readiness for traffic.
- `/version`: service version.
- `/metrics`: Prometheus text metrics.

Operational checks:

- Confirm `/readyz` returns `200` before routing traffic.
- Confirm `/healthz` returns `200` after deployment.
- Confirm PostgreSQL connectivity before onboarding tenants.
- Confirm Redis connectivity for multi-instance rate limiting.
- Confirm logs are collected in JSON format.
- Confirm metrics scraping is either private or token-protected.

## Billing Administration

Billing is isolated behind a provider-neutral boundary.

Important behavior:

- If no billing provider is configured, payment operations fail closed.
- Owner or admin role is required for checkout and subscription changes.
- Idempotency keys are required for mutating billing operations.
- Stripe webhooks require valid signatures before processing.

Beta recommendation:

- Use Stripe test mode for billing flow validation.
- Do not treat billing test-mode success as production payment approval.
- Keep plan and entitlement changes controlled by release administrators.

## Incident Operations

Use this first-response checklist:

1. Check `/readyz` and `/healthz`.
2. Confirm database connectivity.
3. Confirm Redis availability.
4. Review recent `authentication_denied`, `authorization_denied`, `rate_limiter_fallback`, and 5xx logs.
5. Confirm worker queue health if asynchronous jobs are enabled.
6. Stop new traffic before rollback.
7. Preserve PostgreSQL and Redis volumes for forensic and recovery review.

## Backup And Recovery

Minimum beta backup posture:

- PostgreSQL scheduled backups.
- Restore test before customer data onboarding.
- Retain deployment manifests and secret references.
- Preserve case, evidence, lineage, and SaaS data directories for local deployments.

Recovery order:

1. Restore database.
2. Restore persistent data directory if used.
3. Redeploy API.
4. Validate `/readyz`.
5. Validate tenant login.
6. Validate representative investigation lookup.
