# Enterprise Integration Hub

The Integration Hub is the lifecycle boundary for external connections. It registers tenant-scoped connectors, stores opaque credential references, validates adapters, checks health, and routes event references. Existing `services/integrations` adapters and registries remain compatible and retain their ingestion/response ownership; this package does not execute SOAR actions or duplicate collectors.

All reads, events, and health checks require tenant scope. Credentials are
never returned by the public API or retained by the process-local registry;
registration accepts legacy payloads only to preserve the interface and
discards them after recording credential presence. Runtime integrations must
resolve an opaque reference through an external vault or KMS-backed provider.
External writes remain adapter- and approval-controlled.
