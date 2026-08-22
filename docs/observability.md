# Observability

Every canonical application request receives a bounded `X-Correlation-ID`; a valid caller-provided identifier is preserved, while malformed or oversized values are replaced. The identifier is safe for response headers and structured diagnostics.

Health and readiness expose component status without secrets. Existing operational analytics remain tenant-scoped and non-punitive. Queue, lease, retry, provider, notification, approval, contradiction, and investigation actions retain case/tenant/actor references in auditable projections.

Logs must not contain credentials, tokens, raw sensitive provider payloads, or private model reasoning. Deployment environments should forward structured logs and correlate them with reverse-proxy and worker telemetry.
