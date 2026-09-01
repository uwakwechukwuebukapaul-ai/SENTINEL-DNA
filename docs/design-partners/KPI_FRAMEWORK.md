# Design Partner KPI Framework

**Status:** Proposed measurement framework
**Owner:** [Named owner]
**Cadence:** [Weekly operating review / monthly leadership review / phase close]

This framework measures program activity, evidence quality, partner health, and
commercial readiness. It does not fabricate results or assign conversion
probabilities without an approved method.

## Dashboard definitions

| KPI | Definition | Source | Guardrail |
| --- | --- | --- | --- |
| Active partners | Partners with approved scope and at least one active engagement during the period. | Partner register. | Report tier, dates, and paused partners separately. |
| Investigations completed | Approved scenarios closed with a recorded analyst conclusion. | Session register. | Completion does not imply correctness. |
| Analyst sessions | Sessions started by named approved analysts. | Access/session records. | Exclude unauthorized or out-of-scope sessions. |
| Evidence reviews | Evidence packages reviewed by an authorized reviewer. | Evidence register. | Count only reviewable packages; disclose missing records. |
| Feedback volume | Accepted feedback items by type and partner. | Feedback system. | Separate bugs, risks, requests, and perceptions. |
| Trust score | Average or distribution of the versioned trust survey response. | Weekly survey. | Include response count and do not treat perception as proof. |
| Adoption score | Defined weighted use of approved workflows/scenarios. | Session and scenario records. | Publish formula before use; no hidden weighting. |
| Conversion probability | Only an approved forecast field based on named buyer, stage, evidence, and confidence. | CRM/partner register. | Never infer from usage or label it a result. |
| Paid-pilot readiness | Partners meeting every approved paid-pilot gate. | Readiness checklist. | Any critical security or evidence blocker means not ready. |
| Evidence quality rate | Evidence reviews passing the agreed completeness/provenance rubric Ã· reviews assessed. | Evidence validator/reviewer. | Report denominator and exclusions. |
| Time-to-decision | Time from approved scenario start to recorded analyst decision. | Timestamped session record. | Do not optimize time at the expense of evidence or human review. |
| Payment intent | Count and proportion of qualified buyer conversations with a documented next commercial step. | Interview/CRM record. | Analyst interest is not payment intent. |

## Dashboard fields

Every reporting row should include:

- reporting period;
- partner tier and anonymized partner reference where appropriate;
- numerator/denominator or count method;
- scenario and survey versions;
- source/evidence reference;
- missing-data and exclusion note;
- owner and next action;
- confidence/limitation note.

## Partner health view

Track per partner:

- engagement status and last meaningful activity;
- scenario coverage;
- feedback recency and actionability;
- trust, confidence, usefulness, and evidence-quality responses;
- security/control issues;
- decision owner and next meeting;
- commercial stage, buyer, and evidence for that stage;
- access expiry and closeout status.

## Paid-pilot readiness scorecard

Use `PASS`, `BLOCKED`, or `NOT_MEASURED`:

- problem and decision owner identified;
- validation evidence reviewed;
- synthetic/sanitized data boundary approved;
- security and privacy review path complete;
- technical scope and support model defined;
- success and exit criteria measurable;
- price basis and procurement path identified;
- customer sponsor has approved next-step discussion;
- access/revocation and evidence custody plan ready.

The scorecard is a gate, not a probability model.

