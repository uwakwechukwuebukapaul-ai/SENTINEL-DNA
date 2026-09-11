# Gate 5 Controlled Analyst Test Pack

Status: `NOT_EXECUTED`

This pack is the concise human-execution companion to the Gate 5 onboarding and
pilot runbooks. It is a test record template, not pilot evidence. Execute only
with one approved analyst, one isolated non-production tenant, synthetic or
explicitly approved sanitized data, an approved access window, and external
append-only evidence custody.

The authoritative browser journey is:

```text
Secure Login -> MFA -> Organization -> Dashboard -> Case -> Investigation
-> Evidence -> Relationships / Graph -> Timeline -> IOC / Threat Intelligence
-> Contradictions -> MITRE -> Confidence / Uncertainty -> AI Findings
-> Analyst Decision -> Analyst Action -> Investigation Report -> Export
-> Audit -> Logout / expiry / revocation
```

Do not record passwords, OTP/TOTP values, recovery codes, cookies, tokens,
private keys, raw browser session material, customer data, or provider secrets.
Cloud perimeter login and health checks do not prove Sentinel DNA authentication,
authorization, tenant isolation, or analyst acceptance.

## Execution record

| Field | Value |
| --- | --- |
| Pilot / run ID | `[external opaque reference]` |
| Analyst reference | `[approved pseudonym or exact approved identifier]` |
| Manager / reviewer | `[external reference]` |
| Tenant reference | `[isolated synthetic tenant]` |
| Access method and origin | `[approved private origin]` |
| Candidate commit/tree | `[reconciled externally]` |
| Image/runtime identity | `[immutable external references]` |
| Planned UTC window | `[start]` – `[expiry]` |
| Actual UTC window | `[start]` – `[end]` |
| Data classification | `synthetic_sanitized` |
| Customer data | `false` |
| Credentials or tokens captured | `false` |
| Production impact | `false` |
| External notification | `false` |
| Overall status | `NOT_EXECUTED` |

## Journey acceptance checklist

For each stage record `PASS`, `FAIL`, `BLOCKED`, or `NOT_MEASURED`, plus an
opaque evidence reference. A successful previous stage does not imply a later
stage passed.

| Stage | Expected analyst-visible behavior | Result / evidence reference |
| --- | --- | --- |
| Secure Login | Login accepts the approved identity and gives only generic failure messages. | `[ ]` |
| MFA | Enabled MFA requires a valid authenticator or one-time recovery code; pending sessions cannot open protected pages. | `[ ]` |
| Organization | Organization and membership are server-derived; pending, suspended, or revoked access is denied. | `[ ]` |
| Dashboard | Tenant-scoped cases, evidence, timeline, IOC summaries, and analyst activity are visible with honest empty/unavailable states. | `[ ]` |
| Case | The alert/case is identifiable and opens only inside the approved tenant. | `[ ]` |
| Investigation | The analyst can start or inspect the canonical investigation and see execution/provider status. | `[ ]` |
| Evidence | Observed evidence shows stable identifiers, source, time, and provenance. | `[ ]` |
| Relationships / Graph | Evidence links are understandable; absent relationships are shown as unavailable, not invented. | `[ ]` |
| Timeline | Events are ordered with timestamps and source context; gaps remain explicit. | `[ ]` |
| IOC / Threat Intelligence | Enrichment is labeled derived, with provider/freshness/provenance and unavailable status where applicable. | `[ ]` |
| Contradictions | Conflicting or incomplete intelligence is visible and does not become an unsupported conclusion. | `[ ]` |
| MITRE | ATT&CK mappings are labeled derived and linked to supporting evidence or limitations. | `[ ]` |
| Confidence / Uncertainty | Confidence is understandable; uncertainty and missing evidence remain visible. | `[ ]` |
| AI Findings | AI findings/recommendations are visibly advisory and separate from observed evidence. | `[ ]` |
| Analyst Decision | The analyst records an independent decision, rationale, and remaining questions. | `[ ]` |
| Analyst Action | Only authorized, bounded actions are available; writes require CSRF and are auditable. | `[ ]` |
| Investigation Report | The report preserves evidence, provenance, reasoning context, limitations, and execution status. | `[ ]` |
| Export | Export contains only approved tenant-scoped, non-secret report data and an opaque audit/provenance reference. | `[ ]` |
| Audit | The analyst can identify the audit/provenance reference without seeing secret material. | `[ ]` |
| Logout / expiry / revocation | Logout, expiry, and revoked membership fail closed on subsequent protected reads and writes. | `[ ]` |

## Existing synthetic scenario set

The IDs below are copied from the existing versioned `FAVP-SCN-*` and
`FAVP-EXE-*` catalogs. The repository currently exposes ten `FAVP-SCN` records
and eight `FAVP-EXE` records; this pack selects 17 existing IDs for one bounded
test set. It does not create a new scenario catalog. Use only the evidence
actually present in the selected fixture; a coverage label is not evidence that
the fixture contains that condition.

| Scenario ID | Existing scenario | Required review focus | Status |
| --- | --- | --- | --- |
| `FAVP-SCN-001` | Phishing investigation | Phishing delivery, identity linkage, provenance | `NOT_EXECUTED` |
| `FAVP-SCN-002` | Credential compromise | Credential misuse hypothesis, scope, uncertainty | `NOT_EXECUTED` |
| `FAVP-SCN-003` | Suspicious authentication | Sign-in timeline, device/location context, alternatives | `NOT_EXECUTED` |
| `FAVP-SCN-004` | Malware execution | Endpoint compromise, execution chain, safe next steps | `NOT_EXECUTED` |
| `FAVP-SCN-005` | PowerShell abuse | PowerShell context, ATT&CK mapping, intent limits | `NOT_EXECUTED` |
| `FAVP-SCN-006` | Cloud account compromise | Cloud identity, privilege scope, owner approval boundary | `NOT_EXECUTED` |
| `FAVP-SCN-007` | Lateral movement | Host-to-host path, missing telemetry, bounded conclusion | `NOT_EXECUTED` |
| `FAVP-SCN-008` | Command and Control investigation | DNS/proxy context, communication reasoning, no external contact | `NOT_EXECUTED` |
| `FAVP-SCN-009` | Multi-IOC correlation | Relationships, contradictory intelligence, confidence basis | `NOT_EXECUTED` |
| `FAVP-SCN-010` | False positive investigation | Benign explanation, detection gap, disposition | `NOT_EXECUTED` |
| `FAVP-EXE-001` | Phishing investigation | Repeatable analyst decision and evidence references | `NOT_EXECUTED` |
| `FAVP-EXE-002` | Suspicious authentication | AI confidence versus analyst conclusion | `NOT_EXECUTED` |
| `FAVP-EXE-003` | Malware triage | Source-linked execution evidence and no payload execution | `NOT_EXECUTED` |
| `FAVP-EXE-004` | Credential compromise | Valid versus anomalous use and limitations | `NOT_EXECUTED` |
| `FAVP-EXE-005` | PowerShell execution | Fact/inference separation and technique context | `NOT_EXECUTED` |
| `FAVP-EXE-006` | Cloud account anomaly | Access scope and least-privilege reasoning | `NOT_EXECUTED` |
| `FAVP-EXE-007` | IOC investigation | IOC type, freshness, provenance, and corroboration | `NOT_EXECUTED` |

The minimum requested coverage is represented as follows: suspicious IP/domain
is reviewed only when supplied by the approved IOC fixture (`FAVP-EXE-007`),
stale intelligence is recorded only when the fixture marks its source time or
freshness (`FAVP-SCN-009` / `FAVP-EXE-007`), and endpoint compromise is bounded
to the synthetic malware fixture (`FAVP-SCN-004` / `FAVP-EXE-003`). No missing
fixture is to be invented during execution.

## Per-scenario capture sheet

Duplicate this section once for each assigned scenario.

| Field | Value |
| --- | --- |
| Scenario ID / catalog version | `[existing ID]` |
| Analyst objective | `[what the analyst was asked to determine]` |
| Alert / case / investigation references | `[opaque IDs only]` |
| Expected evidence | `[source-linked observations expected from fixture]` |
| Expected investigation result | `[bounded result or unresolved state]` |
| Expected UI behavior | `[observed page, state, empty/error/unavailable behavior]` |
| Expected AI behavior | `[advisory finding, evidence references, confidence, limitations]` |
| Expected analyst decision | `[independent disposition and rationale]` |
| Expected report result | `[provenance, reasoning, uncertainty, export/audit references]` |
| Actual outcome | `[PASS/FAIL/BLOCKED/NOT_MEASURED]` |
| Analyst notes | `[free text without secrets or customer data]` |
| Defect severity | `[S0 critical / S1 high / S2 medium / S3 low / none]` |
| Evidence reference | `[external opaque reference]` |

## Stop conditions and closeout

Stop immediately for cross-tenant data, unauthorized access, secret exposure,
unexpected external notification, destructive action, missing audit/provenance,
unbounded AI action, TLS/origin drift, provider/runtime drift, or any result that
cannot be reproduced from the approved synthetic fixture. Record the condition
as `BLOCKED`, preserve only safe opaque references, revoke access, and escalate
through the approved channel.

At closeout, record analyst logout, session expiry, membership/session
revocation, post-revocation denial, report/export integrity, audit/provenance
references, reviewer disposition, and the final append-only artifact digest.
Unobserved values remain `NOT_MEASURED`; this pack must never be converted into
pilot evidence by filling in expected values alone.
