# Sentinel DNA Authentication and Onboarding Architecture Decision

Date: 2026-09-02
Status: Implemented incrementally after forensic audit; security-critical role/provider/resume decisions remain open.

## Decision summary

Extend the existing canonical authentication boundary and existing canonical authority.
The active integration path is:

`browser auth UI -> /api/auth -> AuthService/providers -> canonical identity and membership -> existing workspace/pilot authorization -> browser workspace`

The existing `app.create_app` factory and WSGI entrypoint remain authoritative. No new
authentication service, tenant service, session stack, audit system, or dashboard API
should be introduced.

## Existing architecture

1. Authentication: `services/auth/routes.py` and `services/auth/auth_service.py`.
2. Password/CSRF: `services/auth/security.py`.
3. Sessions: Flask signed session plus `persistent_sessions`, session versioning, and
   revocation in `AuthService`.
4. OAuth/OIDC: `services/auth/oauth.py::GoogleOIDC` and the Google routes.
5. Email/SMS: `services/auth/providers.py` provider abstractions and OTP persistence in
   `AuthService`.
6. Authorization: `services/core/security_context.py`, `services/auth/permissions.py`,
   `services/core/pilot_boundary.py`, and pilot authorization services.
7. Tenant/workspace authority: `database/canonical_authority.py`, canonical memberships,
   and `services/pilot_management/provisioning.py`.
8. Audit: existing `services/audit` plus auth/pilot event stores and conventions.
9. Browser workspace: `dashboard/browser_routes.py`, the registered analyst workspace,
   and `InvestigationCoordinator` read models.

## Onboarding decision

The in-memory `services/onboarding/wizard.py` is not suitable for account onboarding.
The implementation adds a small durable server-owned state and transition boundary in
`services/auth/onboarding.py` and the existing `users` record. The state is reconciled
with the current users and OTP records; canonical membership and provisioning remain
existing authorities. A browser route,
local storage value, cookie flag, role field, tenant field, or request payload cannot
advance the authoritative state.

Every implemented transition is validated by the backend. A complete resume endpoint,
provisioning retry record, and idempotency contract remain future work and must extend
this same boundary rather than create a second account lifecycle.

## Authorization decision

Use `request_context()` and canonical memberships for tenant/workspace/role. Continue to
reject conflicting `X-Organization-ID` values and never trust client tenant, workspace,
or role fields. Use `permission_required` and the pilot boundary for operation checks.

The requested default `SOC-L1` conflicts with the existing canonical role vocabulary
(`analyst`). This is intentionally unresolved. The safe choices are:

- retain canonical `analyst` and expose `SOC-L1` only as a product label, or
- introduce a formally approved canonical alias/migration with a complete permission,
  pilot, audit, and backward-compatibility review.

No implementation may silently store or authorize a new role.

## Components reused

- `AuthService` for password, OTP, sessions, revocation, and audit events.
- `GoogleOIDC` for provider flow and cryptographic claim validation.
- Email/SMS provider interfaces.
- Canonical identity, tenant, and membership repositories.
- `SecurityContext`, permission map, pilot boundary, and pilot provisioning.
- Existing audit service/event formats.
- Existing WSGI/app factory and browser workspace.
- Existing coordinator/report/projection services for dashboard data.
- Existing templates/tokens and the authentication styling/behavior extensions already
  present in the working tree.

## Components modified or potentially modified

- Auth route orchestration only where a verified onboarding-state or OTP atomicity gap
  requires it.
- `services/auth/onboarding.py` and additive auth persistence fields for server-owned
  state and browser-flow binding.
- Auth tests and staging/security tests for adversarial coverage.
- Auth templates/static assets for the premium Sentinel DNA shell, while preserving API
  and security behavior.
- Documentation and environment examples for provider/custody configuration.

## New components, if genuinely necessary

The small `services/auth/onboarding.py` state guard is justified because no durable
account onboarding state existed. It owns state names/transition validation only;
`AuthService` owns persistence. It does not own a second user, tenant, role, session,
OTP, or audit database.

## Rejected alternatives

- New auth microservice: duplicates and fragments the existing server-authoritative auth.
- Client/local-storage onboarding state: bypassable and violates backend authority.
- Client-selected tenant/workspace/role: violates canonical authority and tenant
  isolation.
- A second dashboard API or direct legacy-table dashboard: creates an authorization
  split and risks cross-tenant leakage.
- Treating phone verification as MFA without an existing policy/step-up architecture:
  misleading and potentially unsafe.
- Automatically linking Google by email alone: account-linking vulnerability.
- Test/console providers as production providers: would invalidate real pilot evidence.

## Database impact

The implementation uses additive runtime schema evolution already used by `AuthService`
to add `users.onboarding_state` and `otp_challenges.session_binding`; no destructive
migration or session invalidation was applied. If deployment policy disallows runtime
schema evolution, promote these additive changes into a formal migration before
production. Existing records default to `AUTHENTICATED` for backward compatibility and
must be reviewed before production use.

## API impact

Prefer existing `/api/auth` routes and existing workspace routes. Any new endpoint must
be justified as absent, CSRF-protected where state-changing, rate-limited, generic in
errors, tenant-derived from the session, and covered by direct API authorization tests.

## Security impact

The decision preserves server-side authentication, authorization, tenant membership,
pilot bounds, CSRF, session revocation, audit, and fail-closed production provider
configuration. The implementation closes OTP concurrency/challenge binding and adds
backend state guards. Remaining security work is user-facing resume/provisioning retry,
duplicate/idempotency behavior, and the role vocabulary conflict without weakening
existing controls.

## Migration impact and rollback

The additive runtime schema changes should be promoted to a formal migration if required
by deployment policy. Rollback is to deploy the prior code while retaining the additive
nullable/defaulted columns; no old columns or existing sessions need to be deleted or
revoked. Rollback must disable new transitions safely and preserve audit records.

## Compatibility considerations

The non-production legacy JSON registration compatibility path is used by existing tests
and callers. Its future behavior must be versioned or explicitly narrowed; production
must remain fail-closed for incomplete onboarding. Existing canonical role strings,
pilot fixtures, session cookies, and Google subject bindings must remain compatible until
an approved migration exists.

## Open decisions required before security completion

1. Is `SOC-L1` a display label for canonical `analyst`, or a new canonical role?
2. Is phone verification onboarding/account verification or a true MFA factor in the
   existing security policy? Current code supports onboarding verification only.
3. Which existing provisioning record/service is authoritative for self-service
   workspace readiness?
4. Which production email and SMS adapters are approved and how are their credentials
   supplied outside the repository?
5. What browser-capable test environment will provide the real acceptance evidence?
