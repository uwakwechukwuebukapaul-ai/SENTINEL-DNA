# Enterprise Operations Layer

## Architecture

Redis uses tenant-scoped, hashed keys for atomic fixed-window rate limiting, TTL cache entries, and optional session mirrors. PostgreSQL remains authoritative for SaaS session expiry and revocation.

Async work is represented by durable application jobs (`queued`, `running`, `completed`, `failed`). The worker invokes `TenantInvestigationService`, which invokes the existing frozen coordinator; no alternate runtime exists.

OIDC and SAML adapters delegate cryptographic token/assertion validation to an approved deployment verifier. The TOTP interface retrieves each secret through a caller-provided secret manager. SCIM remains represented by the existing provider-neutral provisioning contract.

Compliance exports and activity reports are tenant-filtered. Security events use the usage-event audit archive; retention policy objects provide policy cutoffs for a future archival/deletion executor.

## Kubernetes

The Helm chart at `deploy/helm/sentinel-dna` supplies deployment probes, non-root/read-only containers, resource requests/limits, secret references, and deny-by-default network-policy boundaries. Configure ingress, dependency namespaces, managed secrets, and external database/Redis endpoints in the target cluster.
