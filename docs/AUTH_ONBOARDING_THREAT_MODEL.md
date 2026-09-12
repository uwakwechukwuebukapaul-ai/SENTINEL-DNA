# Sentinel DNA Authentication and Onboarding Threat Model

Date: 2026-09-02
Status: Initial forensic model; results are engineering observations, not human pilot evidence.

| Threat | Attack vector | Existing control | New control if needed | Test | Result |
|---|---|---|---|---|---|
| Account takeover | Password guessing/stuffing | Scrypt hashing, login rate limit, generic invalid credentials, session revocation | Confirm production credential policy and telemetry | Invalid-login burst, reused password corpus in isolated test | Partially measured; targeted auth tests exist, production telemetry/provider evidence pending |
| OTP abuse | Guessing, resend abuse, provider flooding | Six-digit cryptographic code, HMAC storage, expiry, five attempts, cooldown, route rate limits, signed auth-flow binding, atomic conditional consume | Operational provider limits and concurrent execution evidence | Invalid attempts, expiry, replay, concurrent verification, resend burst | Engineering controls present; full adversarial/operational matrix needs execution |
| Session theft | Stolen cookie/remember token | HttpOnly, Secure in configured environments, SameSite=Lax, opaque persistent token hash, expiry, revocation | Confirm deployment cookie flags over real HTTPS | Inspect Set-Cookie, logout/reuse, expiry/revocation | Engineering controls present; browser/operational evidence pending |
| Session fixation | Reuse pre-auth session after login | `_login_session` clears and rebuilds the session; CSRF token rotates | Add explicit regression for pre/post session identity | Login with pre-existing session and compare auth/session state | Existing behavior appears protective; test required |
| Credential stuffing | Distributed login attempts | Per-identity/IP rate-limit service and generic errors | Validate distributed bucket policy and alerting | Simulated multi-IP/identity buckets | Partially measured |
| Account enumeration | Email/login/recovery probing | Generic recovery and email OTP responses; generic login failure | Ensure all provider failures and registration conflicts remain generic | Unknown vs known email response comparison | Good for recovery/email OTP; registration/account linking needs tests |
| Privilege escalation | Client submits admin/SOC-L1/role field | Registration route forces analyst; permissions are server-side; canonical membership controls role | Resolve canonical SOC-L1 label/role decision | Submit role/tenant/workspace tampering; direct privileged API | Existing role tampering tests; SOC-L1 decision open |
| Tenant escape | Header/payload tenant substitution | `request_context` derives session/canonical tenant and rejects conflict; coordinator scopes reads | Expand coverage to every report/evidence/IOC/note/action route | Cross-tenant reads/writes and headers | Core controls present; full matrix required |
| Workspace escape | Workspace ID substitution or guessed case/report ID | Canonical context plus tenant-scoped coordinator/report paths | Verify all legacy routes remain unreachable | Cross-workspace IDs and direct legacy endpoints | Active path protected; legacy duplicate surface requires continued exclusion |
| OAuth abuse | Forged callback, state/nonce omission, invalid claims | Google OIDC state/nonce, issuer/audience/signature/time/email_verified validation | Explicit redirect allowlist and no email-only auto-linking tests | Invalid state, nonce, subject collision, callback errors | Provider boundary exists; account-linking tests needed |
| CSRF | Cross-site state-changing auth/workspace request | Synchronizer CSRF token on browser requests, SameSite cookie, route checks | Confirm Origin/Referer policy and JSON compatibility scope | Cross-origin form/JSON requests, missing token | Existing tests; broader browser test pending |
| Replay attacks | Reuse OTP, activation, report/action request | OTP consumed state; pilot authorization expiry/revocation; session revocation | Idempotency keys and atomic state transitions where needed | OTP replay, duplicate POST, retry after timeout | OTP single-use exists; onboarding/action idempotency needs testing |
| Race conditions | Concurrent OTP verification/registration/provisioning | Database transactions and uniqueness in parts of auth/pilot schema; OTP consume is now conditional/atomic | Durable registration/provisioning idempotency and locks | Threaded concurrent requests and duplicate tabs | OTP implementation hardened; registration/provisioning race evidence not yet proven |
| Provisioning failure | User becomes authenticated before authorized workspace is ready | Existing pilot provisioning tracks pending activation; pilot boundary can fail closed; user state cannot authenticate unless `AUTHENTICATED` | Durable self-service resume/retry and no partial authorization | Inject provider/database/provisioning failures and retry | Partial protection present; self-service retry evidence remains |
| Audit integrity | Missing/forged/mis-scoped auth events | Server-side auth/pilot/audit calls with correlation/actor/tenant fields | Verify denials and transition events, prevent sensitive fields | Login/logout/denial/OTP/provisioning audit assertions | Existing event infrastructure; complete onboarding event coverage pending |

## Security invariant checklist

- Authentication and authorization remain server-authoritative.
- Tenant, workspace, and role are derived from authenticated canonical context.
- Frontend state is not accepted as verification or onboarding authority.
- Existing fail-closed pilot and provider behavior is preserved.
- Passwords, raw OTPs, secrets, session tokens, and OAuth tokens are not intended for
  logs or API responses.
- No new public access path or broad firewall surface is part of this architecture.

Any implementation that cannot preserve these invariants is blocked and must be
documented rather than merged.
