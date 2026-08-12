# Sentinel DNA Enterprise Beta Architecture Overview

## System Overview

Sentinel DNA is an AI-native security investigation platform. It converts alerts into evidence-backed decisions through deterministic collection, enrichment, mapping, fusion, risk scoring, recommendations, reporting, and audit records.

## Complete Architecture Diagram

```mermaid
flowchart TD
    User["Enterprise user"] --> Ingress["Ingress / Load balancer / TLS"]
    Ingress --> Web["Sentinel DNA Web/API Workspace"]
    Web --> Auth["Authentication and session boundary"]
    Web --> Metrics["Health, readiness, version, metrics"]
    Auth --> Tenant["Tenant and role authorization"]
    Tenant --> SaaSDB["SaaS database: users, orgs, memberships, sessions, usage"]
    Tenant --> BillingAPI["Billing API boundary"]
    BillingAPI --> BillingService["Provider-neutral billing service"]
    BillingService --> BillingDB["Billing tables"]
    BillingService --> Stripe["Stripe provider adapter"]
    Stripe --> Webhook["Signed provider webhooks"]
    Tenant --> InvestigationSvc["Tenant investigation service"]
    InvestigationSvc --> Core["Investigation core"]
    Core --> Coordinator["InvestigationCoordinator"]
    Coordinator --> Orchestrator["InvestigationOrchestrator"]
    Orchestrator --> Planner["Planning"]
    Planner --> Executor["RuntimeTaskExecutor"]
    Executor --> Evidence["Evidence collection and normalization"]
    Executor --> IOC["IOC enrichment"]
    Executor --> MITRE["MITRE mapping"]
    Executor --> Fusion["EvidenceFusionEngine"]
    Fusion --> Risk["Risk assessment"]
    Risk --> Result["InvestigationResult"]
    Result --> Cases["Case store and audit history"]
    Result --> Lineage["Lineage, replay, provenance"]
    Web --> Redis["Redis: sessions, rate limiting, cache"]
    Web --> Logs["Structured JSON logs"]
```

## SaaS Boundary

The SaaS boundary wraps the investigation core without changing its public contract.

Responsibilities:

- User registration and login.
- Session token issuance and revocation.
- Organization creation.
- Tenant membership and role checks.
- Usage metering.
- Tenant-scoped API access.
- Billing API authorization.
- Operational health and metrics endpoints.

Request pattern:

```text
HTTP request
-> bearer token authentication
-> active tenant context
-> membership check
-> role check
-> tenant-scoped service call
```

## Billing Boundary

Billing is provider neutral. The internal billing model does not depend on Stripe-specific data structures.

```mermaid
flowchart LR
    API["Billing routes"] --> Authz["Owner/admin authorization"]
    Authz --> Validate["Required fields and idempotency"]
    Validate --> Service["BillingService"]
    Service --> Provider["BillingProvider interface"]
    Provider --> NotConfigured["NotConfigured provider: fail closed"]
    Provider --> StripeProvider["Stripe provider"]
    StripeProvider --> StripeAPI["Stripe API"]
    StripeAPI --> Webhooks["Signed webhooks"]
    Webhooks --> Events["Provider event de-duplication"]
    Events --> TenantState["Tenant subscription and invoice state"]
```

Billing principles:

- Missing provider configuration never creates fake payment success.
- Idempotency keys are required for mutation flows.
- Tenant IDs scope customer, subscription, invoice, and provider event records.
- Webhooks are verified before processing.

## Investigation Core

The investigation core is the stable public engine:

```text
InvestigationCoordinator
-> InvestigationOrchestrator
-> Planning
-> RuntimeTaskExecutor
-> Evidence / Intelligence / MITRE / Fusion / Risk / Reasoning
-> InvestigationResult
```

Core outputs:

- Evidence-backed findings.
- Extracted indicators.
- IOC enrichment.
- Entity correlation.
- MITRE ATT&CK mapping.
- Fused evidence verdict.
- Risk score and factors.
- Confidence signal.
- Analyst recommendations.
- Report.
- Audit trail and replay records.

## Deployment Architecture

Recommended enterprise beta deployment:

```mermaid
flowchart TD
    Client["Customer network"] --> LB["TLS load balancer / ingress"]
    LB --> API1["Sentinel DNA API pod"]
    LB --> API2["Sentinel DNA API pod"]
    API1 --> PG["PostgreSQL"]
    API2 --> PG
    API1 --> RD["Redis"]
    API2 --> RD
    API1 --> PV["Persistent data volume, if local artifact storage is used"]
    API2 --> PV
    API1 --> Logs["Log collector"]
    API2 --> Logs
    Prom["Prometheus / monitoring"] --> Metrics["/metrics, private network or token"]
    Metrics --> API1
    Metrics --> API2
```

Deployment controls:

- Docker image runs as non-root.
- Kubernetes deployment uses read-only root filesystem.
- Privilege escalation is disabled.
- Secrets are injected through Kubernetes Secret or equivalent.
- Readiness and liveness probes are configured.
- NetworkPolicy is included.
- Redis-backed rate limiting supports multi-instance deployments.

## Data Stores

| Store | Purpose |
| --- | --- |
| SaaS database | Users, organizations, memberships, sessions, usage, billing state. |
| Case store | Investigation case records and analyst action history. |
| Evidence store | Normalized evidence records. |
| Lineage store | Provenance, replay, and investigation traceability. |
| Redis | Distributed sessions, cache, and rate limiting. |

## Operations Boundary

Operations endpoints:

- `/healthz`
- `/readyz`
- `/version`
- `/metrics`

Operational outputs:

- JSON logs.
- Prometheus text metrics.
- Health/readiness status.
- Audit and usage events.

## Architecture Conclusion

Sentinel DNA's private beta architecture keeps customer-facing SaaS and operations concerns at the boundary while preserving a stable investigation core. This separation supports enterprise beta validation without redesigning the core investigation engine.
