# Gate 5 Analyst Onboarding Checklist

This checklist governs one approved analyst in the non-production staging
pilot. It does not create an identity or assert that a pilot occurred.

## Minimum operator sequence

Run these steps in order. Stop at the first unchecked item; do not continue by
using a bypass, alternate origin, or inferred PASS.

1. Verify Gate 4 readiness, current staging custody identities, private TLS,
   loopback-only edge publication, and fresh backup/isolated-restore evidence.
2. Obtain external approval for this analyst, one synthetic tenant, the
   scenario scope, expiry, remote access method, and rollback owner.
3. Create a unique external run ID and open an append-only evidence record with
   class `remote_access_preflight` and status `NOT_EXECUTED`.
4. Validate the private remote path without authentication. Confirm the exact
   origin, certificate/SNI, same-origin behavior, and denial of all internal
   service ports. If any check fails, leave the record blocked.
5. Have the manager authenticate through the approved browser-auth flow,
   verify manager role/session and CSRF denial, then provision only the
   approved synthetic analyst scope if authorized.
6. Have the analyst authenticate through the approved channel. Verify the
   server-derived analyst role, tenant, authorization expiry, and workspace;
   record only opaque references, never credentials or session values.
7. Execute the bounded synthetic workflow and directly observe RBAC denials,
   foreign-tenant denial/no leakage, audit/provenance references, and
   advisory-only AI handling. Mark anything unperformed `NOT_MEASURED`.
8. Revoke authorization, deactivate the analyst, invalidate sessions, verify
   post-revocation denial, disable/narrow the remote access policy, seal the
   external evidence, and run every required validator.

The record may use class `authenticated_controlled_analyst_pilot` only after
the analyst actually completes the approved workflow. Rehearsal and access
preflight records remain separate and cannot satisfy pilot completion.

## Approval and scope

- [ ] Security/release owner approved the specific analyst, environment,
      scenario set, access method, and UTC expiry.
- [ ] Analyst identity was verified through the approved identity provider;
      record only an opaque identity reference.
- [ ] Analyst device and MFA requirements were verified where required.
- [ ] Exactly one synthetic tenant and one analyst are in scope.
- [ ] No production credentials, customer data, production routes, or
      production database are in scope.
- [ ] Operator, reviewer, audit owner, and rollback owner are named.
- [ ] Unique run ID and evidence custody location were created externally.

## Environment and access

- [ ] Gate 4 returns `READY_FOR_ANALYST_PILOT` with all 13 checks PASS.
- [ ] Current runtime/image/bridge/manifest/TLS identities match custody.
- [ ] Fresh staging backup and isolated restore evidence is PASS.
- [ ] Private access method is approved: Cloudflare One private application or
      narrowly routed WireGuard overlay.
- [ ] No public hostname route or wildcard listener exists.
- [ ] Analyst can reach only the certified browser surface.
- [ ] Database, Redis, SSH, Docker, shell, metrics, management, repository,
      and production routes are denied or unroutable.
- [ ] Remote request uses exactly `https://sentinel-dna-staging:18443`.
- [ ] Approved CA validates the certificate and `sentinel-dna-staging` SNI.
- [ ] Cookies, CSRF, Host, Origin, and redirects remain same-origin.

## Manager approval and onboarding

- [ ] Manager signs in through the approved browser-auth bridge.
- [ ] Manager role and active session are directly verified.
- [ ] Missing-CSRF request is denied before any protected write.
- [ ] Manager provisions only the approved synthetic tenant and analyst through
      the protected workflow, if authorized.
- [ ] Authorization is explicitly bounded by tenant, role, scenario, and UTC
      expiry.
- [ ] One-time activation is transferred only through the approved secure
      channel; it is not recorded in Git, tickets, logs, or evidence.
- [ ] Analyst activates their own access.
- [ ] Analyst sees only the approved analyst workspace.
- [ ] Record opaque analyst, tenant, authorization, audit, provenance, and
      custody references only.

## Authentication and RBAC verification

- [ ] Authenticated analyst access is directly observed and referenced.
- [ ] Analyst role is `analyst`; no manager/admin privilege is present.
- [ ] CSRF protection is enforced for protected writes.
- [ ] Analyst can complete only the approved non-destructive synthetic
      investigation.
- [ ] Admin escalation, authorization management, provisioning, database,
      shell/container, runtime-management, secrets, metrics, and destructive
      requests fail closed and do not mutate state.
- [ ] Each denial has a safe status and opaque audit reference.

## Tenant isolation verification

- [ ] Analyst tenant context is server-derived and matches the approved tenant.
- [ ] Workspace, investigation, result, feedback, and evidence are tenant
      scoped.
- [ ] Known foreign-tenant resource returns `403` or indistinguishable `404`.
- [ ] No foreign tenant identifier, payload, audit content, provenance, or
      changed tenant context is observable.
- [ ] AI recommendation remains advisory-only and separate from the analyst's
      human conclusion.

## Audit and provenance verification

- [ ] Audit sink was active before authentication and onboarding.
- [ ] References exist for authentication, CSRF denial, provisioning,
      activation, investigation, workspace/result access, denials, feedback,
      revocation, deactivation, and session invalidation.
- [ ] Events include actor, role, tenant, action/denial, correlation, UTC time,
      and integrity linkage required by the deployed contract.
- [ ] Provenance links synthetic input, execution path, result, tenant, and
      human/AI decision separation.
- [ ] Evidence is append-only or independently hashable and contains no
      credential, token, cookie, session, customer data, or raw payload.

## Revocation verification

- [ ] Authorization revoked with an externally recorded reason.
- [ ] Analyst deactivated.
- [ ] Active sessions invalidated.
- [ ] Login renewal fails closed after revocation.
- [ ] Workspace and investigation reads fail closed after revocation.
- [ ] Feedback/action writes fail closed after revocation.
- [ ] Remote access peer/policy disabled or narrowed.
- [ ] Safe audit, provenance, and custody references retained.

## Evidence and closeout

- [ ] Evidence class is `rehearsal`, `remote_access_preflight`, or
      `authenticated_controlled_analyst_pilot`; classes are not mixed.
- [ ] No `PASS` was inferred from configuration, health, readiness, rehearsal,
      or an unobserved response.
- [ ] Access record conforms to
      `GATE5_ANALYST_ACCESS_EVIDENCE.schema.json`.
- [ ] Authenticated pilot record conforms to
      `CONTROLLED_ANALYST_PILOT_EVIDENCE.schema.json`.
- [ ] Five focused validators and the full validator pass for a completed
      pilot; otherwise status remains `BLOCKED_WITH_REASON` or `NOT_MEASURED`.
- [ ] Evidence hash and external custody receipt were reviewed by the release
      authority.
- [ ] Pilot report records outcomes, limitations, metrics, issues, and
      analyst feedback without customer data.
