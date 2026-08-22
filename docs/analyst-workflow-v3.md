# Evidence Intelligence Analyst Workflow V3

V3 is the analyst operating layer over the certified V2 investigation projections. It does not create a second investigation engine, evidence store, identity system, or authorization model.

## Architecture

`InvestigationCoordinator` remains the canonical boundary. `AnalystWorkflowV3Service` composes the existing `InvestigationReadModel`, explainability, graph, contradiction, report, lifecycle, assignment, evidence-review, collaboration, feedback, and audit repositories into versioned workflow projections.

The V3 queue is tenant-scoped and uses the canonical report repository's bounded SQL page query. Queue priority is deterministic and exposes its reasons; it is not an opaque model score.

## Workflow

Queue items map existing investigation data to additive workflow states:

`NEW -> CLAIMED -> INVESTIGATING -> REVIEW_REQUIRED -> DECISION_READY -> APPROVAL_REQUIRED -> APPROVED/REJECTED -> DISPOSITIONED -> CLOSED`

The mapping does not replace existing lifecycle states. Assignment, evidence review, contradiction review, collaboration, feedback, approval, and lifecycle events remain append-only and auditable.

## Queue and prioritization

`GET /api/investigations/queue` supports bounded pages and filters for status, severity, workflow state, SLA, escalation, contradiction, priority, intelligence freshness, unassigned, and MITRE presence. Priority reasons include critical/high risk, SLA breach, unresolved contradiction, low confidence, stale intelligence, escalation, low evidence quality, and unassigned ownership.

## Evidence and contradictions

`GET /api/investigations/<case_id>/evidence-priorities` ranks evidence using relationships to findings, IOCs, ATT&CK, contradictions, confidence, and review state. `POST /api/investigations/<case_id>/evidence-review` records append-only review events.

Contradiction review uses the existing contradiction projection and lifecycle repository. Review, resolution, and reopening remain explicit states; no contradiction is silently converted into certainty.

## Collaboration and approval

`POST /api/investigations/<case_id>/notes` is a compatibility-friendly collaboration entry point over the canonical collaboration repository. Notes preserve actor, timestamp, evidence references, and mentions.

Approval requests use the existing lifecycle approval history. Analysts may request review; approval or rejection requires `soc_manager` or `admin` authorization.

## Readiness and decision support

`GET /api/investigations/<case_id>/readiness` returns completion percentage, completed items, warnings, and blocking items. Decision support remains advisory-only. Destructive automation is not exposed by the V3 UI or APIs.

## Security and audit

All V3 endpoints use Authentication V3 request context and canonical tenant authorization. Cross-tenant investigation IDs fail closed. Assignment targets are validated through the canonical assignment directory for active tenant members with analyst, SOC manager, or administrator roles. Mutations emit existing audit events and retain append-only history. Responses reuse redacted read-model/projection data and never expose private chain-of-thought or provider secrets.

## Browser certification

The V3 browser suite covers login, queue rendering/filtering, workflow/readiness/evidence priorities, claim, evidence review, collaboration note, contradiction review, decision, approval authorization/request, audit/history, tenant isolation, authentication denial, redaction, and visual screenshot capture.

## Future extensions

Additional queue dimensions, SQL-native materialized priority indexes, richer manager approval UX, and aggregate productivity telemetry can be added behind the same versioned projection and canonical repository boundaries.
