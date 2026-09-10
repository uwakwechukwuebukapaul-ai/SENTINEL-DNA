# Controlled Real-Analyst Pilot Guide

This guide defines preparation for one controlled, non-production analyst
pilot. It is not a production, customer, enterprise, certification, or
independent-approval record. No pilot conclusion may be treated as release
authorization.

## Boundary and ownership

- Pilot owner: `Uwakwe chukwuebuka paul`.
- Authorized analysts: exactly one named analyst account, provisioned and
  approved for this pilot before the run. Record only the account's approved
  identifier or pseudonym in evidence; never record its password or tokens.
- Environment: an isolated non-production environment using synthetic or
  separately approved non-customer data only.
- Tenant: one pilot tenant. The analyst may read and investigate only records
  authorized for that tenant.
- Planned start (UTC): `NOT SET — record before execution`.
- Planned end (UTC): `NOT SET — record before execution`.
- Pilot authorization record: `NOT PROVIDED — required before execution`.

The founder owns this bounded pilot activity only. Enterprise production
ownership, on-call coverage, enterprise SLA, customer approval, compliance
approval, security approval, third-party approval, and independent review
remain unresolved unless separately evidenced.

## Remote access boundary

Application pilot access and remote accessibility are separate gates. The
repository does not contain or verify a public pilot URL, VPN, zero-trust
front door, or hosted non-production environment. Remote accessibility is
therefore **BLOCKED / NOT CONFIGURED** until the founder provisions an
isolated non-production environment behind an approved private HTTPS, VPN, or
zero-trust access boundary and verifies it from the analyst's location. Do
not expose the Flask development server directly to the internet.

The remote analyst receives only the application URL through a protected
channel, a unique analyst account, the pilot authorization ID, its UTC
expiry, the assigned tenant, and the approved scenario IDs. The analyst does
not receive repository or GitHub access, server or SSH access, database
credentials, production credentials or secrets, or unrestricted
administrative privileges. No URL, password, token, or secret is stored in
this repository.

## Allowed and prohibited activity

The analyst may sign in with the unique least-privilege `analyst` role, open
assigned synthetic alerts, review evidence and provenance, inspect IOC and
MITRE context, review AI reasoning and uncertainty, record notes/conclusions
through the existing analyst feedback boundary, inspect the timeline/report,
and sign out. All mutating browser/API requests must use the existing CSRF
and authenticated session controls.

The pilot must not use production credentials, customer data, unrestricted
SOAR actions, autonomous destructive actions, unrestricted command execution,
or external notification. No connector, deployment, database, tag, release,
or production configuration mutation is part of this pilot.

## Canonical workflow

Use the existing architecture and tenant-scoped read model:

1. Sign in through `/login` and verify the server-derived analyst identity and
   tenant.
2. Open `/workspace/` and select only the assigned synthetic alert.
3. Open the investigation detail and report; review evidence, relationships,
   IOC intelligence, MITRE context, reasoning, uncertainty, recommendations,
   timeline, and provenance.
4. Record the analyst's independent conclusion, confidence, evidence used,
   missing evidence, contradictions, and feedback through the existing
   `POST /api/investigations/<case_id>/feedback` endpoint. Use the supported
   decisions (`confirmed`, `accepted`, `rejected`, `modified`,
   `false_positive`, `escalated`, `request_more_evidence`, or `analyst_note`).
5. Record the returned feedback identifier and corresponding audit-event
   identifier. Do not overwrite the AI investigation result.
6. Inspect/export the report where supported, then sign out through the
   authenticated logout route.

The canonical execution path remains:

`InvestigationCoordinator → InvestigationOrchestrator → RuntimeTaskExecutor`

No second investigation path is introduced by this pilot.

## Founder setup and revocation

### Controlled analyst account provisioning

Account creation for this pilot is manager-controlled; public or self-service
registration is not part of the pilot. With
`SENTINEL_DNA_PILOT_ACCESS_REQUIRED=1`, an authenticated `admin` or
`soc_manager` uses the existing session, RBAC, canonical tenant, CSRF, audit,
and pilot-authorization services through:

```text
POST /api/pilot-provisioning
{
  "username": "<unique analyst username>",
  "email": "<unique analyst email>",
  "display_name": "<analyst display name>",
  "tenant_name": "<isolated pilot tenant name>",
  "expires_at": "<UTC ISO-8601 timestamp>",
  "approved_scenarios": ["phishing_compromise", "suspicious_authentication"]
}
```

The server creates a dedicated synthetic-only pilot tenant, binds the new
inactive analyst identity to it, creates the bounded authorization, and
returns a one-time activation token in the protected manager response. The
token is hashed at rest and is never logged, audited, placed in evidence, or
committed to Git. Transfer it to the analyst only through an approved secure
channel. The analyst establishes their own password with
`POST /api/pilot-provisioning/activate`; activation is single-use and expires
independently. The password is processed by the existing authentication
hashing mechanism and is never returned or stored in plaintext.

Use `GET /api/pilot-provisioning` and
`GET /api/pilot-provisioning/<provisioning_id>` for manager review. Use
`POST /api/pilot-provisioning/<provisioning_id>/revoke` with a reason to
deactivate the account, revoke the pilot authorization and tenant, invalidate
active sessions, and write the corresponding audit records. Revoked, expired,
unknown, or cross-tenant records fail closed. Provisioning does not grant
repository, GitHub, shell, SSH, database, production-secret, administrator,
SOAR, or destructive-action access.

Use an authenticated `admin` or `soc_manager` account in the isolated pilot
environment. Set `SENTINEL_DNA_PILOT_ACCESS_REQUIRED=1` before issuing access.
The server derives the authorizing actor and tenant from the authenticated
session; the request must not choose either value. Create an authorization
with:

```text
POST /api/pilot-authorizations
{
  "analyst_id": "<canonical analyst actor ID>",
  "expires_at": "<UTC ISO-8601 timestamp>",
  "approved_scenarios": ["phishing_compromise", "suspicious_authentication"]
}
```

The target must already be an active analyst account with an active analyst
membership in the same pilot tenant. The supported scenario allowlist is
enforced by the service; an unapproved or unknown scenario is denied. Record
the returned authorization ID and audit correlation ID in the protected
pilot run record. Use `GET /api/pilot-authorizations` to review manager
records and `POST /api/pilot-authorizations/<authorization_id>/revoke` with
a reason to end access. Revocation invalidates the analyst's sessions and
the authorization fails closed. The analyst may inspect only their current
scope with `GET /api/pilot-authorizations/current`.

Founder handoff values that are not yet observed must remain `NOT PROVIDED`:
the remote URL, analyst account identifier, authorization ID, tenant ID,
pilot start/end timestamps, and approved scenario execution results.

`REMOTE_ANALYST_ENDPOINT = NOT PROVIDED`. The provisioning capability is not a
remote deployment: private HTTPS/VPN/zero-trust infrastructure must be
provided and verified separately before any external analyst receives access.

## Scenario set

Use a small representative set from the existing deterministic scenario
catalog. At minimum, assign one scenario for each of:

- phishing compromise;
- suspicious authentication;
- malware execution;
- suspicious IP/domain;
- contradictory intelligence; and
- benign false positive.

The repository's existing operational-accuracy fixtures provide deterministic
coverage for phishing, suspicious authentication, malware, contradictory
intelligence, and benign false-positive classes. A suspicious IP/domain case
must be selected from an existing approved fixture or separately approved
synthetic input before execution; it must not be invented in the result
record. The analyst's conclusion is the ground truth for this pilot and must
be recorded as observed, including disagreement with AI output.

## Human-versus-AI measurement

Capture the analyst conclusion and the AI conclusion as separate fields. For
each scenario record:

- analyst and AI conclusions, confidence, and evidence references;
- agreement/disagreement and the rule used to derive it;
- analyst time-to-conclusion, when measured, and measurement method;
- false-positive/false-negative observations;
- missing evidence and contradictions discovered;
- analyst feedback and usability issues; and
- investigation, alert, feedback, audit, and provenance references.

Do not infer agreement, confidence, timing, or accuracy when a value was not
observed. Use `NOT MEASURED` or `NOT RECORDED`. Preserve disagreements and
analyst corrections as append-only evidence.

## Evidence capture contract

The real-analyst pilot record is a run record, not a fixture or release
claim. Store only non-secret fields in an append-only evidence artifact under
the approved pilot evidence directory. The minimum deterministic record is:

```json
{
  "pilot_id": "REAL-ANALYST-PILOT-001",
  "run_id": "operator-assigned",
  "status": "NOT_EXECUTED",
  "owner": "Uwakwe chukwuebuka paul",
  "analyst_id": "RECORD_APPROVED_ID_ON_RUN",
  "environment": "isolated non-production",
  "planned_start_utc": "NOT SET",
  "planned_end_utc": "NOT SET",
  "actual_timestamps_utc": {},
  "application_commit": "RECORD_IMMUTABLE_EXECUTION_COMMIT",
  "tenant_id": "RECORD_PILOT_TENANT_ID",
  "scenarios": [],
  "audit_event_references": [],
  "provenance_references": [],
  "data_controls": {
    "synthetic_or_approved_non_customer_data_only": true,
    "customer_data": false,
    "credentials_or_tokens": false,
    "production_impact": false,
    "external_notification": false
  },
  "sha256": "CALCULATE_AFTER_FINALIZATION"
}
```

Each scenario entry must contain its scenario identifier, alert and
investigation identifiers, actual UTC action timestamps, analyst and AI
measurement fields, outcome, evidence references, feedback reference, audit
reference, and an explicit `PASS`, `FAIL`, `SKIPPED`, or `NOT MEASURED` result.
The JSON above is a capture template only; it is not evidence of an executed
pilot.

Store the finalized non-secret real-analyst artifact under `pilot-evidence/`
with an approved run-specific filename. Update the same directory's
`checksums.sha256` only after the artifact is final. Verify it independently
with PowerShell, for example:

```powershell
Get-FileHash .\pilot-evidence\REAL-ANALYST-PILOT-001.json -Algorithm SHA256
Get-Content .\pilot-evidence\checksums.sha256
```

The artifact must distinguish `NOT EXECUTED`, `EXECUTED`, and `VERIFIED`.
Only an actual external analyst run may change the real-analyst record from
`NOT EXECUTED`; preparation or founder testing is not analyst evidence.

## Revocation and incidents

Before execution, confirm the operator can deactivate the single pilot user
and revoke its sessions. The existing authentication service deactivation
path increments the session version and revokes persistent sessions; record
the real deactivation/revocation event outside the evidence artifact if it
contains sensitive operational details. On suspected cross-tenant access,
credential exposure, data-policy breach, or unintended external action:

1. stop the pilot and preserve the current evidence;
2. deactivate the pilot analyst and revoke sessions;
3. do not send an external notification from the pilot;
4. record the incident and escalation through the approved protected channel;
5. review the audit/provenance trail before any restart.

## Readiness status

Preparation is documented. Application pilot controls are **READY FOR
FOUNDER AUTHORIZATION**, subject to the focused validation results for the
current commit. Remote accessibility is **BLOCKED / NOT CONFIGURED** until
an approved non-production endpoint is provisioned and tested. The real
analyst pilot remains **NOT EXECUTED** until an external analyst actually
performs the workflow and the evidence is captured. The monitoring pilot
evidence is separate bounded synthetic evidence and does not satisfy this
real-analyst pilot record. Production readiness remains **BLOCKED**.
