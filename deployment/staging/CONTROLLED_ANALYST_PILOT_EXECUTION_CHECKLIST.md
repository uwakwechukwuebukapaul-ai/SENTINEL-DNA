# Controlled analyst pilot execution checklist

This is an operator procedure for the remaining authenticated gates. It is
non-production only and does not authorize access or issue an analyst URL.
Run it only after the live staging boundary is corrected and the approved
trusted browser service is available.

## Hard stops before authentication

- [ ] Docker engine is available in the operator shell; record engine/client
      versions without recording environment values or secrets.
- [ ] The inspected pilot containers belong to the isolated staging Compose
      project; application, PostgreSQL, and Redis have no published host ports.
- [ ] `staging_internal` is an internal Docker network and the application can
      reach PostgreSQL/Redis only through that network.
- [ ] The only host publication is exactly
      `127.0.0.1:18443->443/tcp`; stop for any wildcard, LAN, public, or
      additional listener, including host port 443.
- [ ] The private edge certificate is valid for the requested private name
      and has exactly the reviewed SAN contract: `DNS:sentinel-dna-staging`,
      `IP Address:127.0.0.1`, and the configured staging LAN IP.
- [ ] `/health` and `/ready` both return HTTP 200 through the private HTTPS
      endpoint. A healthy response does not prove authenticated gates.
- [ ] The manual validator remains unchanged and the trusted browser bridge
      is available. Do not use standalone browser automation or direct
      credential-bearing HTTP clients.

If any item is unchecked, record it as `NOT_MEASURED`, `FAIL`, or `BLOCKED`
with a reason and stop. Do not create a tenant, account, credential, or URL.

## Manager authentication and exact onboarding scope

1. The manager opens the visible login page through the independently verified
   private origin and enters credentials only through the secure browser
   authentication handoff. Never pass passwords, cookies, CSRF values, or
   activation tokens to the runner or write them to evidence.
2. Confirm `/api/auth/me` identifies an authorized `admin` or `soc_manager`.
   Record only a non-secret manager identifier and the observation reference.
3. Submit one manager-only write without CSRF. Confirm HTTP 403 and verify
   that no state changed. Then use the valid CSRF-protected manager session.
4. With explicit operator approval, create exactly one synthetic pilot tenant
   and exactly one synthetic analyst account. Verify both counts before and
   after the operation. Do not create a production user or a second test
   identity.
5. Confirm the analyst is bound only to role `analyst`, to the one synthetic
   tenant, with an explicit bounded authorization start and expiry.
6. Transfer the one-time activation mechanism through the approved protected
   channel. Do not place the token in logs, source control, runner output, or
   evidence. The manager must not activate the analyst on the analyst's behalf.

## Analyst RBAC and tenant isolation

1. The analyst activates and signs in through the protected channel. Confirm
   secure cookie/session behavior and `/api/auth/me` identity, role, tenant,
   and authorization expiry.
2. Run one CSRF-protected synthetic investigation action. Verify the action
   succeeds only within the assigned tenant and follows the canonical
   investigation execution path. Use synthetic data only; do not notify an
   external party or invoke a destructive action.
3. Read the analyst workspace and resulting investigation. Confirm every
   returned object is scoped to the one synthetic tenant.
4. Request a known foreign-tenant synthetic resource. Pass only on the
   endpoint's documented denial (`403` or indistinguishable `404`). Confirm
   no state, audit scope, or tenant context changed.
5. Attempt pilot provisioning, authorization management, manager resources,
   production resources, and admin-only actions. Each must be denied and must
   not mutate state.

## Audit, provenance, and AI advisory-only validation

- [ ] The synthetic action returns a verifiable tenant-scoped audit event
      reference, not merely HTTP 200.
- [ ] The same action returns a verifiable provenance reference tied to the
      action, investigation, and synthetic tenant.
- [ ] All sensitive actions and denied attempts have non-secret audit status
      records; no credential or token appears in the response or evidence.
- [ ] Human conclusion and AI recommendation are separate fields.
- [ ] The AI result explicitly states advisory-only behavior and requires a
      human review/decision. No AI output can enforce, execute, or approve an
      action by itself.

## Denial boundary testing

Using the analyst session, test the reviewed paths for:

- [ ] pilot provisioning and authorization-management routes;
- [ ] admin escalation and manager resources;
- [ ] database, secrets, metrics, runtime-management, shell, SSH, and
      container-control surfaces;
- [ ] destructive operations and unrestricted SOAR/action execution;
- [ ] foreign-tenant resources.

Record the exact path classification and non-secret HTTP result. A missing,
ambiguous, or unreviewed denial path is `NOT_MEASURED`, not `PASS`.

## Revocation testing

1. The manager revokes the one pilot authorization with a reason.
2. Deactivate the one synthetic analyst account and invalidate active sessions.
3. With the previously active analyst session, verify login renewal,
   workspace reads, investigation reads, and feedback/action writes fail
   closed.
4. Confirm the revocation, deactivation, session invalidation, and
   post-revocation failures are tenant-scoped, auditable, and secret-free.

## Evidence and release decision

Create one new, unique, append-only evidence record under the approved
protected evidence directory. It may contain only non-secret identifiers,
UTC timestamps, statuses, image/configuration/certificate digests, and
tenant-scoped audit/provenance references. Mark any unperformed item
`NOT_MEASURED`; never infer `PASS` from source inspection, a healthy endpoint,
or an HTTP status alone.

The evidence must satisfy the manual validator's required gates:

`manager_authentication`, `csrf_protection`, `analyst_rbac`,
`tenant_isolation`, `audit_logging`, `provenance_verification`,
`investigation_workflow`, `ai_advisory_only`, `deny_cross_tenant`,
`deny_admin_escalation`, `deny_database`, `deny_shell_container`,
`deny_destructive`, and `session_revocation`.

Also record the four revocation outcomes, all sensitive-action audit and
provenance references, secret-free controls, the certified private boundary,
and `analyst_url_issued: false`. Run the unchanged manual validator. Only its
exact result `READY_FOR_CONTROLLED_ANALYST_PILOT` permits a later human
release authority to consider issuing a private analyst endpoint. Any other
result remains blocked.
