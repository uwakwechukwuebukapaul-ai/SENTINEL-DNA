# Design Partner Validation Plan

**Plan status:** Proposed scenario catalogue
**Data boundary:** synthetic or separately approved sanitized data only
**Decision authority:** participating analyst, with reviewer oversight

Each exercise must be assigned an identifier, version, tenant, owner, stop
condition, evidence plan, and reviewer before execution. The descriptions below
define expected behavior to test; they are not claims that the behavior has
already occurred.

## Common evidence requirements

Every scenario must capture the analyst question, evidence references,
timestamps, tenant scope, provenance, independent conclusion, confidence,
missing evidence, advisory comparison, reviewer note, and closeout/revocation
status. Never capture credentials, cookies, tokens, private keys, customer data,
or browser session material.

## Scenario catalogue

### DP-01 â€” Phishing investigation

- **Objective:** assess whether the analyst can reconstruct a suspected phishing
  event from message, identity, and endpoint evidence.
- **Dataset:** synthetic message metadata, sender/domain context, link
  reputation result, identity events, and endpoint timeline.
- **Analyst task:** determine likely attack path, affected synthetic identities,
  confidence, and missing evidence.
- **Expected Sentinel DNA behavior to test:** present source-linked evidence,
  preserve provenance, distinguish facts from inference, and mark advisory
  conclusions as non-authoritative.
- **Human review points:** analyst must decide whether evidence supports the
  conclusion and whether additional collection is needed.
- **Evidence requirements:** message/event references, timeline, reasoning,
  uncertainty, and advisory comparison.
- **Success criteria:** conclusion is reproducible from cited evidence and
  limitations are explicit.

### DP-02 â€” Credential-compromise investigation

- **Objective:** examine investigation of a synthetic account with anomalous
  access and possible credential misuse.
- **Dataset:** synthetic sign-in events, device posture, MFA events, role and
  tenant records, and approved response context.
- **Analyst task:** assess whether compromise is supported, identify gaps, and
  propose bounded next investigative steps.
- **Expected behavior to test:** correlate events without exposing or requesting
  credential values; maintain tenant scope.
- **Human review points:** analyst distinguishes suspicious activity from proof
  of compromise and approves any proposed action.
- **Evidence requirements:** event references, scope, correlation rationale,
  uncertainty, and access-boundary observations.
- **Success criteria:** no credential material is handled and the conclusion is
  evidence-backed or explicitly unresolved.

### DP-03 â€” Malware-alert investigation

- **Objective:** assess triage of a synthetic endpoint alert without executing
  or distributing harmful content.
- **Dataset:** synthetic alert, file metadata, process tree, hash reputation,
  host timeline, and containment state.
- **Analyst task:** classify alert confidence, identify affected scope, and
  decide whether further review is warranted.
- **Expected behavior to test:** preserve source and timestamp context and avoid
  treating an enrichment result as proof.
- **Human review points:** analyst decides severity and whether the evidence is
  enough for escalation.
- **Evidence requirements:** alert/event references, enrichment provenance,
  decision rationale, and unresolved questions.
- **Success criteria:** classification is traceable and unsafe actions remain
  denied.

### DP-04 â€” Suspicious-authentication investigation

- **Objective:** review synthetic impossible-travel, device, or session
  anomalies within one tenant.
- **Dataset:** synthetic authentication timeline, device/location abstractions,
  policy events, and known benign explanations.
- **Analyst task:** compare competing hypotheses and state confidence.
- **Expected behavior to test:** expose contradictory or missing evidence and
  avoid overconfident attribution.
- **Human review points:** analyst chooses the working hypothesis and records
  what would change it.
- **Evidence requirements:** timeline, hypothesis matrix, sources, and
  provenance.
- **Success criteria:** uncertainty and alternative explanations are recorded.

### DP-05 â€” IOC enrichment validation

- **Objective:** assess whether enrichment references are useful, current, and
  traceable for a synthetic indicator.
- **Dataset:** synthetic domains, hashes, IP abstractions, source timestamps,
  confidence labels, and intentionally incomplete results.
- **Analyst task:** verify relevance, freshness, and limitations of enrichment.
- **Expected behavior to test:** preserve source provenance and distinguish
  enrichment from analyst judgment.
- **Human review points:** analyst accepts, rejects, or requests corroboration.
- **Evidence requirements:** source references, retrieval timestamps, confidence,
  and decision rationale.
- **Success criteria:** no unsupported attribution or fabricated source is
  recorded.

### DP-06 â€” MITRE ATT&CK mapping review

- **Objective:** examine whether observed synthetic behaviors support proposed
  technique mappings.
- **Dataset:** synthetic event sequence, behavior descriptions, and mapping
  candidates with known ambiguity.
- **Analyst task:** accept, reject, or qualify mappings and explain evidence.
- **Expected behavior to test:** present mapping rationale and uncertainty rather
  than treating a label as a finding.
- **Human review points:** analyst remains responsible for the final mapping.
- **Evidence requirements:** behavior references, mapping version, rationale,
  alternative mapping, and reviewer note.
- **Success criteria:** mappings are evidence-linked and qualified where
  ambiguity exists.

### DP-07 â€” Evidence-chain review

- **Objective:** test whether a reviewer can reproduce a finding from source to
  conclusion.
- **Dataset:** synthetic investigation with event, enrichment, analyst note,
  and provenance records.
- **Analyst task:** identify missing links, altered context, or unsupported
  conclusions.
- **Expected behavior to test:** show chain order, source identity, timestamps,
  transformations, and reviewer status.
- **Human review points:** reviewer decides whether the chain is sufficient.
- **Evidence requirements:** chain references, hashes where applicable,
  custody, and limitation record.
- **Success criteria:** a separate reviewer can reproduce the reasoning or list
  exactly what prevents reproduction.

### DP-08 â€” AI recommendation review

- **Objective:** test how analysts evaluate advisory recommendations against
  independent reasoning.
- **Dataset:** synthetic investigation with correct, incomplete, and
  intentionally misleading advisory examples.
- **Analyst task:** record independent conclusion, review advisory material, and
  accept, challenge, or reject it.
- **Expected behavior to test:** label output as advisory, preserve evidence
  references, and require human judgment.
- **Human review points:** analyst owns the final decision; reviewer checks for
  automation bias and unexplained adoption.
- **Evidence requirements:** ordering timestamps, advisory summary,
  comparison rationale, confidence, and final conclusion.
- **Success criteria:** agreement is not treated as correctness, and
  disagreement is captured without penalty.

## Scenario decision record

| Field | Value |
| --- | --- |
| Scenario ID/version | [Reference] |
| Partner/analyst/tenant | [Approved references] |
| Planned date/window | [UTC] |
| Stop condition owner | [Name/role] |
| Evidence owner | [Name/role] |
| Status | [PASS/PARTIAL/BLOCKED/NOT_MEASURED] |
| Re-test decision | [Decision/reference] |

