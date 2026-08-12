# Sentinel DNA Enterprise Beta Security Whitepaper

## Executive Summary

Sentinel DNA is an evidence-backed security investigation platform designed for private enterprise beta deployment. Its core security posture is based on explicit identity, tenant isolation, role-based authorization, deterministic investigation records, signed provider callbacks, structured audit trails, and conservative fail-closed behavior for sensitive commercial operations.

The investigation core remains isolated from SaaS commercialization concerns. Authentication, tenancy, usage metering, billing, operations, and deployment controls live at the application and SaaS boundary.

## Architecture Security Model

Sentinel DNA separates platform responsibilities into security domains:

```text
Enterprise User
-> Authenticated API / Workspace
-> SaaS Boundary
-> Tenant Authorization
-> Case / Evidence / Usage / Billing Stores
-> Investigation Core
-> Evidence-backed Result
```

Security design principles:

- Authenticate before tenant access.
- Authorize every tenant-scoped operation.
- Keep tenant ID checks close to data access.
- Use parameterized SQL.
- Store session tokens as digests.
- Fail closed for payment provider operations.
- Verify webhook signatures before processing provider events.
- Log operational metadata without request bodies or secrets.

## Tenant Isolation

Organizations are Sentinel DNA tenants. Tenant isolation is enforced through:

- `X-Sentinel-Org` active tenant context.
- Organization membership checks.
- Role checks for privileged actions.
- Tenant-scoped database queries.
- Tenant-aware billing records.
- Tenant-aware usage metering.
- Tenant-aware job lookup.
- Tenant-aware case and evidence access.

IDOR mitigation:

- Users cannot access organizations where they lack membership.
- Investigation detail routes compare requested tenant context with stored case tenant.
- Billing and usage APIs require tenant membership.
- Job records are looked up by both job ID and tenant ID.
- SaaS identifiers are validated before use.

## Authentication

Sentinel DNA beta authentication uses:

- Email and password login.
- PBKDF2-HMAC-SHA256 password hashing.
- Per-password salt.
- High iteration count.
- Random bearer tokens.
- Token digest storage.
- Session expiration.
- Token revocation.

Security properties:

- Plaintext passwords are not stored.
- Bearer tokens are not stored directly.
- Invalid login failures are generic.
- Inactive users cannot authenticate.
- Distributed session mirroring is available through Redis.

## Authorization

Authorization uses role-based access control at the SaaS boundary.

Roles:

- `OWNER`
- `ADMIN`
- `SOC_MANAGER`
- `ANALYST`
- `VIEWER`

Sensitive operations require elevated roles:

- Tenant member administration: owner/admin.
- Owner role grant: owner only.
- Billing checkout: owner/admin.
- Subscription creation/cancellation: owner/admin.
- Invoice creation: owner/admin.
- Investigation analyst actions: analyst or above.

Read operations are constrained to tenant membership and minimum role where applicable.

## Auditability

Sentinel DNA creates audit and traceability records across the investigation and SaaS boundary:

- Case event history.
- Investigation task audit records.
- Evidence provenance and lineage.
- Replay records.
- Usage events.
- Billing lifecycle events.
- Provider webhook event de-duplication.
- Authentication and authorization denial logs.

Auditability goals:

- Explain why an investigation reached a decision.
- Preserve evidence and reasoning context.
- Support replay and validation.
- Allow administrators to review tenant activity.
- Keep operational logs free of sensitive payloads.

## Data Protection

Data protection controls:

- Production configuration requires an encryption key when using environment-backed secrets.
- Production requires PostgreSQL rather than local-only SaaS state.
- Production requires nonzero rate limiting.
- Docker runs as a non-root user.
- Kubernetes deployment uses read-only root filesystem and disallows privilege escalation.
- Kubernetes secrets inject runtime configuration.
- NetworkPolicy restricts service ingress and egress.

Logging protection:

- Structured JSON logs use an allow list of fields.
- Request bodies, passwords, bearer tokens, and payment payloads are not logged by default.

Metrics protection:

- `/metrics` supports default private-network scraping.
- Optional private metrics mode requires a configured token.

## Webhook Security

Stripe webhook processing is protected by:

- Required Stripe signature header.
- HMAC verification.
- Timestamp tolerance.
- Duplicate provider event detection.
- Tenant and plan metadata extraction only after signature verification.

If Stripe is not configured, billing provider operations fail closed rather than simulating success.

## Billing Security

Billing uses a provider-neutral abstraction:

```text
Billing API
-> Tenant role check
-> Required field validation
-> Idempotency handling
-> Billing provider
-> Provider result or fail-closed 503
```

Security properties:

- Checkout requires owner/admin.
- Subscription mutation requires owner/admin.
- Billing records are tenant scoped.
- Idempotency keys prevent duplicate lifecycle effects.
- Missing provider configuration returns service unavailable for payment flows.

## Beta Security Boundaries

Enterprise beta operators are responsible for:

- TLS termination.
- Identity policy outside Sentinel DNA local accounts, if SSO is added later.
- Secret rotation.
- Database backup encryption.
- Private access to metrics.
- Network access restrictions.
- Customer environment monitoring.

## Security Conclusion

Sentinel DNA is suitable for private enterprise beta use when deployed with PostgreSQL, Redis, secret management, TLS termination, restricted metrics access, and routine backup validation. The current model is intentionally conservative: high-risk operations require authentication, tenant membership, role authorization, and fail-closed provider behavior.
