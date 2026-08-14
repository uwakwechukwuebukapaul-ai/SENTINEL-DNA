# Agent memory and collaboration

This layer stores deterministic agent experiences in SQLite, provides tenant-scoped message passing, tracks analyst feedback, and exposes confidence metrics. It is memory and collaboration infrastructure, not uncontrolled learning: it does not train models, alter evidence, bypass governance, call external APIs, or execute actions.
