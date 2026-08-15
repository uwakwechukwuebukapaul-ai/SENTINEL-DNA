# Enterprise Data Exchange and Connector Runtime

This runtime executes provider-agnostic adapter operations, receives event references, normalizes payload shapes, tracks retries and telemetry, and persists tenant-scoped execution history. It does not own ingestion normalization, correlation, investigations, SOAR, or remediation; those capabilities remain with their existing services.

Execution is auditable and failures are represented as execution state. External destructive operations are not introduced by this package.
