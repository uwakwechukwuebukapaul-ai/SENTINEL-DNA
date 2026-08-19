# Customer Pilot Execution Guide

Create a tenant-scoped pilot run with `POST /api/pilot/runs`, then execute it through `POST /api/pilot/investigations` with the returned `run_id`, scenario ID, and case ID. The execution delegates to the canonical InvestigationCoordinator.

Track the run with `GET /api/pilot/runs/<run_id>`. Review the canonical investigation view, collect an analyst outcome through the existing investigation-feedback endpoint, then retrieve validation and final outcome projections.

Pilot execution does not automatically close incidents or trigger response actions.
