# Sentinel DNA v1.0 Security Audit Report

Date: 2026-08-12
Scope: authentication, authorization, tenant isolation, IDOR risk, secrets handling, logging leakage, input validation, SQL safety, webhook security, and billing security.

## Executive Summary

Sentinel DNA's SaaS and workspace boundary is broadly release-ready from a security perspective. The platform uses explicit authentication checks, tenant-scoped authorization, parameterized SQL, signed Stripe webhooks, fail-closed billing provider behavior, and allow-listed structured logs.

No critical security defect was found during this audit. The highest remaining security work is operational hardening: ensuring production Redis is consistently used for distributed controls, protecting metrics at the ingress layer, and moving all production secrets to a managed secret backend.

Production security score: 91/100.

## Findings

| ID | Severity | Area | Finding | Status |
| --- | --- | --- | --- | --- |
| SEC-001 | Medium | Metrics | `/metrics` is unauthenticated in the Flask app. This is acceptable only when restricted by ingress/network policy. | Documented gap |
| SEC-002 | Medium | Distributed controls | The app creates a local rate limiter even when `SENTINEL_DNA_REDIS_URL` is configured. In multi-replica production this can weaken global rate limiting. | Documented gap |
| SEC-003 | Low | Secrets | Environment-backed secrets are supported in production. The `external` backend is preferred for mature enterprise deployment, but not enforced. | Documented gap |
| SEC-004 | Low | Webhook payload handling | Stripe webhook signature verification is enforced before processing. Unknown or invalid tenant metadata is not processed into subscription state, but operators should monitor these events. | Accepted |

## Controls Reviewed

Authentication:
- Passwords are hashed with PBKDF2-HMAC-SHA256 at 600,000 iterations.
- Session tokens are random, stored as SHA-256 digests, bounded by expiration, and revocable.
- Authentication errors use generic messages and do not disclose whether a user exists.

Authorization and Tenant Isolation:
- SaaS API routes authenticate before tenant operations.
- Tenant access and role checks are explicit for billing, organization, usage, and investigation actions.
- Organization/member listing is tenant scoped.
- Job status lookup uses both `job_id` and `tenant_id`.
- Billing records, usage events, invoices, and subscriptions are tenant scoped.

IDOR Risk:
- Organization, billing, usage, and job access paths include tenant membership checks.
- Investigation detail/action routes compare requested tenant context with the stored case tenant before access.
- Identifier validation rejects path traversal and malformed SaaS IDs.

Secrets Handling:
- Stripe keys, database URLs, Redis URLs, and encryption keys are environment configured.
- Production mode requires database URL, encryption key when using environment secrets, and a nonzero rate limit.
- Docker Compose uses required variable expansion for production secrets.

Logging Leakage:
- Structured logs use an allow list of safe fields.
- Request bodies, bearer tokens, passwords, and Stripe payloads are not logged by the web boundary.

Input Validation:
- JSON routes require object bodies.
- User email, passwords, display names, organization names, tenant IDs, plan IDs, and idempotency keys are validated.
- Invalid JSON/object shape returns structured 400 responses.

SQL Safety:
- Application queries use parameter binding rather than string interpolation.
- PostgreSQL support adapts qmark placeholders at the database boundary.
- SQLite enables foreign key enforcement.

Webhook Security:
- Stripe webhook signature is required.
- Timestamp tolerance is enforced.
- Duplicate provider event IDs are idempotently ignored.
- Subscription and invoice updates are derived only after signature verification.

Billing Security:
- Checkout, customer creation, subscription creation, cancellation, and invoice creation require owner/admin role.
- Billing provider failures fail closed.
- Checkout and subscription flows preserve idempotency.
- Tenant billing records are isolated by tenant ID.

## Release Recommendation

Security posture is acceptable for v1.0 production release if ingress/network policy restricts `/metrics` and operators configure PostgreSQL, Redis, TLS termination, and managed secrets as documented.
