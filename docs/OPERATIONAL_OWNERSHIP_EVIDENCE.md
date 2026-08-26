# Operational Ownership Evidence

This document is an evidence template only. It does not assign an owner,
authorize deployment, or represent production coverage. Every placeholder must
be replaced by an authorized operator and independently reviewed before release
approval.

Repository or product ownership does not satisfy the production operational
assignments below. Each assignment requires an authorized operating
organization, real evidence, and independent review.

## Bounded founder-operated pilot

The following responsibilities are limited to pilot validation and do not
assign enterprise production operations:

- Monitoring owner: `Uwakwe chukwuebuka paul`
- Alert recipient: `Uwakwe chukwuebuka paul`
- Escalation owner: `Uwakwe chukwuebuka paul`
- Dashboard/query ownership: `Uwakwe chukwuebuka paul`
- Response objective: `Best-effort founder-operated response during pilot validation. Enterprise SLA not established.`
- Alert validation evidence: `PASS` for `MONITOR-PILOT-001` bounded pilot scope only

Pilot evidence must be captured for each validation run:

- Alert generation from a documented synthetic trigger.
- Alert receipt by the named pilot recipient.
- Alert acknowledgement.
- Escalation simulation and observed response.
- Dashboard/query verification.
- UTC timestamps for generation, receipt, acknowledgement, escalation, and
  dashboard/query verification.

The bounded pilot run has now produced non-secret evidence for the listed
generation, receipt, acknowledgement, escalation simulation, and dashboard
query steps. Independent review and enterprise operational ownership remain
unresolved.

The external evidence package must contain, at minimum:

- a manifest with remediation HEAD, pilot scope, and UTC validation window;
- separate records for alert generation, receipt, acknowledgement, and
  escalation simulation;
- a dashboard/query verification record;
- event identifiers and UTC timestamps in each applicable record; and
- a `checksums.sha256` file covering every non-secret package artifact.

Package status: `PASS` for bounded pilot scope; independent review `NOT ATTESTED`.

Observed package:

- Artifact: `pilot-evidence/MONITOR-PILOT-001.json`
- Checksum manifest: `pilot-evidence/checksums.sha256`
- SHA-256: `930146f0ca7644d14ebc0d9ccb6f2cb056602e8dbc5814c8800e576b4ea33e67`
- Command: `python scripts/run_monitoring_pilot.py`

## Founder-operated pilot execution mechanism

The bounded implementation is `services/monitoring/pilot.py` and is executed
from the repository root with:

```text
python scripts/run_monitoring_pilot.py
```

The command writes the append-only artifact
`pilot-evidence/MONITOR-PILOT-001.json` and
`pilot-evidence/checksums.sha256`. It records actual UTC transition times for
generation, receipt, acknowledgement, escalation simulation, and dashboard
query verification. The dashboard/query check uses the existing
`GET /api/command-center/events` path; escalation is an explicitly synthetic
attention-queue simulation and is not an enterprise notification or on-call
route.

The command fails closed if any transition, timestamp, dashboard query,
artifact write, or checksum verification fails. The artifact is `PASS` only
when every bounded pilot state is observed. The recorded execution is complete
for this bounded run; future runs must produce a new append-only output path
and independently reviewed evidence.

Enterprise production assignments remain unresolved in the table below.

## Required assignments

| Evidence requirement | Required evidence | Assignment |
| --- | --- | --- |
| Security ownership assignment | Named security owner, review authority, and effective date | `UNKNOWN — not attested` |
| Incident escalation ownership | Severity-based escalation owner and backup route | `UNKNOWN — not attested` |
| Platform ownership | Platform operator, coverage window, and handoff procedure | `UNKNOWN — not attested` |
| Database ownership | Database operator, backup owner, and recovery responsibility | `UNKNOWN — not attested` |
| Release approval ownership | Release approver and approval record authority | `UNKNOWN — not attested` |
| Operational review responsibility | Review cadence, evidence reviewer, and change follow-up | `UNKNOWN — not attested` |

## Evidence acceptance criteria

- Assignments must come from the authorized operating organization.
- Contact details must be supplied through the approved protected channel; do
  not commit credentials, tokens, private keys, or sensitive contact data here.
- Escalation, database, release approval, and operational review evidence must identify a
  reviewable source and effective date.
- A release reviewer must verify the assignments and record the review outside
  this template before the ownership gate can pass.

## Current status

`NOT ATTESTED — no production owner, on-call identity, escalation route, or
approval record is inferred by repository validation.`
