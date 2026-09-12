# Customer Pilot Measurement and Scorecards

## Measurement rules

Measurements must have a defined cohort, period, denominator, source, method, and limitation. Record `NOT_MEASURED` when the required observation was not collected. Do not infer customer value, risk reduction, or payment intent from usage alone.

Use these statuses:

- `PASS`: the agreed observation was completed and met the order-form criterion.
- `PARTIAL`: some evidence exists, but the criterion or denominator is incomplete.
- `BLOCKED`: the observation could not safely or validly occur.
- `NOT_MEASURED`: no valid observation was collected.

## TRUST scorecard

| Measure | Question | Evidence source | Suggested scale |
|---|---|---|---|
| Analyst confidence | Can the analyst explain why they accepted, qualified, or rejected an output? | Survey plus sampled review | 1–5 with comments |
| Explainability | Could the analyst identify the inputs, reasoning boundary, and uncertainty? | Recommendation review | Pass/partial/blocked |
| Provenance quality | Are source, time, transformation, and linkage fields present? | Evidence record audit | Pass/partial/blocked |
| Evidence usefulness | Did the evidence help the defined review or decision? | Analyst and reviewer assessment | 1–5 with evidence reference |

## USAGE scorecard

| Measure | Definition | Evidence source | Guardrail |
|---|---|---|---|
| Investigations completed | Approved investigations reaching the agreed review state | Case register | Report numerator and denominator |
| Analyst adoption | Named analysts with at least one valid session in the period | Access/session record | Exclude service accounts |
| Workflow integration | Agreed workflow steps used with the product | Workflow checklist | Do not call use a success result |
| Blocked workflows | Attempts stopped by product, control, data, or process blocker | Blocker register | Categorize cause and owner |

## EVIDENCE scorecard

| Measure | Question | Evidence source |
|---|---|---|
| Completeness | Are the required evidence fields present for sampled cases? | Evidence-quality review |
| Auditability | Can an authorized reviewer reconstruct access and relevant events? | Audit log review |
| Replay capability | Can the approved reviewer reproduce the evidence view or decision path? | Replay test record |
| Decision traceability | Is the human decision linked to supporting evidence and rationale? | Case and review records |

## PAYMENT scorecard

| Measure | Question | Evidence source |
|---|---|---|
| Willingness to pay | Has an authorized stakeholder stated a budget or buying intention for a defined scope? | Recorded customer statement |
| Budget owner engagement | Has the budget owner reviewed evidence and scope? | Meeting record |
| Procurement readiness | Are security, legal, vendor, and purchase steps identified? | Procurement tracker |

Payment intent is not revenue, a booking, or a forecast. Record the statement, speaker role, date, scope, and confidence level; do not embellish it.

## Scorecard cadence

| Cadence | Output |
|---|---|
| Per investigation | Evidence quality and analyst decision record |
| Weekly | TRUST, USAGE, EVIDENCE, blockers, and actions |
| Midpoint | Scope health, control review, and conversion hypothesis |
| Closeout | Final scorecard, limitations, decision, and next-stage owner |

## Time-savings baseline

If time savings is evaluated, define the pre-pilot baseline, comparable task, analyst cohort, measurement method, exclusions, and sample size before collecting pilot observations. Report raw observations and limitations; do not claim savings from anecdote or self-selection.
