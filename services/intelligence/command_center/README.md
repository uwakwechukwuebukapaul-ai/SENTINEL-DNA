# AI SOC command center experience layer

This module is a tenant-aware, read-only aggregation boundary for analyst and
executive views. It composes existing investigations, cases, evidence, threat
intelligence, MITRE, detection, vulnerability, attack-path, and agent outputs.

Decision queue entries are advisory and always require human approval. The
module performs no evidence mutation, detection mutation, or SOAR execution.
Missing inputs produce partial snapshots instead of failing the investigation.
