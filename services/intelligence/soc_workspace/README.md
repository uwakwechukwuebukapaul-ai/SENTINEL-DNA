# Unified SOC workspace

The workspace service is a read-only aggregation layer for cases, evidence, threat intelligence, hunting, reasoning, decisions, copilot context, and narratives. It owns presentation data only; the existing intelligence modules remain responsible for their domains. Component failures produce partial data rather than changing investigation behavior.

The data flow supports dashboard views today and can later feed React/WebSocket collaboration, multi-tenant MSSP views, and executive reporting.
