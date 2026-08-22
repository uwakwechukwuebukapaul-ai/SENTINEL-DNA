# Multi-tenancy

Tenant scope is derived from authenticated identity and canonical authority. Request headers and request bodies are not authoritative tenant selectors. A conflicting tenant header fails closed.

Repositories include tenant predicates for investigations, evidence, reports, graph, explainability, assignments, approvals, operations jobs, notifications, and audit-related projections. Cross-tenant object access returns an indistinguishable not-found response where appropriate. Negative tests cover tampered investigation/evidence IDs and cross-tenant assignment/approval attempts.

New features must reuse the canonical tenant authorization boundary and add a regression test before release.
