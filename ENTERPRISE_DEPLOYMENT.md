# Enterprise Deployment Architecture

The investigation core remains a single canonical workflow. PostgreSQL stores only SaaS records: users, organizations, memberships, sessions, and usage events. Investigation cases, evidence, lineage, and execution contracts remain unchanged.

```text
TLS/WAF -> Sentinel DNA API -> PostgreSQL (SaaS state)
                         -> Redis (rate limits, cache, sessions, jobs)
                         -> worker deployment (future serialized jobs)
                         -> frozen InvestigationCoordinator
```

## Database migration

Development uses SQLite automatically. Production requires `SENTINEL_DNA_SAAS_DATABASE_URL`; install the `postgres` extra and apply `src/sentinel_dna/saas/migrations/001_saas_schema.postgresql.sql` through the deployment migration job before API rollout. No investigation records are migrated by this phase.

## Identity and workers

`platform.identity` defines SAML/OIDC, MFA, and SCIM contracts. Provider adapters must validate signed assertions/tokens, use state/nonce/PKCE where applicable, and map external subjects to existing tenant-scoped users. `platform.workers` defines serializable investigation, report, and enrichment job envelopes; a future worker calls the existing coordinator, never a duplicate runtime.

## Compose validation

Set `POSTGRES_PASSWORD` and a base64-encoded 32-byte `SENTINEL_DNA_ENCRYPTION_KEY`, then run `docker compose -f docker-compose.production.yml up --build`. Put the resulting service behind TLS/WAF and restrict `/metrics` to the monitoring network.
