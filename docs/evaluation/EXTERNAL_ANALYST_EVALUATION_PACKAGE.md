# Zero-Cost External SOC Analyst Evaluation Package

Status: `TECHNICALLY ACCESS-READY; EXTERNAL EVALUATION NOT EXECUTED`

This package prepares one independent cybersecurity/SOC professional to
evaluate Sentinel DNA against synthetic data in an isolated, non-production
environment. It is product-validation material only. It is not Gate 5
custody evidence, release authority, production authorization, or evidence
that the product is effective.

## Hard boundary

The analyst receives only a private application URL and a dedicated,
time-limited application account after the operator completes the access
gates. The analyst receives no repository, GitHub, shell, SSH, Docker,
PostgreSQL, Redis, infrastructure, production, management, or secret access.

Use one synthetic-only pilot tenant. Do not use customer data, production
credentials, production URLs, real incidents, or real secrets. Do not expose
the development server or any database/management port publicly. The external
analyst result must remain separate from Gate 5 custody evidence.

## Current-main readiness finding

The current-main pilot flow already provides:

- manager-only, CSRF-protected provisioning;
- a dedicated isolated synthetic pilot tenant;
- canonical identity and active `analyst` membership binding;
- server-controlled tenant and role derivation;
- bounded approved-scenario authorization;
- one-time activation with hashed-at-rest activation state;
- analyst-selected password establishment;
- account, authorization, tenant, and session expiry/revocation;
- tenant-scoped investigation and feedback boundaries; and
- audit records without passwords or activation values.

Current main now enforces a server-side TOTP step for pilot analyst accounts
before SOC authorization. Password authentication places an MFA-required
account in a non-SOC authentication stage; protected pages and APIs reject
requests until a valid, non-replayed TOTP code establishes a short-lived,
server-bound MFA session. The TOTP seed is encrypted at rest, and the
enrollment, verification, failure, blocking, logout, and revocation paths are
audited without secrets. Existing registration, recovery, and email-OTP
routes remain distinct from this MFA boundary.

This implementation is covered by focused security tests and affected
authentication/security regression tests. It does not activate an external
analyst or establish independent external validation. Activation remains a
separate, explicitly authorized non-production operation.

## Approved identity and access sequence

The intended sequence is:

1. An authorized `admin` or `soc_manager` authenticates in the isolated
   non-production environment.
2. The manager provisions exactly one analyst through the existing
   `POST /api/pilot-provisioning` boundary.
3. The service creates one synthetic-only pilot tenant and an inactive,
   analyst-role account with an explicit maximum lifetime of 30 days.
4. The one-time activation mechanism is transferred to the analyst through a
   protected channel. It is never placed in Git, logs, tickets, screenshots,
   evaluation records, or chat.
5. The analyst uses `POST /api/pilot-provisioning/activate` to choose their
   own password. The mechanism is single-use and independently expiring.
6. The analyst completes the enforced MFA enrollment/challenge.
7. The server derives tenant and role from the canonical authenticated
   principal. Client-supplied tenant, role, or manager identifiers are not
   trusted.
8. The analyst accesses only the assigned synthetic investigation surface.
9. The manager revokes the account and authorization after the evaluation or
   immediately on incident. Revocation must invalidate active sessions.

Passwords, activation values, MFA recovery material, cookies, session IDs,
private keys, certificates, and database or infrastructure credentials are
never recorded in the evaluation package.

## Synthetic case set

Assign only identifiers accepted by the current pilot scenario catalog. The
recommended zero-cost set is:

- `phishing_compromise` — phishing compromise;
- `credential_theft` — credential theft;
- `malware_execution` — malware execution;
- `suspicious_authentication` — suspicious authentication;
- `lateral_movement` — lateral movement;
- `command_and_control` — command and control;
- `benign_false_positive` — benign false positive;
- `multi_ioc_investigation` — multi-IOC investigation; and
- `suspicious_powershell_execution` — suspicious PowerShell execution.

The catalog does not currently approve a literal `suspicious_ip_domain` or
`phishing_url` identifier. Do not invent those IDs. Use an approved existing
fixture or leave the category untested and record the limitation.

## Analyst protocol

For every assigned case, the analyst independently records observations before
seeing or accepting any suggested conclusion. The analyst may disagree with,
correct, or reject the system output.

Review:

1. investigation usefulness;
2. evidence quality;
3. evidence traceability;
4. AI reasoning clarity;
5. confidence transparency;
6. attack reconstruction;
7. MITRE ATT&CK mapping;
8. IOC and surrounding-context usefulness;
9. false-positive handling;
10. ease of use;
11. investigation speed and friction;
12. confusing or misleading behavior;
13. security and privacy concerns;
14. changes the analyst would want; and
15. whether Sentinel DNA is useful as an investigation aid.

Use the existing analyst workspace, investigation detail/report, evidence and
provenance views, timeline, and feedback boundary. Record the case ID,
investigation ID, evidence references, feedback reference, and audit reference
where the application exposes them. Do not ask the analyst to prove that
Sentinel DNA is good, and do not convert observations into a product score or
ranking.

## Evidence preservation

Use the accompanying form as a run-specific record. Before execution, create
the record outside the application source tree in the approved protected
operator evidence location with status `NOT_EXECUTED`. The record must contain
only non-secret values:

- evaluator identifier or approved pseudonym and role;
- UTC evaluation date and time window;
- exact evaluated Sentinel DNA commit/version;
- isolated environment classification;
- synthetic tenant identifier;
- pilot authorization identifier and expiry;
- assigned approved case IDs;
- observations, findings, limitations, and recommendations; and
- audit/provenance references that contain no credentials or tokens.

After the analyst completes the run, finalize the record, compute SHA-256, and
store the hash in a separate protected manifest. A second reviewer may verify
the hash and change the record status to `VERIFIED`. Preserve the original
record; corrections are append-only addenda. Never edit a record to improve a
result, manufacture an outcome, or establish release authority.

The record is product-validation evidence only. It cannot authorize Gate 5,
production, image release, or any deployment.

## Stop and revoke conditions

Stop the evaluation and revoke the account if there is suspected cross-tenant
access, privilege escalation, MFA bypass, credential or activation-value
exposure, customer-data exposure, production-data exposure, unexpected
external notification, or any destructive action. Preserve the non-secret
audit references and report the incident through the protected operator
channel. Do not restart access until the boundary is reviewed.

## Readiness decision

`TECHNICALLY ACCESS-READY FOR EXPLICIT NON-PRODUCTION AUTHORIZATION; EXTERNAL
EVALUATION NOT EXECUTED`

The server-enforced MFA contract is implemented and covered by focused and
affected regression tests. The next action is independent security review and
explicit authorization of a separate non-production activation procedure.
Remote endpoint provisioning is a separate infrastructure action and is
outside this package.
