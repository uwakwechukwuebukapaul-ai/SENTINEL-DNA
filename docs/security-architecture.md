# Security architecture

Authentication V3 is authoritative. Requests derive user, actor, and tenant context from the authenticated session and the canonical identity/tenant authority. A conflicting `X-Organization-ID` header is rejected when a session tenant is already established; request bodies cannot override trusted tenant scope.

Investigation, evidence, graph, explainability, report, assignment, approval, operations, and notification paths are tenant-scoped. Missing or cross-tenant objects fail closed as unauthorized or not found according to the API contract. Analyst actions are append-only where the repository contract requires history.

Provider data is untrusted input. Provider adapters use bounded timeouts, safe destination validation, secret references rather than secret values, and sanitized response projections. Evidence and provider text are never treated as system instructions. Decision support is advisory-only and does not execute destructive actions.

Responses and reports exclude credentials, tokens, provider credentials, filesystem/database details, raw sensitive payloads, and private model reasoning. API errors expose a stable safe code and correlation identifier; diagnostic details remain in protected logs.

Authentication POST endpoints use a bounded local fixed-window limiter in the current one-worker SQLite deployment. Before horizontal scaling, move this seam to the reverse proxy or a shared Redis-backed limiter; the local limiter is not presented as a cross-worker guarantee.
