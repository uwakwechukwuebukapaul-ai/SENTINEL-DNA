# Controlled Analyst Pilot — Remaining Gates

Preparation artifact only. This checklist does not provision an account, issue
access, or authorize a pilot. All unknown values remain `NOT MEASURED` or
`NOT PROVIDED`.

## Current protected boundary

- [x] Staging edge is loopback-only: `127.0.0.1:18443 -> 443`.
- [x] HTTPS is enabled through the nginx edge.
- [x] TLS SANs cover `sentinel-dna-staging`, `127.0.0.1`, and `192.168.1.115`.
- [x] Application, PostgreSQL, and Redis have no published host ports.
- [x] `staging_internal` remains an internal Docker network.
- [x] Gate 2 release image, staging image, volumes, manifests, and evidence remain protected.
- [x] Repository security logic and release custody are unchanged.

## Runner safety disposition

The runner is browser-bound and does not accept passwords, cookies, activation
tokens, or CSRF tokens as arguments. It uses the approved secure browser
authentication handoff, relative same-origin API paths, and exclusive-create
(`wx`) evidence output. These controls are verified by source inspection and
the pilot test suite.

The following items are hard stops for the operator until the runner is
revised or independently reviewed in the execution environment:

- `allowProvisioning` must remain `false`. If provisioning is ever separately
  authorized, the supplied identity values must be independently confirmed as
  synthetic; the current runner does not enforce a synthetic email domain or
  generated identity format.
- Use only an origin that the operator has independently verified resolves to
  the loopback listener. The current hostname check accepts
  `sentinel-dna-staging:18443` but does not itself resolve or inspect the
  address. Do not run if the name resolves outside loopback or if any public
  listener is present.
- Review the response schema before treating an authenticated run as valid.
  The current redaction list covers common exact field names but is not a
  complete guarantee for alternate spellings such as `accessToken` or
  `sessionCookie`; evidence must be inspected for secret-shaped values and the
  run is blocked on any uncertainty.
- Audit and provenance endpoints must return verifiable references tied to the
  synthetic action and tenant. HTTP 200 alone is not evidence of event
  creation.

These findings do not alter application authorization logic. They mean the
runner is not approved to issue access until the hard stops are cleared and
the authenticated run produces complete evidence.

## Remaining authenticated execution checklist

The trusted browser service must be available before any authenticated item is
run. Use exactly one synthetic tenant and one analyst account during the
authorized execution. Never place passwords, activation tokens, cookies, CSRF
tokens, or private keys in evidence.

### Manager and onboarding

- [ ] Manager signs in through the visible login page using the browser's secure
      authentication handoff.
- [ ] `/api/auth/me` confirms an authorized `admin` or `soc_manager` manager.
- [ ] Missing or invalid CSRF on a manager-only write returns `403` without
      changing state.
- [ ] Exactly one synthetic pilot tenant and one analyst account are created,
      only after explicit operator approval.
- [ ] Analyst account is bound only to role `analyst`, with bounded expiry and
      active pilot authorization.
- [ ] Activation is completed through an approved protected channel; the
      activation token is never logged or written to evidence.

### Analyst authenticated gates

- [ ] Analyst login and session/cookie behavior pass.
- [ ] `/api/auth/me` derives the expected analyst identity and pilot tenant.
- [ ] Current pilot authorization is active, unexpired, and tenant-bound.
- [ ] CSRF-protected synthetic investigation action succeeds; missing CSRF is
      denied without state change.
- [ ] Analyst workspace and investigation reads are limited to the assigned
      synthetic tenant.
- [ ] An analyst request for a foreign-tenant resource is denied (`403` or
      indistinguishable `404`, according to the endpoint contract).
- [ ] Analyst-only action produces an audit reference and tenant-scoped
      provenance reference.
- [ ] Investigation workflow uses synthetic data and the canonical execution
      path; no external notification or destructive action occurs.
- [ ] Human conclusion and AI recommendation are separate fields; AI output is
      marked advisory and cannot become an enforced decision.

### Authenticated denial gates

- [ ] Analyst cannot access pilot provisioning or authorization-management
      routes.
- [ ] Analyst cannot perform admin-only actions or access manager resources.
- [ ] Analyst cannot access production resources, secrets, database controls,
      shell/SSH/container controls, or runtime management surfaces.
- [ ] Analyst cannot invoke destructive operations or unrestricted SOAR/action
      execution.
- [ ] Every denied attempt is recorded as a non-secret status/result and does
      not mutate the staging state.

### Evidence and closeout

- [ ] Evidence contains only non-secret identifiers, statuses, timestamps,
      audit/provenance references, and SHA-256 digest material.
- [ ] Evidence is written to the release evidence directory under a unique
      run-specific filename and is append-only.
- [ ] Pilot remains blocked if any authenticated gate is `NOT MEASURED`, `FAIL`,
      or `UNKNOWN`.
- [ ] On completion, manager revokes the pilot authorization, deactivates the
      analyst, invalidates sessions, and preserves the audit/provenance record.
- [ ] A private analyst endpoint is issued only after every gate is `PASS` and
      a human release authority records `READY_FOR_CONTROLLED_ANALYST_PILOT`.

## Prepared execution command

Run the browser-bound module from the trusted browser service after it becomes
available. The module intentionally requires explicit arguments for the
manager session, analyst session, tenant/resource identifiers, and any
provisioning action; it cannot invent credentials or data.

```js
var pilotRunner = await import("C:/Users/HP/Documents/sentinel-dna-postmerge-ssh/deployment/staging/scripts/controlled_analyst_pilot_runner.mjs");
await pilotRunner.runControlledAnalystPilot({
  browser,
  origin: "https://sentinel-dna-staging:18443",
  runId: "PILOT-RUN-<operator-assigned>",
  allowProvisioning: false,
  analyst: {
    expectedTenantId: "<operator-supplied-after-approved-provisioning>",
    foreignTenantResourcePath: "<operator-supplied-synthetic-resource-path>",
    auditPath: "<operator-supplied-tenant-scoped-audit-path>",
    provenancePath: "<operator-supplied-tenant-scoped-provenance-path>",
    aiVerificationPath: "<operator-supplied-investigation-result-path>",
    denialPaths: {
      deny_database: ["<known-database-control-path>"],
      deny_shell_container: ["<known-shell-or-container-control-path>"],
      deny_destructive: ["<known-destructive-action-path>"]
    }
  }
});
```

The `allowProvisioning: false` preparation invocation cannot create an
account. A later, separately authorized run may set it to `true`; the runner
still withholds the activation token from output and requires a protected
activation handoff before analyst gates can pass.

The hostname in the example is accepted by the current runner only after the
operator verifies that it resolves to `127.0.0.1` and that the live Docker
publication is exactly `127.0.0.1:18443->443/tcp`. No LAN or public address is
an acceptable browser origin for this preparation run.
