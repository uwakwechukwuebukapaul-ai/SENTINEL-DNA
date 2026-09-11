# Controlled Analyst Pilot Final Readiness Review

**Review date:** 2026-09-01  
**Scope:** Sentinel DNA staging controlled analyst pilot activation chain  
**Decision:** `BLOCKED_WITH_REASON`  
**Pilot execution:** Not authorized

## Executive decision

The repository implementation contains the expected trusted-browser activation
controls and fails closed when the external reviewed runtime is unavailable.
No missing repository control was identified in the reviewed activation path.
However, enterprise readiness is not established: the external reviewed
Playwright/RPC runtime and its trusted bridge are not configured in this
operator environment, the activation manifest is absent, the certified staging
origin is not reachable from this environment, and deployment evidence for
tenant isolation and audit logging is not present.

These are activation and infrastructure dependencies, not reasons to add a
fallback provider. The pilot must remain blocked until the operator supplies
the approved runtime and evidence listed below, and a human release authority
records approval.

## Review scope and evidence

The review covered:

- execution adapter: `scripts/trusted_browser_execution_adapter.mjs`;
- trusted browser facade: `scripts/trusted_browser_service/browser-client.mjs`;
- provider boundary and runtime interface:
  `scripts/trusted_browser_service/runtime-provider.mjs` and
  `scripts/trusted_browser_service/providers/playwright-runtime-provider.mjs`;
- provider verification, readiness, activation reporting, and troubleshooting;
- pilot runner gate and evidence handoff;
- staging security assertions and the operator runbook/checklist;
- Node and Python staging tests, syntax checks, and repository diff hygiene.

The latest repository-side blocked report is
[`pilot-evidence/controlled-pilot-readiness-report-20260901T000000Z.json`](../../pilot-evidence/controlled-pilot-readiness-report-20260901T000000Z.json).
It contains only non-secret statuses and safe diagnostic categories.

Static review found no credential values, cookie extraction, direct HTTP login
automation, CDP access, insecure browser launch flags, localhost origin
bypass, disabled validator, or secret-bearing diagnostic output in the
activation chain. The runner's `browserAuth` call is an external handoff of
field descriptors; credential entry and richer results remain outside the
runner boundary.

## Activation-chain assessment

| Layer | Repository assessment | Production decision |
| --- | --- | --- |
| Pilot runner | Readiness is checked before browser acquisition; incomplete or unmeasured evidence remains blocked. | Control present; authenticated pilot not authorized. |
| Execution adapter | Accepts only `codex-app`, the certified origin, the reviewed client export, and the required browser/tab surfaces. | Control present; depends on trusted service. |
| Trusted facade | Loads only an operator-configured local module, restricts origin/navigation, validates the browser contract, redacts secret-shaped results, and exposes no cookie/storage/credential APIs. | Control present; external module unavailable here. |
| Provider boundary | Accepts only `setupBrowserRuntime({ environment: "codex-app" })`, forwards no arbitrary options, and delegates transport to the external reviewed runtime. | Control present; external runtime is an activation dependency. |
| Reviewed Playwright/RPC runtime | Must be supplied by the operator and provide the approved browser RPC bridge. It is intentionally not checked into this repository. | **Blocked: external dependency not configured.** |
| Provider verification | Performs read-only contract checks and requires `browserAuth`; it does not authenticate, navigate, evaluate, or write evidence. | Control present; currently blocked by missing provider. |
| Activation manifest | Strict schema, certified-origin binding, SHA-256 integrity, operator approval reference, and image digest reconciliation are required. | **Blocked: manifest not present in this workspace.** |
| Readiness gate | Requires image identity, staging environment, provider verification, writable evidence custody, validation scripts, TLS origin reachability, secure cookies, disabled debug, pilot access, tenant isolation, and audit logging. | Control present; deployment evidence is incomplete. |
| Evidence generation | Readiness artifact is non-secret and exclusive-create; pilot evidence remains separate and must pass the unchanged validator. | Control present; no incomplete evidence may authorize execution. |
| Human authority | Runbook requires human review of gate results, hashes, tenant-scoped audit/provenance, revocation, and remaining review items. | **Pending operator/security sign-off.** |

## Production controls verified

The following controls are implemented in the reviewed repository path:

- certified origin is exact and HTTPS-only:
  `https://sentinel-dna-staging:18443`;
- the environment is fixed to `codex-app`;
- runtime/provider/client exports are checked before use;
- missing, invalid, or untrusted provider modules produce allowlisted `TB_*`
  categories and no upstream paths or stack traces;
- browser selection and browser/tab/Playwright/DOM contracts are validated;
- `browserAuth` is mandatory and is never replaced with a credential argument,
  cookie, token, direct HTTP login, or automatic login;
- provider options are rejected when they contain secret-shaped fields;
- DOM/evaluation results and readiness reports redact secret-shaped fields;
- there is no direct CDP access, browser-debugging-port use, insecure launch,
  localhost-origin exception, or alternate browser fallback;
- the activation gate runs before `createApprovedBrowser()` and before pilot
  evidence generation;
- manifest integrity and image digest binding are checked;
- readiness artifacts use exclusive creation and cannot overwrite a prior
  report;
- missing external runtime, invalid contract, missing capability, invalid
  origin, missing manifest, image mismatch, unavailable origin, unavailable
  evidence directory, and missing security assertions remain blockers;
- the pilot runner preserves tenant-scope, denial, audit/provenance,
  advisory-only AI, revocation, and human-approval gates for the authenticated
  execution phase.

## Current blockers and external-dependency determination

The following blockers were observed or are not evidenced in the current
operator environment:

| Safe code/status | Blocker | Why it is external | Required evidence |
| --- | --- | --- | --- |
| `TB_PROVIDER_NOT_CONFIGURED` | Reviewed client/runtime variables are not configured for an operator runtime. | The transport is intentionally owned by the operator environment. | Non-secret configuration check from the approved host. |
| `TB_PROVIDER_MODULE_MISSING` | External reviewed Playwright/RPC runtime module is not available/configured. | The repository must not ship or synthesize the reviewed runtime. | Approved module installation, provenance, and provider verification. |
| `TB_PROVIDER_MANIFEST_MISSING` | Activation manifest is absent. | Manifest approval and custody belong to the deployment/security process. | Valid manifest with SHA-256 binding, image digest, origin, timestamp, and approval reference. |
| `TB_ORIGIN_UNREACHABLE` | Certified staging origin is not reachable from this environment. | DNS, private edge, TLS trust, and staging deployment are external runtime conditions. | Successful authenticated-environment reachability check and certificate review. |
| `TB_SECURITY_CONTROL_MISSING` | Tenant-isolation/audit/security assertions are not all present in the current shell/deployment evidence. | These are deployment configuration and service-observability responsibilities. | Deployment evidence proving secure cookies, debug-off, pilot gate, tenant isolation, and audit logging. |
| `BLOCKED_WITH_REASON` | Human release approval and customer pilot prerequisites are not recorded. | Authorization and scope approval are organizational controls. | Signed/referenced approval, scope, revocation owner, and custody plan. |

No blocker justifies a repository fallback, a test fixture in production, a
credential shortcut, or a relaxed validator. If any required evidence cannot
be produced, retain `BLOCKED_WITH_REASON`.

## Remaining operational requirements

An operator must complete these steps in the approved private staging
environment:

1. Install or make available the separately reviewed Playwright/RPC runtime
   from the approved distribution, with its immutable provenance recorded.
2. Register the checked-in trusted browser facade and provider boundary. Point
   `SENTINEL_DNA_TRUSTED_BROWSER_CLIENT` and
   `SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT` to those reviewed modules;
   point `SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME` only to the reviewed
   external runtime module. Never point it to a test fixture, standalone
   Playwright install, CDP endpoint, or HTTP client.
3. Create the non-secret activation manifest outside source control. Include
   the approved provider identity, runtime module identity, image/runtime
   digest, exact certified origin, UTC activation timestamp, operator approval
   reference, and the required SHA-256 integrity value.
4. Set `SENTINEL_DNA_IMAGE_DIGEST` to the immutable deployed staging image
   digest and reconcile it with the manifest. A mismatch blocks activation.
5. Verify private DNS, TLS trust, and reachability of the exact certified
   origin. Do not broaden the origin or publish a wildcard/public listener.
6. Prove deployment controls: secure cookies enabled, debug disabled, pilot
   access gate enabled, tenant isolation enabled and tested, and audit logging
   enabled and observable.
7. Validate the append-only evidence directory and evidence custody owner.
8. Run provider verification, the activation gate, and the troubleshooting
   report if needed. Preserve the machine-readable report as non-secret
   activation evidence.
9. Obtain human security/release approval before any authenticated pilot
   session. Keep provisioning disabled unless separately approved.

## Customer pilot prerequisites

Before customer participation, the release authority must confirm:

- written customer scope, pilot dates, named tenant, named analyst(s), and
  named security/incident owner;
- synthetic or explicitly approved pilot data only; no unapproved customer or
  production data;
- private HTTPS access through the approved edge/VPN/zero-trust path, with no
  public listener or public DNS exposure;
- identity, RBAC, tenant scope, and least-privilege review for every pilot
  participant;
- external `browserAuth` availability and an operator-controlled credential
  handoff; no credential material in source, environment reports, logs, or
  evidence;
- verified cross-tenant denial and denial of administrative, database,
  shell/container, destructive, and production-impact actions;
- audit and provenance records that are tenant-scoped, immutable/custodied,
  and reviewable by the customer and internal security team;
- evidence retention, access control, hash verification, and export/custody
  procedure;
- human approval for analyst decisions and explicit AI-advisory-only scope;
- session revocation, analyst deactivation, rollback, and incident response
  procedures tested before customer access;
- a documented stop condition: any missing, stale, unverifiable, or
  contradictory prerequisite returns `BLOCKED_WITH_REASON` and prevents
  execution.

## Security sign-off checklist

The release authority should mark each item only from direct evidence:

- [ ] Execution adapter -> trusted facade -> provider boundary -> reviewed
      external Playwright/RPC runtime chain is intact.
- [ ] External runtime provenance and security review are recorded.
- [ ] Provider exports `setupBrowserRuntime` and accepts only `codex-app`.
- [ ] Runtime returns the approved browser contract and external
      `browserAuth` capability.
- [ ] No credentials, cookies, tokens, sessions, or private keys are stored
      in the repository, manifest, logs, or evidence.
- [ ] No direct HTTP authentication, CDP access, insecure launch, or test
      provider fallback is configured.
- [ ] Activation manifest schema, provider identity, runtime identity, exact
      origin, approval reference, and SHA-256 integrity are valid.
- [ ] Manifest image/runtime digest exactly matches the deployed immutable
      staging image digest.
- [ ] Certified staging origin and TLS trust are verified from the operator
      environment.
- [ ] Secure cookies are enabled and debug mode is disabled.
- [ ] Pilot access gate is enabled; no public or wildcard origin is allowed.
- [ ] Tenant isolation is enabled and cross-tenant denial evidence is
      available.
- [ ] Audit logging and provenance are enabled, tenant-scoped, and reviewable.
- [ ] Evidence directory is writable by the approved process, append-only by
      procedure, access-controlled, and has a custody owner.
- [ ] Provider, readiness, activation, adapter, and Python staging security
      tests pass in the release candidate.
- [ ] Readiness and activation commands return `READY_FOR_ANALYST_PILOT`.
- [ ] Human security/release authority has reviewed the report and approved
      the bounded pilot scope.
- [ ] Revocation, rollback, evidence preservation, and incident contacts are
      documented and tested.

## Operator commands

Run from the approved operator environment. These commands do not print
secrets; they must be run in order and stop at the first blocked result.

```powershell
.\deployment\staging\scripts\configure_trusted_browser_provider.ps1 -DryRun
node .\deployment\staging\scripts\verify_trusted_browser_provider.mjs
node .\deployment\staging\scripts\generate_trusted_browser_readiness_report.mjs
node .\deployment\staging\scripts\generate_trusted_browser_activation_troubleshooting_report.mjs
.\deployment\staging\scripts\check_controlled_pilot_activation.ps1 -Json -DryRun
```

Only after the JSON decision is `READY_FOR_ANALYST_PILOT` and the human
approval gate is complete may the operator run the normal activation command:

```powershell
.\deployment\staging\scripts\check_controlled_pilot_activation.ps1
```

That command's normal mode writes the non-secret readiness report. It does not
authenticate, create an account, create an analyst session, or authorize the
pilot by itself. The controlled analyst pilot runner remains separately gated
and must produce complete, validator-approved evidence.

## Final readiness conclusion

**Repository control status:** Ready for external operator activation review.  
**Enterprise pilot status:** `BLOCKED_WITH_REASON`.  
**Reason:** External reviewed Playwright/RPC runtime, trusted bridge, valid
activation manifest, certified staging reachability, deployment security
evidence, and human release approval are not available in this workspace.  
**Authorization:** Do not execute the controlled analyst pilot or issue an
analyst endpoint until every checklist item is evidenced and the final human
decision is recorded.

