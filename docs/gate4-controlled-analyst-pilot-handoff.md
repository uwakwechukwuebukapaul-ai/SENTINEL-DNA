# Sentinel DNA Gate 4 Controlled Analyst Pilot Handoff

## Executive summary

Controlled analyst pilot readiness achieved.

The Gate 4 readiness decision is `READY_FOR_ANALYST_PILOT`, with 13 of 13
controlled-pilot readiness checks passing. This is a controlled, non-production
pilot handoff. It is not a production-readiness decision, a production release
approval, or permission to expose a public listener.

The readiness validation source commit is
`b24d0cf5dad78f9848ed1300d48236e48092e3e9`. The certified staging origin is
`https://sentinel-dna-staging:18443`.

## Architecture components validated

- Isolated staging Docker Compose project with application, PostgreSQL, Redis,
  and Nginx edge services.
- Private edge publication limited to `127.0.0.1:18443->443/tcp`.
- Checked-in trusted-browser facade and reviewed provider boundary.
- Separately supplied operator Playwright/RPC runtime and dependency closure.
- Separately supplied browser-auth bridge for visible, browser-mediated
  credential entry.
- Read-only readiness gate before pilot execution.
- Append-only, non-secret evidence and audit references.

The pilot runner is origin-scoped, same-origin for application requests, and
does not accept credentials, cookies, CSRF values, tokens, or session state as
runner inputs.

## Trusted browser provider custody model

The repository contains only the reviewed facade and provider boundary. The
runtime bundle, its exact dependency closure, activation manifest, and
browser-auth bridge remain in approved external custody. The operator
environment supplies their non-secret references and independently verified
digests. No runtime bundle, private key, credential, browser session, or
custody secret is copied into this repository.

Provider verification passed for the `codex-app` environment, the certified
origin, the browser/tab contract, and the required `browserAuth` capability.
Provider verification discovers the capability; it does not invoke it.

## Runtime integrity verification

| Artifact | Identity or digest | Result |
| --- | --- | --- |
| Reviewed runtime module | `sha256:42530c78b4d15f591d090d4da71ee2485dd20247104fdb2464705879a071831b` | PASS |
| Runtime dependency lockfile | `sha256:bfe418c7e4c3ae90aed3b0637584b4a995f7a1f3ae3e2d3833d9fb936b4f3529` | PASS |
| Browser-auth bridge | `sentinel-dna-browser-auth-bridge:1.0.0`; `sha256:6419e45dd2256cde8e0b982e6137b951cb9ff63c78577a31fb35e2782d656498` | PASS |
| Staging image | `sha256:0ce1ef605201f5f8e2d5b47c0bffae3eaa13da68952a14229faf2c97477bacec` | PASS |
| Activation manifest | External custody; integrity and bindings verified | PASS |

The manifest binds the runtime, dependency closure, browser-auth bridge,
image, and exact certified origin. The checked-in manifest under
`pilot-evidence/gate4/` remains a validation fixture and is not an activation
authority.

## Browser auth bridge verification

The bridge export and digest were verified through the approved custody path.
The bridge is restricted to the certified origin and reviewed field/submit
descriptors. Credential entry remains in the approved browser service; no
credential material is passed through Sentinel DNA orchestration or written to
evidence.

## Security controls validated

The readiness gate passed all of the following:

- secure cookies enabled;
- debug disabled;
- pilot access gate enabled;
- tenant isolation enabled;
- audit logging enabled;
- exact certified-origin TLS reachability;
- reviewed image identity and activation-manifest binding;
- provider, runtime, browser contract, and browser-auth verification;
- writable approved evidence custody and required validation scripts.

## Remaining operational responsibilities

Before authentication or account creation, the release/security operator must:

1. Reconfirm the staging Docker project, private listener, TLS SANs, and
   `/health` and `/ready` responses.
2. Confirm a current backup and a tested recovery reference for the staging
   data required by the pilot.
3. Obtain human approval for one synthetic pilot tenant and one analyst
   identity, with bounded authorization expiry.
4. Verify audit and provenance sinks from the deployed service, not only shell
   environment flags.
5. Run the procedures in
   [`GATE4_ANALYST_PILOT_RUNBOOK.md`](../deployment/staging/GATE4_ANALYST_PILOT_RUNBOOK.md).
6. Create one unique append-only pilot evidence record and run the unchanged
   manual evidence validator.

Any failed, missing, or `NOT_MEASURED` authenticated gate stops the pilot and
keeps the release blocked.

## Analyst pilot scope

The pilot is limited to approved synthetic data and the assigned synthetic
tenant. It may validate manager handoff, analyst RBAC, tenant isolation,
CSRF-protected investigation workflow, audit/provenance visibility,
advisory-only AI output, denial boundaries, and session revocation.

The pilot must not use production data, notify external parties, issue a
public URL, expose a public listener, perform destructive actions, grant admin
access, or treat an AI recommendation as a human approval.

## Rollback procedure

On a failed control, unexpected access, runtime anomaly, evidence problem, or
pilot stop condition:

1. Stop pilot activity and record only the non-secret run ID and UTC time.
2. Keep activation blocked and notify the security and release owners.
3. Revoke pilot authorization through the approved control plane.
4. Invalidate analyst sessions and verify post-revocation denial.
5. Tear down the external runtime using its reviewed lifecycle procedure.
6. Preserve only non-secret audit, incident, provenance, approval, and evidence
   hashes in approved custody.
7. Re-run the complete readiness sequence and obtain fresh human approval
   before any reactivation.

## Evidence references

- [`gate4-controlled-pilot-readiness-20260902.json`](../pilot-evidence/gate4/gate4-controlled-pilot-readiness-20260902.json)
  — deterministic readiness reference bound to `b24d0cf`.
- [`gate4-provider-verification-20260902-final.json`](../pilot-evidence/gate4/gate4-provider-verification-20260902-final.json)
  — provider, runtime, origin, browser contract, and browser-auth verification;
  evidence SHA-256 `8b10a192ab262c478399a0f23c511631162eef84bebeff06e6ff19ec0cbe573b`.
- [`gate4-external-artifact-verification-20260902T163527Z.json`](../pilot-evidence/gate4/gate4-external-artifact-verification-20260902T163527Z.json)
  — external artifact, manifest, bridge, image, and origin reconciliation;
  evidence SHA-256 `2a162a5fb5f0198ddca7033705cf0f20004c5f4049164d60edcb9517de06f778`.
- [`pilot-evidence/gate4/README.md`](../pilot-evidence/gate4/README.md) —
  custody boundary and fixture handling.
- [`CONTROLLED_ANALYST_PILOT_EXECUTION_CHECKLIST.md`](../deployment/staging/CONTROLLED_ANALYST_PILOT_EXECUTION_CHECKLIST.md)
  — authenticated gate and evidence requirements.

## Known limitations

- This handoff validates staging infrastructure and controlled-provider
  readiness; it does not prove production readiness.
- Authenticated analyst gates are executed during the pilot and must be
  evidenced independently. A healthy endpoint or passing infrastructure check
  is not sufficient evidence for those gates.
- External custody availability, revocation, backup/restore, analyst approval,
  and human release authority remain operational responsibilities.
- Historical blocked artifacts remain retained for audit history and must not
  be interpreted as the current decision.
- The requested `curl.exe -k` probe is diagnostic only; the authoritative
  readiness check retains certificate verification and uses the approved
  staging trust anchor.
