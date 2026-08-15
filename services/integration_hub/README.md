# Enterprise Integration Hub

The Integration Hub is the lifecycle boundary for external connections. It registers tenant-scoped connectors, stores opaque credential references, validates adapters, checks health, and routes event references. Existing `services/integrations` adapters and registries remain compatible and retain their ingestion/response ownership; this package does not execute SOAR actions or duplicate collectors.

All reads, events, and health checks require tenant scope. Credentials are never returned by the public API. External writes remain adapter- and approval-controlled.
