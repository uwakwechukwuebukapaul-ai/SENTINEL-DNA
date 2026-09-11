# Sentinel DNA Authentication and Onboarding Audit

Date: 2026-09-02
Branch: `gate4-controlled-analyst-pilot`

## Scope and audit qualification

This is a repository forensic audit of the existing Sentinel DNA implementation. The
repository was already a dirty working tree, including intentional Gate 5 changes and
earlier authentication/dashboard/Tailscale working-session edits. No application code,
schema, migration, or dependency changes were made after the latest CTO instruction
until this audit record and the baseline record below were created.

The authoritative production entrypoint is `wsgi.py` -> `app.create_app()`. The
authoritative browser workspace is the `dashboard.browser_routes` and
`dashboard.analyst_workspace` path registered by `app.create_app`; `dashboard.app` and
`services.api.dashboard.routes` are not registered by that factory.

## Existing

### Authentication and sessions

- `app/__init__.py` / `create_app`: creates the Flask application, configures the
  runtime secret, HttpOnly sessions, Secure cookies according to runtime configuration,
  SameSite=Lax, a 30-day permanent-session lifetime, session restoration, and session
  epoch enforcement. Reuse and extend this boundary.
- `services/auth/routes.py`: canonical `/api/auth` HTTP boundary for registration,
  password login, email OTP login, password recovery, phone OTP, Google callback,
  logout, CSRF, and persistent-session management. It derives the session principal
  through `_login_session`; it does not accept a client-selected tenant or role as the
  authorization authority.
- `services/auth/auth_service.py`: password registration/authentication, scrypt
  password hashing through `services/auth/security.py`, OTP persistence, hashed OTPs,
  expiry, attempt counts, cooldown, persistent sessions, revocation, session-version
  invalidation, and auth events.
- `services/auth/security.py`: Werkzeug scrypt password hashing and synchronizer CSRF
  token generation. Reuse; do not create a second security stack.
- `services/auth/oauth.py`: Google OIDC discovery, authorization-code exchange, state,
  nonce, issuer/audience/signature/time validation, and `email_verified` validation.
  Reuse, subject to the account-linking finding below.
- `services/auth/providers.py`: provider-neutral email and SMS interfaces, with test
  providers and explicit production-provider configuration failures. Reuse the
  abstraction; do not treat test providers as production evidence.

### Authorization, tenants, and pilot boundary

- `database/canonical_authority.py`: durable canonical tenants, identities, identity
  bindings, and memberships. `services/core/security_context.py` resolves tenant and
  role from the authenticated session plus canonical membership and rejects conflicting
  client tenant headers.
- `services/auth/permissions.py`: server-side permission map and `permission_required`
  decorator. `services/core/security_context.py` and the pilot boundary provide the
  lower-level request and pilot authorization checks.
- `services/pilot_management/authorization.py` and
  `services/core/pilot_boundary.py`: bounded pilot authorization, expiry, scenario
  restrictions, revocation, and fail-closed analyst access requirements.
- `services/pilot_management/provisioning.py`: manager-controlled pilot account,
  canonical tenant, identity, analyst membership, authorization, activation, expiry,
  and audit provisioning. This is separate from self-service registration and must not
  be duplicated.

### Analyst workspace and data

- `dashboard/browser_routes.py`: registered browser routes for authenticated home,
  workspace, investigation detail, reports, investigation execution, and analyst
  feedback. `_principal()` requires a canonical authenticated identity, tenant, active
  membership, and active user. Detail/report/action paths use tenant-scoped coordinator
  operations and server-side authorization.
- `services/intelligence/orchestration/investigation_coordinator.py`: canonical
  workspace snapshot and investigation read/write orchestration. It combines reports,
  intelligence, evidence, IOC, timeline, MITRE/context, confidence, uncertainty, and
  provenance-bearing state by tenant.
- `services/intelligence/reporting/investigation_projection.py` and
  `services/intelligence/reporting/ai_investigator_report.py`: projection/report
  boundaries used by the browser workspace. Reuse these rather than reading legacy
  tables directly.
- `database/repository.py`, `database/schema.py`, and `database/ioc_repository.py`:
  legacy case/evidence/timeline/IOC/note/action persistence. These tables are useful
  persistence infrastructure but their low-level helpers are not, by themselves, an
  authorization boundary.

### Audit, rate limiting, and deployment

- `services/audit`, `services/auth/auth_service.py`, and the pilot-management services
  provide existing audit/event conventions. Auth events are persisted without raw
  passwords, OTP values, session tokens, or OAuth tokens.
- `services/auth/rate_limit.py` and `services/rate_limiting.py` provide database/Redis
  rate-limit boundaries used by auth endpoints.
- `config/runtime.py`, `deployment/staging/.env.example`, `deployment/staging/docker-compose.yml`,
  `deployment/staging/nginx.conf`, and the Gate 5 runbooks define runtime, TLS, and
  private-access configuration. These are deployment controls, not onboarding state.

## Partially implemented

### Registration is secure at the current HTTP boundary, but not a complete state machine

`services/auth/routes.py::register` forces the application role to `analyst`, ignores
client role/tenant values, requires both consumed email and phone challenges for the
browser-style path, validates date of birth, and binds a canonical tenant/membership.
However, it also retains `AUTH_LEGACY_JSON_COMPAT` for JSON registrations that omit DOB
and phone. In non-production environments this can create a user without email/phone
verification. This is a compatibility boundary, not proof that the requested mandatory
onboarding lifecycle exists. It must be explicitly retained, narrowed, or retired only
after an API compatibility decision and tests.

`services/auth/routes.py::_bind` creates a tenant and membership when none exists, and
`_login_session` establishes the authenticated session immediately. The implementation
now persists `users.onboarding_state` and validates transitions in
`services/auth/onboarding.py`/`AuthService`, but it does not yet expose a complete
server-driven resume endpoint or a durable self-service provisioning retry workflow.

### OTP controls exist but need lifecycle hardening

`services/auth/otp.py` and `AuthService.issue_otp/verify_otp` provide secure random
six-digit values, HMAC-derived storage, ten-minute expiry, five attempts, single-use
consumption, and a sixty-second resend cooldown. Route-level rate limits are present.
The verifier now uses a conditional atomic consume update and browser-issued challenges
are bound to the signed auth-flow session. A real concurrent-request test and operational
provider behavior still need to be measured.

### Google OIDC is implemented, but first-login/account-linking policy needs an explicit decision

`services/auth/oauth.py` validates the provider token boundary. `services/auth/routes.py`
links an authenticated user only through the CSRF-protected link path, while an existing
provider subject is resolved before a first-login registration. The implementation needs
tests proving that a matching email alone cannot silently bind a Google subject to an
existing password account, and that callback/redirect failures remain generic.

### Visual authentication experience exists as a composed shell, not yet browser-accepted

`dashboard/templates/login.html`, `signup.html`, and `forgot_password.html`, plus
`dashboard/static/css/sentinel-dna-auth.css` and `dashboard/static/js/sentinel-dna-auth.js`,
compose the Sentinel DNA dark SOC authentication shell, OTP controls, country selection,
password-strength states, loading/error states, reduced-motion behavior, and secure
same-origin API calls. The in-app browser runtime was unavailable (`No browser is
available`), so this is an engineering inspection result, not browser acceptance.

## Missing

- A complete server-driven onboarding resume endpoint and durable self-service workspace
  provisioning/retry state integrated with the existing provisioning services.
- Idempotency keys or equivalent durable deduplication for registration, verification,
  workspace provisioning, and retried onboarding operations.
- A defined, tested production email provider adapter and SMS provider adapter. The
  current production configuration intentionally fails closed when adapters are absent.
- A supported canonical `SOC-L1` role identifier or an explicit documented mapping from
  the product label `SOC-L1` to the existing canonical `analyst` role. The current role
  authorities are `admin`, `soc_manager`, `analyst`, and `viewer`; silently adding a new
  role would affect permissions, pilot authorization, and existing tests.
- A durable self-service workspace provisioning state and retry path integrated with the
  existing canonical authority/pilot provisioning services.
- Complete browser-level acceptance evidence for desktop 1366x768 and mobile flows.

## Insecure or security-sensitive findings

### Legacy dashboard surface

`dashboard/app.py` contains a separate legacy Flask dashboard path that directly reads
legacy case/evidence/timeline/action/note/IOC helpers. Several helpers in
`database/repository.py` are global by case ID and do not encode tenant authorization.
Although this surface is not registered by the authoritative `app.create_app` path, it
is a duplicate security boundary and must remain unreachable from production routing or
be retired through a separately approved migration. Do not use it for new dashboard
features.

### Duplicate dashboard API

`services/api/dashboard/routes.py` defines a separate dashboard blueprint. It is not
registered by `app.create_app`; the authoritative browser path uses
`dashboard.browser_routes`. Any future registration of this blueprint without a review
would create a parallel data/authorization surface. It should remain unregistered or
be removed only through an explicit architecture change.

### Role-model conflict

`services/auth/routes.py` and `AuthService.ROLES` use `analyst`; canonical permissions
and pilot authorization also use `analyst`. The requested `SOC-L1` default is therefore
not an independently verified existing role. Treating a client-supplied `SOC-L1` as a
new privilege or changing existing role semantics would violate the CTO rule. Resolve
through a canonical role alias/migration decision, with authorization tests, before
implementation.

### Onboarding compatibility and resume risk

The legacy registration branch is deliberately compatible with existing tests and API
callers, but it does not represent the requested mandatory email/phone/profile/workspace
flow. Staging and production have `AUTH_LEGACY_JSON_COMPAT` disabled; only development
and test environments retain the compatibility branch. The persisted state blocks
authentication until completion, but a partially completed account does not yet have a
complete user-facing resume/provisioning-retry API. No frontend state may be accepted as
proof of completion.

### OTP lifecycle risk

The current OTP verifier now checks an unconsumed row and performs an atomic conditional
consume. Challenge identifiers remain opaque and registration challenges are bound to
the signed browser auth flow. Concurrent operational behavior and provider failure
handling still need an execution result.

## Duplicate

- `dashboard/app.py` versus `dashboard/browser_routes.py` are competing browser dashboard
  implementations. Only `browser_routes` is authoritative for the WSGI application.
- `services/dashboard/dashboard_service.py` and
  `services/intelligence/dashboard/dashboard_service.py` expose similarly named dashboard
  services. Their consumers must be mapped before any new service is introduced.
- `services/api/dashboard/routes.py` is a second dashboard API boundary and is not part
  of the active app factory.
- `services/onboarding/wizard.py` is an in-memory deployment wizard for organization,
  invitation, connector, validation, and security-assessment steps. It is not the
  account onboarding state machine requested here and cannot be treated as one.

## Needs testing

- Server-side authentication, logout, session rotation, expiry, revocation, CSRF, and
  generic error behavior across all auth routes.
- Email and phone OTP normalization, Nigeria `+234`, expiry, retry limit, replay,
  resend cooldown, provider failure, rate-limit behavior, and concurrent verification.
- Duplicate registration and duplicate workspace provisioning under retries and multiple
  tabs.
- Google callback state/nonce, invalid redirect/provider failures, provider-subject
  collision, and no email-only account linking.
- Direct API tenant/workspace/role/onboarding-state tampering and cross-tenant reads,
  writes, reports, notes, actions, and pilot resources.
- Incomplete-onboarding resume and direct dashboard URL denial.
- Dashboard reconciliation against the canonical coordinator/read models; no stale/mock
  production data; correct status/confidence/uncertainty/provenance/contradiction
  display; safe unavailable/empty/malformed response handling.
- Keyboard, focus, screen-reader labels, reduced motion, responsive layout, country
  selector behavior, OTP paste/autofill, and mobile touch targets.
- Actual approved-device Tailscale reachability and TLS validation. Repository validators
  must remain fail-closed when policy/custody evidence is absent.

## Baseline record

This baseline is not a pristine Git baseline because the working tree contained
intentional Gate 5 changes and the implementation session had begun before this CTO
instruction. It is the earliest recorded test evidence available for comparison.

| Area | Command/environment | Result | Classification |
|---|---|---|---|
| Node/staging contracts | `npm.cmd test`, Windows PowerShell | 88 total; 86 passed; 2 failed | Both failures were trusted-browser environment failures: missing operator bridge/native Playwright runtime behavior. |
| Dashboard Python | `py -3 -m pytest tests/dashboard -q` | Assertion output reached 100%; teardown hung and the process was interrupted; no assertion failure was reported before interruption | Environment/teardown condition; exact final exit unavailable. |
| Browser | In-app browser runtime | `No browser is available` | Environment blocker; no browser acceptance claim. |

The later focused post-edit result (`125 passed, 4 skipped`) is not a baseline and is
recorded in the implementation report. No baseline failure may be relabeled as a pass
without rerunning the same command and classifying the cause.

## Recommendations

1. Keep `app.create_app` -> `browser_routes` -> canonical coordinator as the only new
   dashboard path.
2. Define the role compatibility decision for `SOC-L1` before changing role storage or
   permission semantics.
3. Add a durable onboarding state integrated with the existing auth, canonical authority,
   and provisioning boundaries; do not use browser storage or URL state as authority.
4. Make OTP consumption atomic and bind verification to the server-side onboarding
   context.
5. Preserve production fail-closed provider behavior and document required provider env
   configuration.
6. Complete adversarial, browser, mobile, and operational pilot validation before any
   Gate 5 completion claim.
