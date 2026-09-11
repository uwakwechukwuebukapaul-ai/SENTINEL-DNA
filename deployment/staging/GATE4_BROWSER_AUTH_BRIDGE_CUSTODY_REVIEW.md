# Gate 4 browserAuth bridge external-custody review

Review scope: the operator-supplied browser-authentication bridge selected by
`SENTINEL_DNA_BROWSER_AUTH_BRIDGE`.

Decision for this workspace: `BLOCKED_WITH_REASON`. This review defines the
acceptance and promotion requirements; it does not supply or implement a
bridge, runtime, fixture, credential path, or fail-open alternative.

## 1. Operator acceptance checklist

### External custody intake

- [ ] The bridge is supplied by the approved custody/distribution owner and is
      outside the repository checkout.
- [ ] The exact bridge file received by the operator is hashed with SHA-256;
      the digest is recorded in the custody record and reconciled independently.
- [ ] The custody record identifies the bridge, version/release, source,
      reviewer, review date, security-review reference, intended environment,
      certified origin, owner, incident contact, and revocation/teardown owner.
- [ ] The artifact is immutable or otherwise protected against replacement
      between review, hashing, configuration, and execution.
- [ ] The bridge is not a test, fixture, mock, stub, fake, simulation, inline
      test capability, or repository-local substitute.
- [ ] No credentials, cookies, tokens, session state, signing keys, or
      authentication responses are included in custody evidence.

### Structural acceptance

- [ ] `SENTINEL_DNA_BROWSER_AUTH_BRIDGE` is a non-secret path to the approved
      local module; it is not a URL, endpoint, package fallback, or credential.
- [ ] The path resolves to an existing plain local file with no query or
      fragment and is not under a rejected test/fixture/mock/stub/fake path.
- [ ] The module imports without import-time authentication, browser launch,
      direct network login, secret reads, or other unreviewed side effects.
- [ ] The read-only harness returns `{"status":"PASS","checks":{"bridge":"PASS"}}`:

      `node .\\deployment\\staging\\scripts\\validate_trusted_browser_auth_bridge.mjs`

- [ ] The operator records that the harness only imports and checks the export;
      it never invokes `requestBrowserAuth()` and is not proof of custody or
      behavioral approval.

### Contract and operational acceptance

- [ ] The bridge exports callable `requestBrowserAuth` with the interface in
      section 2 and accepts only `environment: "codex-app"`.
- [ ] Credential entry occurs only through the approved browser UI/page. The
      bridge receives no password, token, cookie, header, CSRF value, session
      value, or credential object from Sentinel DNA.
- [ ] The bridge targets only the certified origin
      `https://sentinel-dna-staging:18443` and the supplied visible selectors.
- [ ] The bridge returns only a non-secret string status; successful handoff
      returns `status: "submitted"`.
- [ ] Bridge load, execution, timeout, malformed result, and teardown behavior
      are covered by the external security review and remain fail-closed.
- [ ] The bridge has no direct HTTP login, CDP/debugging-port, arbitrary-origin,
      cookie/storage extraction, secret logging, or session-persistence path.
- [ ] Bridge owner confirms lifecycle, revocation, incident response, and
      removal/replacement procedure.

## 2. Bridge interface specification

The required module contract is:

```js
export async function requestBrowserAuth({ page, request, environment }) {
  // Credential entry remains in the approved browser-mediated custody path.
  return { status: "submitted" };
}
```

`environment` is exactly `"codex-app"`.

`request` is the only Sentinel DNA request payload and is limited to:

```js
{
  origin: "https://sentinel-dna-staging:18443",
  fields: [
    {
      id: "username",
      label: "Email or username",
      type: "text",
      selector: "#username",
      autocomplete: "username", // optional
      required: true              // optional
    },
    {
      id: "password",
      label: "Password",
      type: "password",
      selector: "#password",
      autocomplete: "current-password",
      required: true
    }
  ],
  submit: {                         // optional
    selector: "#login-form button[type='submit']",
    action: "click"
  }
}
```

Required request rules:

- `origin` must equal the certified origin exactly.
- `fields` must be a non-empty array. Every field must contain string `id`,
  `label`, `type`, and non-empty string `selector`.
- `submit`, when present, must contain a non-empty string `selector`.
- Credential-shaped fields and values are rejected before the bridge is called.

`page` is the operator/runtime-owned approved browser page. It is not a
serializable evidence value and must not be returned, logged, persisted, or
passed to another unapproved transport. The bridge may use it for the reviewed
browser-mediated UI handoff only.

The only accepted result is an object with a non-secret string `status`.
`{ status: "submitted" }` is required for the runner to continue. The bridge
must never return passwords, tokens, cookies, headers, CSRF values, session
values, page data, or richer authentication results.

Read-only provider verification may discover the `browserAuth` capability but
must not call it. A missing or invalid bridge remains a blocker:

| Condition | Required safe result |
| --- | --- |
| Missing/unresolvable configured bridge | `TB_AUTH_BRIDGE_MISSING` |
| No callable `requestBrowserAuth` export | `TB_AUTH_BRIDGE_EXPORT_INVALID` |
| Import, execution, malformed-result, or bridge handoff failure | `TB_AUTH_BRIDGE_RUNTIME_FAILED` |
| Timeout | `TB_AUTH_BRIDGE_TIMEOUT` |

## 3. Security review checklist

- [ ] Source, dependency tree, release provenance, and exact SHA-256 digest
      were reviewed by an independent security/release reviewer.
- [ ] Import-time behavior is side-effect limited; importing the bridge does
      not authenticate, launch an alternate browser, read credentials, or
      expose secrets.
- [ ] Credential values originate only in the approved external custody/UI
      flow and never in Sentinel DNA arguments, environment reports, logs,
      diagnostics, provider options, or evidence.
- [ ] The bridge uses only the supplied approved page and selectors; no direct
      HTTP authentication, CDP, debugging port, arbitrary RPC endpoint,
      localhost exception, or alternate origin exists.
- [ ] Origin, navigation, selector, and submit handling are constrained to the
      reviewed certified staging flow.
- [ ] Return values are reduced to `{ status }`; exceptions are mapped to safe
      `TB_*` categories without paths, stack traces, environment values, or
      upstream error text.
- [ ] Timeouts, cancellation, duplicate requests, partial login, browser/page
      close, and runtime teardown have bounded and fail-closed behavior.
- [ ] No cookies, storage, authorization headers, CSRF values, tokens, session
      identifiers, or credential material are extracted or persisted.
- [ ] Least-privilege filesystem, network, process, and module permissions are
      documented and verified on the approved operator host.
- [ ] Replacement, revocation, incident handling, and evidence-retention
      procedures are tested or independently witnessed.
- [ ] No production data, customer credentials, public endpoint, or analyst
      access is in scope for bridge acceptance.

## 4. Evidence required before enabling `SENTINEL_DNA_BROWSER_AUTH_BRIDGE`

The following non-secret artifacts must exist in approved custody before the
environment variable is enabled as an activation input for a Gate 4 attempt.
A quarantined read-only validation shell may set the variable solely to run
the structural harness; that temporary check does not constitute activation,
custody approval, or pilot authorization:

1. **Bridge custody record** — bridge identity/version, supplier or source,
   exact SHA-256 digest, custody owner, approved host/scope, reviewer/date,
   security-review reference, incident contact, and revocation owner.
2. **Bridge-to-approval binding** — an approval record or manifest entry that
   binds the exact bridge digest to `codex-app`, the certified origin, the
   reviewed provider/runtime identities, the immutable image digest, and the
   operator/run scope. A bridge digest that is merely recorded in prose is
   insufficient.
3. **Integrity/signature evidence** — validated canonical integrity and, where
   required by custody, detached-signature metadata. Signing keys remain
   outside the repository and runtime inputs.
4. **Structural acceptance output** — the read-only harness result is `PASS`,
   with the command, UTC time, reviewed checkout identity, and safe result
   retained. The harness result alone is not approval.
5. **Static security review record** — confirmation of the section 3 controls,
   including no direct login transport, secret persistence, debug endpoint,
   test substitute, or import-time side effect.
6. **Host control evidence** — approved host identity, file ownership and
   permissions, module immutability/replacement control, and confirmation that
   the configured path is outside the repository and test topology.
7. **Change/revocation record** — named owner and procedure for removing or
   replacing the bridge; any digest, code, runtime, origin, or scope change
   invalidates the approval and requires a new review.

### Important current-state finding

The current activation-manifest schema binds provider identity, runtime
identity/digest, image digest, origin, timestamp, and operator approval, but it
does not contain a browser-auth bridge identity or digest. Therefore, the
existing manifest and `verify_gate4_external_artifacts.mjs` output must not be
treated as sufficient bridge custody evidence. Gate 4 must require either an
approved manifest revision that cryptographically binds the bridge or a
separately integrity-checked custody attestation that is part of the release
approval set. This is a promotion requirement, not a request to add a bridge
or weaken the current fail-closed code.

## 5. Final Gate 4 promotion criteria

Promote only when every criterion is `PASS` and independently attributable to
the same reviewed artifact set, host, image, origin, and release attempt:

- [ ] Bridge custody, digest, approval, integrity/signature, owner, and
      revocation evidence are complete and current.
- [ ] Bridge digest is cryptographically bound to the activation approval set;
      runtime and image digests also reconcile exactly.
- [ ] Provider verification returns exactly `{"status":"PASS"}` and every
      check (`provider`, `runtime`, `origin`, `browser_contract`,
      `browser_auth`) is `PASS`. Verification has not invoked authentication.
- [ ] External artifact verification passes; no repository-local runtime,
      manifest, bridge, fixture, mock, or simulation is used as custody.
- [ ] Certified-origin private TLS reachability is proven for exactly
      `https://sentinel-dna-staging:18443`.
- [ ] Readiness returns `READY_FOR_ANALYST_PILOT`; activation returns exactly
      `{"status":"READY_FOR_ANALYST_PILOT","codes":[]}`.
- [ ] Secure cookies, debug-off, pilot access gating, tenant isolation, audit
      logging, evidence custody, and private deployment controls are proven by
      deployment evidence, not environment flags alone.
- [ ] After human release approval, the bounded pilot proves the submitted
      browser-mediated handoff, manager/session checks, RBAC and tenant-scope
      denial, CSRF protection, audit/provenance, advisory-only AI, and all
      destructive/admin/database/shell/production-impact denials.
- [ ] Pilot evidence is validator-approved, append-only, hash-reconciled, and
      contains no credentials, cookies, tokens, sessions, customer data, or
      raw upstream exceptions.
- [ ] Teardown, revocation, post-revocation denial, incident contacts, and
      rollback evidence are complete.
- [ ] Named security/release authority records final approval for the bounded
      analyst scope. Any missing, stale, contradictory, unverifiable, or
      changed prerequisite keeps Gate 4 `BLOCKED_WITH_REASON`.

### Current decision

Do not enable the bridge for promotion and do not release analyst access from
this workspace. The recorded state remains blocked by absent/insufficient
external bridge custody, activation custody reconciliation, and live staging
prerequisites.

## Repository basis

- `deployment/staging/TRUSTED_BROWSER_PROVIDER_CONFIGURATION.md`
- `deployment/staging/scripts/validate_trusted_browser_auth_bridge.mjs`
- `deployment/staging/scripts/trusted_browser_service/providers/approved-playwright-runtime.mjs`
- `deployment/staging/scripts/trusted_browser_service/browser-client.mjs`
- `deployment/staging/scripts/verify_trusted_browser_provider.mjs`
- `deployment/staging/scripts/verify_gate4_external_artifacts.mjs`
- `deployment/staging/GATE4_EXTERNAL_ARTIFACT_ONBOARDING_CHECKLIST.md`
- `deployment/staging/GATE4_OPERATOR_RUNBOOK.md`
- `deployment/staging/GATE4_EXTERNAL_DEPENDENCY_CLOSURE_EVIDENCE_2026-09-02.md`
