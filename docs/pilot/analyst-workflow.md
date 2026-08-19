# Analyst Validation Workflow

1. Select a scenario and submit `POST /api/pilot/investigations`.
2. Review the canonical investigation view and its evidence references.
3. Validate findings, provenance, confidence, quality, IOCs, MITRE mapping, and timeline.
4. Record one immutable analyst outcome using the existing feedback endpoint. Use the reason field for an auditable note; feedback remains advisory.
5. Review `GET /api/investigations/<case_id>/metrics` and `GET /api/pilot/runs/<run_id>/validation`.
6. Share the tenant-scoped customer summary only after analyst review.

Supported outcomes remain accepted, rejected, modified, false_positive, and escalated. “Advisory only” describes AI recommendations, not an additional analyst-decision state.
