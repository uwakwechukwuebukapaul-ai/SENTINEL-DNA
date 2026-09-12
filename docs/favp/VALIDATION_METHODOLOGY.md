# FAVP Validation Methodology

**Method status:** Proposed for Phase 0 approval
**Unit of analysis:** analyst Ã— scenario Ã— session
**Data boundary:** synthetic only

## Method purpose

This methodology defines how FAVP will collect and review evidence about
analyst workflow and operational fit. It does not predetermine favorable
results. A conclusion is valid only to the extent supported by the recorded
scope, observations, evidence, and limitations.

## Validation questions

The program owner should select and version a finite set of questions, such as:

- Can the analyst locate and interpret the intended synthetic evidence?
- Can the analyst distinguish known facts, assumptions, and missing evidence?
- Can the analyst reproduce the path from observation to conclusion?
- Are tenant boundaries and denied actions understandable and effective?
- Are audit and provenance records sufficient for later review?
- Does advisory output improve, distract from, or conflict with independent
  analyst reasoning?
- Which workflow, evidence, or control gaps prevent a confident conclusion?

Questions are hypotheses to test, not claims about product performance.

## Scenario design

Each scenario must have:

- a unique versioned identifier;
- a defined synthetic tenant and data set;
- a bounded analyst task and expected evidence types;
- known facts, planted ambiguity, and known missing evidence where appropriate;
- explicit prohibited actions and denial expectations;
- a stop condition and escalation contact;
- an evidence and provenance collection plan;
- a scoring rubric that does not require a preferred conclusion when the
  evidence is intentionally ambiguous.

Scenario authors must record the design rationale and review conflicts before
the scenario enters a participant session.

## Session protocol

1. Confirm participant identity, scope, agreements, and readiness gate.
2. Explain the synthetic-data boundary and analyst authority.
3. Provide only the scenario brief approved for that session.
4. Capture the analyst's initial question and independent reasoning.
5. Permit the analyst to perform the workflow within the approved boundary.
6. Capture evidence references, provenance, timestamps, and denied actions.
7. Expose advisory material only at the defined point in the scenario.
8. Capture whether the analyst accepts, challenges, or rejects it and why.
9. Record final analyst conclusion, confidence, uncertainty, and missing
   evidence.
10. Close the session, revoke access, and verify closeout controls.

Facilitators must not reveal hidden scenario facts or correct the analyst's
reasoning during the measurement window.

## Evidence and provenance standard

Every material observation should be linked to:

- source or evidence reference;
- UTC timestamp;
- approved tenant and scenario scope;
- actor/role reference that contains no credential material;
- relevant application/runtime/image identity;
- transformation or interpretation applied;
- reviewer or confirmation status;
- limitation, contradiction, or missing-evidence note.

Evidence must be secret-free, append-only by procedure, access-controlled, and
hash-verifiable. Raw customer or production data is out of scope.

## Human and advisory comparison

The analyst conclusion is recorded before advisory output where the scenario
permits. The comparison must distinguish:

- agreement supported by the same evidence;
- agreement for different reasons;
- analyst correction of advisory output;
- analyst adoption after independent review;
- unresolved disagreement;
- cases where the evidence is insufficient for either conclusion.

No metric should treat agreement alone as correctness. Correctness requires a
scenario reference answer or reviewer-supported rationale and must disclose
ambiguity.

## Scoring and review

Two reviewers should independently score material sessions when practicable.
Reviewers must record evidence references for each score and disclose any
conflict. Differences are discussed after independent scoring; changes are
logged with the reason and reviewer.

Use `NOT_MEASURED` when a criterion was not observed. Do not convert a missing
observation into a pass, fail, or estimate.

## Stop and escalation criteria

Stop the session for unauthorized access, data boundary failure, credential or
secret exposure, audit/provenance failure, unsafe action, or inability to
verify scope. Escalate through the approved incident channel and preserve only
non-secret records.

## Analysis and reporting

The final report should separate:

- observed findings;
- participant perceptions;
- reviewer interpretations;
- known limitations;
- open risks and owners;
- recommendations requiring a separate decision.

Report denominators, cohort composition, scenario versions, exclusions, and
missing data. Do not generalize from a small or selected cohort without stating
the limitation.

