# Sentinel DNA Gate 5 Final Acceptance Report

Date: 2026-09-03  
Branch: `gate4-controlled-analyst-pilot`  
Candidate commit: `211f16ed57d71c21a8b16fbc367d72597e6fc4e9`  
Worktree: **dirty**; the candidate includes uncommitted MFA, onboarding, display-label,
and documentation changes.  
Evidence rule: only directly observed results are `PASS`; unavailable or unperformed
checks remain `NOT_MEASURED`, `BLOCKED`, or `REQUIRES HUMAN VALIDATION`.

## 1A. Exact state snapshot

| Field | Observed value |
| --- | --- |
| Branch | `gate4-controlled-analyst-pilot` |
| HEAD SHA | `211f16ed57d71c21a8b16fbc367d72597e6fc4e9` |
| HEAD tree SHA | `9da5fe427bb2fe7f6728fafc253e9eb88a4a4480` |
| Remote branch SHA | `c34a0707d2ef7a51e2cf9d90ccc933adaec300dd` |
| Merge base | `c34a0707d2ef7a51e2cf9d90ccc933adaec300dd` |
| Local-only commits | `11` |
| Remote-only commits | `0` |
| Tracked modified files | `33` |
| Untracked files | `9` |

The remote SHA was verified with a read-only `git ls-remote` query. The deployed
staging runtime identity was not observable because Docker is unavailable; only
the repository Compose identity contract was verified.

## 1B. Candidate and runtime custody

| Identity | Status | Evidence / disposition |
| --- | --- | --- |
| Candidate Git SHA/tree | PASS | `211f16ed57d71c21a8b16fbc367d72597e6fc4e9` / `9da5fe427bb2fe7f6728fafc253e9eb88a4a4480` |
| Expected candidate image tag | NOT ESTABLISHED | `ghcr.io/uwakwechukwuebukpaul-ai/sentinel-dna:sha-211f16ed57d71c21a8b16fbc367d72597e6fc4e9`; read-only Actions lookup returned no usable candidate run data and an anonymous GHCR manifest probe returned `401 Unauthorized` |
| Candidate immutable digest/image ID | NOT ESTABLISHED | No candidate image artifact was available locally or independently observed |
| Candidate OCI revision/source | NOT ESTABLISHED | No candidate image was available from which to verify OCI labels |
| Candidate release manifest/provenance/attestation | NOT ESTABLISHED | The protected manual-dispatch workflow requires clean checkout, protected release inputs/secrets, Docker, and GHCR publication; no candidate-bound manifest or attestation was observed |
| Current staging runtime | NOT CANDIDATE | Recorded running revision is `c34a0707d2ef7a51e2cf9d90ccc933adaec300dd`; Docker is unavailable for independent inspection |
| Historical local image evidence | RETAINED / NOT CANDIDATE | Existing image evidence identifies revision `626eed8ecc83b67b90d8baf04112d1e05a685196`; it is not relabeled as candidate evidence |

The corrected canonical GitHub repository `uwakwechukwuebukapaul-ai/SENTINEL-DNA`
resolves, but its commit API returns `422 No commit found` for the candidate SHA;
the exact candidate Actions query returns no runs. The remote
`gate4-controlled-analyst-pilot` branch remains at `c34a0707d2ef7a51e2cf9d90ccc933adaec300dd`.
The repository exposes five historical `deployment-contract` runs, all failed on
unrelated `main` commits; none is candidate evidence.

The authoritative staging source Compose file contains no stale
`974e3275bc678851e3979a5cbb95ff7d2e9dc4c9` application reference. Tracked rendered
snapshots retain historical `c34a0707d2ef7a51e2cf9d90ccc933adaec300dd` and
`974e3275bc678851e3979a5cbb95ff7d2e9dc4c9` values; they were not rewritten or
promoted to candidate evidence.

## 1. Executive summary

The existing authentication, canonical authorization, tenant isolation, dashboard,
onboarding, and Tailscale architecture was preserved. The safe hardening completed in
this candidate adds backend-enforced Authenticator App/TOTP MFA, encrypted TOTP secret
storage, one-time hashed recovery codes, MFA-pending session denial, strict MFA CSRF,
MFA rate limits and audit events. `SOC-L1 Analyst` is a display/business label only;
the canonical authorization role remains `analyst`.

Local automated security coverage is green, but Gate 5 cannot be accepted from this
workstation. No approved S10 end-to-end run, live staging authentication, reconciled
trusted-browser custody, mobile acceptance, production provider validation, human
verification, fresh authoritative staging backup, or isolated restored application
run was observed.

## 2. Final status

**BLOCKED**

This status is supported by the existing Gate 4 external-dependency record,
unavailable local Tailscale/Docker tooling, unavailable in-app browser, missing live
trusted-browser authentication bridge, and absence of human-approved analyst pilot
evidence. No analyst account, credential, session, or pilot evidence was fabricated.

## 3. Objective and evidence matrix

| Area | Status | Evidence / disposition |
| --- | --- | --- |
| Existing architecture preservation | PASS | Focused auth/identity/security/tenant tests; no replacement auth, RBAC, tenant, workspace, or Tailscale system added |
| Canonical role | PASS | Internal role remains `analyst` in permissions, canonical memberships, pilot boundary, and API checks |
| Product label | PASS | `SOC-L1 Analyst` is presentation-only in auth public data and dashboard templates |
| Backend authentication | PASS | Existing password, email OTP, phone verification, OIDC boundaries retained; focused suites pass |
| Authenticator/TOTP implementation | PASS | RFC-compatible 30-second SHA-1 TOTP, one-step clock tolerance, secure random secret, AES-GCM envelope, server verification |
| MFA session enforcement | PASS | MFA-enabled password/email login creates `mfa_pending`; canonical context and permission boundaries reject it until verification |
| Recovery codes | PASS | 10 cryptographically random codes shown only at enrollment/regeneration, scrypt-hashed, one-time atomic consumption, regeneration invalidates prior set |
| MFA audit | PASS | Enrollment start/verification, enable, success/failure, recovery use, regeneration, and disable events contain no factor material |
| Human verification | NOT_MEASURED / REQUIRES APPROVAL | No provider or challenge was added; existing server-side rate limiting remains anti-abuse only. A private-compatible provider and privacy/accessibility review are required before implementation |
| Existing-organization onboarding | PASS | Verified-domain detection, server-controlled policy, join-request idempotency, invitation binding/replay protection, and revocation tests pass |
| Onboarding resume endpoint | PASS | `/api/auth/onboarding/resume` is server-controlled and requires active approved membership; browser acceptance remains unmeasured |
| Tailscale client and policy | BLOCKED | `tailscale` unavailable; external policy/device custody not observable locally |
| Tailscale HTTPS / S10 reachability | NOT_MEASURED / REQUIRES HUMAN VALIDATION | No approved Samsung S10 observation; MagicDNS resolution alone is insufficient |
| Nginx/private staging edge | BLOCKED | `docker` unavailable; existing Gate 4 record says live edge/TLS/ready checks blocked |
| Browser desktop acceptance | BLOCKED | In-app browser runtime reported `No browser is available`; external trusted-browser custody currently fails certified-origin selection |
| Browser mobile acceptance | NOT_MEASURED / REQUIRES HUMAN VALIDATION | No supported mobile browser/device session available |
| Signup/email/phone | PASS (automated only) | Existing and new auth tests cover server-side verification; real provider/device acceptance is not measured |
| Login/logout/session expiration | PASS (automated only) | Existing session/revocation tests pass; live analyst run is not measured |
| Profile/workspace/dashboard | PASS (contract only) | Server-side route tests pass; live remote analyst access is not measured |
| Investigation/evidence/reports/actions/notes | PASS (contract only) | Existing focused route and authorization tests pass; approved synthetic analyst workflow is not measured |
| RBAC and tenant isolation | PASS (automated only) | Canonical context, role-tampering, and tenant-boundary tests pass; live pilot denial matrix is not measured |
| Revocation | PASS (automated only) | Membership revocation invalidates sessions and canonical authority access in focused tests |
| Fresh staging backup/checksum | NOT_MEASURED | No authoritative staging database or fresh backup was available locally |
| Isolated restore/application startup | NOT_MEASURED | No staging backup/isolated target was available; disposable recovery tests are not staging evidence |
| Production email/SMS/OIDC configuration | NOT_MEASURED | Provider configuration is external and intentionally absent from Git |
| Human analyst/security approval | NOT_MEASURED / REQUIRES HUMAN VALIDATION | No live controlled pilot or release approval was performed |

## 4. Automated validation evidence

- `python -m pytest tests/auth/test_mfa.py -q` -> **4 passed**.
- Final focused regression: `python -m pytest tests/auth/test_mfa.py tests/identity/test_organization_membership.py tests/dashboard/test_auth_experience.py tests/security/test_permissions.py tests/security/test_logout_navigation.py -q` -> **28 passed**.
- `python -m pytest tests/auth tests/identity tests/security tests/tenant -q` ->
  **228 passed, 4 skipped**. Skips are expected POSIX filesystem-semantic checks on
  Windows.
- `python -m pytest tests/deployment/test_sqlite_backup.py tests/deployment/test_deployment_contract_validation.py tests/staging/test_staging_tls_validation.py tests/staging/test_staging_security_contract.py tests/staging/test_staging_persistence_contract.py tests/staging/test_favp_staging_initialization.py tests/staging/test_favp_launch_contract.py -q` -> **49 passed**.
- `git diff --check` -> **PASS**.
- Completed post-correction repository-wide Python regression:
  `python -m pytest -q` -> **3,211 passed, 8 skipped in 1129.52s (0:18:49)**.
  The skips are four
  expected Windows/POSIX filesystem-semantic checks, two explicitly unconfigured
  disposable-PostgreSQL integration checks, and two POSIX deployment-mode checks.
- Post-correction affected UX/security tests -> **23 passed in 23.43s**.
- Independent post-correction MFA, organization, authorization, tenant,
  investigation, evidence, and intelligence matrix -> **141 passed in 22.65s**.
- An earlier repository-wide Python attempt was interrupted at 13% during the
  environment-heavy run. It was superseded by the completed full regression above;
  the earlier interruption is retained only as historical context.
- The isolated trusted-browser bridge harness -> **4 passed**. The current full Node
  staging run has one exact failure: `verifies the external custody provider with
  the operator browserAuth bridge`; it returned `TB_BROWSER_SELECTION_FAILED` at
  certified-origin selection and then teardown stalled. The configured external
  custody runtime accepts `https://sentinel-dna-staging:18443`, while the reviewed
  facade requests the certified origin `https://uwakwe-desktop.taile388cc.ts.net`.
  This is an external custody/configuration reconciliation defect, not an
  application authorization defect, and the Node run is not reported as a pass.

## 4A. Compose application-image identity

The authoritative staging Compose file now binds `app`, `migration`, and
`favp-volume-init` to the same candidate-bound reference:
`staging-app:${SENTINEL_DNA_IMAGE_TAG:?set SENTINEL_DNA_IMAGE_TAG}`. The FAVP
initializer remains a non-networked volume-permission helper, but it uses the
same Sentinel DNA application image and cannot silently run from a historical
application revision. A staging contract test rejects recurrence of the former
`974e3275...` pin.

This is a Compose-level engineering correction only. Clean release preparation
must still establish the reviewed commit/tree, GitHub Actions run, GHCR image,
immutable digest, OCI provenance, release manifest, and reconciled staging
runtime identity. None of those custody claims are made here.

## 4B. Readiness distinctions

The only concrete analyst-surface defect found was that the report command palette
advertised export without an export action or route. It was corrected with the
authenticated, tenant-scoped JSON report endpoint and visible detail/report links;
the affected tests pass. No authentication, MFA, organization, tenant, object
authorization, evidence, report, or session-security defect was found.

| Readiness layer | Status | Evidence / limitation |
| --- | --- | --- |
| UX/UI engineering readiness | COMPLETE (automated/inspection) | The canonical protected browser surface was reviewed across login/MFA, organization context, dashboard, case/investigation queue, investigation detail, evidence/provenance, relationships, timeline, IOC intelligence, ATT&CK, confidence/uncertainty, advisory AI, analyst feedback/actions, report, export links, audit context, logout, and explicit empty/error/unavailable states. Focused dashboard/security/workspace/report tests pass. |
| Application readiness | COMPLETE (local automated) | The post-correction full Python regression is 3,211 passed with 8 documented environment/configuration skips; the affected export/security suite is 23 passed and the independent investigation/security matrix is 141 passed. |
| Human analyst testing readiness | NOT_READY | The pack is prepared at `deployment/staging/GATE5_CONTROLLED_ANALYST_TEST_PACK.md`, but no approved human run, browser acceptance, mobile acceptance, or real analyst evidence exists. |
| Release custody | NOT_ESTABLISHED | The worktree is dirty; image digest, runtime digest, manifest, approvals, and external custody are not established by this task. |
| Staging runtime reconciliation | NOT_MEASURED | Docker is unavailable locally; the Compose contract is verified, but deployed runtime identity and health are not observable. |
| Formal Gate 5 acceptance | BLOCKED | Tailscale/private edge, trusted-browser custody, mobile/browser, backup/restore, provider, and human approval evidence remain independent requirements. |

The human execution procedure and per-scenario capture template are in
`deployment/staging/GATE5_CONTROLLED_ANALYST_TEST_PACK.md`. Its entries remain
`NOT_EXECUTED` and must not be promoted to pilot evidence without an approved
external run.

## 5. MFA security evidence

The implementation is additive to `AuthService` and uses the configured application
secret only as key material for an HKDF-derived AES-GCM key. The database stores only
the encrypted TOTP secret. The provisioning URI is returned only during pending setup;
the secret is not returned by normal user/session responses. Recovery codes are stored
as password hashes and are never logged. MFA state is server-owned and is not read from
frontend flags, local storage, or client-selected roles/tenants.

The automated tests directly cover valid and invalid TOTP, clock-window rejection,
missing CSRF, MFA-pending dashboard denial, enrollment activation only after valid
TOTP, recovery-code single use, password-plus-factor disable, and role-label behavior.
Live authenticator application scanning and device acceptance remain
`NOT_MEASURED / REQUIRES HUMAN VALIDATION`.

## 6. Tailscale and HTTPS evidence

The selected architecture remains Tailscale private overlay -> raw TCP Serve ->
`127.0.0.1:18443` -> existing HTTPS edge. Cloudflare remains paused reference material
and was not introduced as a deployment requirement.

On this workstation, `tailscale` and `docker` were unavailable. The configured
MagicDNS name resolved to `100.121.164.69`, and the local `127.0.0.1:18443` probe was
reachable, but neither result proves the approved staging node, Serve configuration,
certificate chain, SNI, Nginx route, or Samsung S10 path. Therefore S10, CA-verified
remote HTTPS, `/health`, `/ready`, private surface isolation, and authenticated remote
access are not measured here.

Existing evidence in
`deployment/staging/GATE4_EXTERNAL_DEPENDENCY_CLOSURE_EVIDENCE_2026-09-02.md` records
the external trusted-browser bridge/custody reconciliation and live staging
dependencies as blocked. That evidence is retained; it is not relabeled as a Gate 5
pass.

## 7. Recovery evidence

The repository’s disposable SQLite backup/restore contract tests pass. This proves the
local recovery validator behavior only. It does not prove a fresh staging backup,
cryptographic checksum custody, isolated restore of the authoritative staging state,
restored app startup, or restored `/ready`. Those items remain `NOT_MEASURED` until an
approved staging operator executes the sequence without overwriting the source.

## 8. Required human validation before status can change

An approved operator and security/release reviewer must, using a clean reviewed
checkout and external custody:

1. Reconcile the candidate commit, image, TLS material, Tailscale policy, Serve state,
   trusted-browser runtime/bridge, and external approvals.
2. Create and checksum a fresh staging backup, restore it into an isolated target, and
   verify tenant, membership, audit, investigation, evidence, provenance, startup, and
   readiness integrity.
3. Validate the exact Tailscale origin and CA/SNI from the approved Samsung S10;
   verify only the approved application surface is reachable.
4. Complete one manager and one analyst flow for one synthetic tenant, including
   server-side onboarding/membership, profile/workspace readiness, investigation,
   evidence, report, notes/action, audit/provenance, RBAC denials, tenant isolation,
   logout, expiry, and revocation.
5. Enroll and use an authenticator app if application MFA is required by policy; record
   only opaque references and safe outcomes. Do not place QR/provisioning values,
   recovery codes, passwords, cookies, or sessions in evidence.
6. Obtain explicit human security/release approval and run the unchanged Gate 5
   validators against append-only, secret-free external evidence.

## 9. Security exceptions

No security exception was granted. No public network exposure, Cloudflare route,
public DNS, duplicate RBAC role, duplicate identity system, duplicate tenant/workspace
system, or frontend-authoritative security state was introduced.

The absence of a human-verification provider is an open control decision, not an
exception or a bypass. Existing rate limits do not constitute proof of human identity.

## 10. Final security review

| Control | Result |
| --- | --- |
| `analyst` remains canonical RBAC role; `SOC-L1 Analyst` display-only | PASS |
| Backend-authoritative authentication and MFA | PASS (automated) |
| MFA-pending protected-resource denial | PASS (automated) |
| TOTP/recovery secret protection and MFA audit | PASS (automated) |
| Human verification server enforcement/replay resistance | NOT_MEASURED; no provider approved |
| Organization membership, invitation, onboarding, and revocation server-controlled | PASS (automated) |
| Tenant/workspace/investigation/evidence/report authorization | PASS (automated/contract) |
| Pending/suspended/revoked denial | PASS (automated) |
| Tailscale private path and no public ports | BLOCKED / NOT_MEASURED live |
| Desktop/mobile browser acceptance | NOT_MEASURED |
| Fresh backup/checksum/isolated restore | NOT_MEASURED |
| Human analyst and release validation | NOT_MEASURED |
| Unsupported readiness claim avoided | PASS |

**Gate 5 final status: `BLOCKED`.**
