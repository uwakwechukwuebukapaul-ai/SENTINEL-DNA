# Command and Decision Surface

This read-oriented package consolidates existing Sentinel DNA intelligence into deterministic snapshots, attention queues, evidence context, historical context, and advisory decision items. It preserves tenant scope, provenance, uncertainty, partial subsystem availability, and explicit human review.

It is an orchestration surface, not a new intelligence engine. It does not replace the Platform Intelligence Fabric, Analyst Workspace, Copilot, Evidence Engine, lifecycle, SOAR, or any domain owner; it does not approve, execute, remediate, mutate controls/detections/playbooks/workflows, certify compliance, or make autonomous security decisions. TTS remains an optional presentation seam and is not implemented here.

The in-memory repository is replaceable by SQLite/PostgreSQL without changing the service contract. Future UI, API, role-based, executive, streaming, notification, and voice integrations can consume the normalized models.
