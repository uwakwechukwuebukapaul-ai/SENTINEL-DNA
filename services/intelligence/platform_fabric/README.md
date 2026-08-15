# Unified AI SOC Intelligence Fabric
This read-only convergence layer normalizes existing subsystem outputs, preserves provenance, creates reference-only cross-domain relationships, and presents a tenant-scoped SOC operating picture and attention queue.

It does not replace InvestigationCoordinator/Orchestrator, Evidence, threat intelligence, compliance, risk, incident management, Command Center, or any authoritative engine. It does not execute remediation, mutate source systems, make autonomous business decisions, store secrets, or certify compliance. Partial subsystem failures are represented as unavailable in snapshot availability metadata; missing data is not converted into certainty. Future SQLite/PostgreSQL persistence can replace the repository implementation.
