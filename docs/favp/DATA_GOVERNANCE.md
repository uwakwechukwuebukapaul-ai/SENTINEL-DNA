# FAVP Data Governance

## Allowed data

- operator-supplied participant and organization program metadata;
- invitation, NDA/terms, onboarding, access, and phase statuses;
- references to synthetic/sanitized evidence and their SHA-256 digests;
- analyst decisions, advisory AI outputs, bounded scores, limitations, and
  version identifiers;
- non-sensitive commercial feedback such as requested tier and integrations.

## Prohibited data

Passwords, API keys, tokens, cookies, browser sessions, private keys, raw
customer telemetry, raw evidence payloads, production identifiers, or
credential-bearing invitation material are rejected. The service rejects
sensitive-shaped keys and credential-shaped text before persistence.

## Isolation and custody

Every FAVP table is tenant-scoped and every read includes a tenant predicate.
Timeline, invitation, result, feedback, and evidence rows are append-only at
the database boundary. Evidence records contain references only and use a
per-tenant SHA-256 hash chain with sequence numbers. Audit events are written
through the existing append-only audit service in the same transaction as the
mutation.

Reports are read-only projections. They do not certify analysts, customers,
security posture, revenue, or product-market fit. Empty populations are
reported as insufficient data, not as successful outcomes.
