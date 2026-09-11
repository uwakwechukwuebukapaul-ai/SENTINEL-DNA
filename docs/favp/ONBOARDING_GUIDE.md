# FAVP Analyst Onboarding Guide

**Audience:** selected founding analysts and session facilitators
**Data rule:** synthetic data only
**Access rule:** bounded, personal, time-limited, and revocable

## Before onboarding

The program owner must complete the following before access is issued:

- application review, identity confirmation, conflict review, and selection
  decision;
- executed participation terms and NDA or documented approval that an NDA is
  not required;
- approved analyst, synthetic tenant, scenario set, dates, support contact,
  and revocation owner;
- staging readiness and trusted-browser activation review;
- evidence directory, audit reference, and provenance-capture readiness;
- incident and stop-condition briefing;
- accessibility and scheduling confirmation.

No analyst access should be issued while the staging activation decision is
`BLOCKED_WITH_REASON`.

## Orientation agenda

The facilitator should cover:

1. FAVP purpose, scope, and non-objectives;
2. synthetic-data boundary and prohibited material;
3. analyst decision authority and advisory-only system output;
4. approved workflow and scenario instructions;
5. tenant boundary and denied-action expectations;
6. evidence and provenance fields;
7. reporting, stop, and incident channels;
8. session end, revocation, and closeout steps.

The facilitator may explain procedure but must not coach the analyst toward a
desired substantive conclusion.

## Access and environment check

Record non-secret references for:

- analyst approval and agreement status;
- approved tenant and scenario scope;
- access start and expiry in UTC;
- staging image/runtime/manifest identities;
- readiness report and provider verification result;
- audit and evidence custody location.

Do not record credentials, cookies, tokens, private keys, raw session values,
or customer information.

## Session procedure

### Start

- confirm the analyst's identity and approved scope;
- confirm the session is private and uses synthetic data;
- record the run identifier and start time;
- confirm the analyst understands that system output is advisory;
- confirm the stop condition and support channel.

### Execute

For each scenario, the analyst should:

1. state the question or decision to be examined;
2. identify the evidence they expect to need;
3. perform the approved workflow;
4. record source, timestamp, tenant scope, and provenance references;
5. record uncertainty, contradictions, and missing evidence;
6. write an independent conclusion before reviewing advisory output;
7. compare the advisory output and accept, challenge, or reject it with a
   reason;
8. record any denied or unexpected action.

### Stop immediately when

- data appears non-synthetic;
- an unexpected tenant or privilege is visible;
- a credential, cookie, token, or session value is exposed;
- audit or provenance cannot be trusted;
- the workflow leaves the approved origin or scenario scope;
- the analyst is asked to make an action outside their authority;
- the program owner or security owner directs a stop.

## Closeout

- record scenario completion and unresolved items;
- preserve only approved non-secret evidence references;
- capture structured scorecard responses;
- record analyst feedback without editing their conclusion;
- revoke access through the approved procedure;
- verify post-revocation denial where in scope;
- record end time, revocation reference, and evidence hash.

## Analyst checklist

- [ ] I used synthetic data only.
- [ ] I stayed within the approved tenant and scenario scope.
- [ ] I made the final analyst decisions independently.
- [ ] I treated system output as advisory.
- [ ] I recorded evidence and provenance references.
- [ ] I reported uncertainty and contradictions.
- [ ] I reported any suspected control or data issue.
- [ ] I completed closeout and access-revocation confirmation.

