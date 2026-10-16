# Sentinel DNA Synthetic Analyst Workflow MVP Design

## Purpose

Deliver a usable, non-production Sentinel DNA workflow in which one synthetic-data analyst can review an alert, inspect the resulting investigation, make an independent decision, and preserve an auditable record. This is product validation for the analyst experience; it is not release authorization, external analyst activation, or production readiness.

## User and success outcome

The primary user is a SOC analyst working in an isolated environment with approved synthetic scenarios. They should be able to complete the workflow without shell, database, or administrator access:

1. Sign in with an authorized account and complete MFA when required.
2. Open their tenant-scoped workspace and choose an approved synthetic investigation.
3. Start or review the investigation and understand its evidence, indicators, timeline, reasoning, confidence, uncertainty, provenance, and unavailable sources.
4. Record an independent decision or request further review, with feedback attributed to the authenticated analyst and tenant.
5. Inspect the report and audit/provenance references, then sign out.

The MVP is successful when this journey is repeatable for the approved synthetic scenario set, gives clear feedback when a step cannot proceed, and has automated evidence for its security boundaries. AI output remains advisory; analyst actions remain explicit.

## Scope

### Included

- The existing browser login, MFA, analyst workspace, investigation detail/report, feedback, and logout paths.
- An explicit path from the workspace to approved synthetic investigations, with clear loading, empty, unavailable, and error states.
- Evidence and provenance visibility, including clear separation between observed evidence, correlation, and inference.
- Append-only analyst feedback and server-derived actor and tenant attribution.
- An automated, deterministic end-to-end workflow check that does not require binding a localhost socket.
- Focused regression coverage for authentication, MFA, CSRF, OTP replay protection, tenant isolation, pilot authorization, and access revocation.

### Excluded

- Customer or production data, public analyst access, real-analyst activation, external notification, autonomous response, and unrestricted SOAR or command execution.
- Deployment, image rebuilding, migrations, account provisioning in a live environment, and production or staging changes.
- New intelligence providers or other broad platform capabilities unless the workflow review proves one is essential to complete this journey.

## Existing components and intended flow

Reuse the current canonical WSGI dashboard application and existing boundaries:

- Authentication and MFA establish the server-side principal.
- Canonical identity, membership, and pilot authorization resolve the allowed tenant and scenarios.
- The workspace and investigation routes read tenant-scoped cases and investigation data.
- Existing orchestration and evidence services produce investigation results; AI conclusions stay advisory.
- The existing report view renders results and evidence references.
- The append-only feedback boundary derives analyst and tenant identity server-side and emits audit records.
- Logout and authorization revocation invalidate the applicable session.

No parallel investigation route, alternate feedback store, client-selected tenant, or new privileged bypass is introduced.

## User experience and failure behavior

- Show only cases the signed-in analyst is authorized to access.
- Explain empty queues and unavailable evidence without inventing findings or reporting provider failures as successful evidence.
- Keep provenance and uncertainty visible with each relevant finding.
- Preserve the analyst's ability to disagree with the AI or request more review.
- Reject invalid, expired, replayed, cross-session, cross-tenant, or unauthorized actions at the server boundary; the interface should present a safe, actionable error without exposing secrets or internal exception details.
- Give a clear submitting/success/error state for feedback and preserve the server's append-only behavior.

## Security and data requirements

- Preserve CSRF checks on state-changing browser requests.
- Preserve MFA requirements and short-lived server-bound MFA state.
- Preserve single-use, session-bound OTP verification and replay rejection.
- Derive role, analyst, and tenant from canonical server-side identity and authorization state.
- Keep pilot authorization bounded to approved scenarios, tenant, lifetime, and revocation state.
- Keep feedback append-only and audit-linked; never trust client-supplied actor, tenant, timestamp, or record identifiers.
- Use synthetic data only. Do not create default accounts or credentials as part of the workflow.
- Do not expose secrets, tokens, or raw internal exceptions in the interface, logs, or evidence artifacts.

## Verification and acceptance criteria

1. An unauthenticated user cannot reach the workspace, investigation, report, or feedback surfaces.
2. An authenticated but unauthorized or non-MFA-complete user cannot bypass the existing pilot/MFA boundary.
3. The workspace lists only the current tenant's authorized synthetic investigations.
4. An authorized analyst can open a case, inspect its evidence and provenance, review a report, and submit a valid decision or request for review.
5. Feedback records use server-derived analyst and tenant identity and remain append-only and auditable.
6. Cross-tenant identifiers, forged identity fields, invalid CSRF, replayed OTP, expired authorization, and revoked sessions remain denied.
7. Missing or failed providers appear as unavailable/degraded, never as fabricated successful evidence.
8. The end-to-end acceptance test runs deterministically without requiring a local network socket; the separate socket-bound HTTP test is reported independently when the host permits it.
9. Focused tests pass before broader non-container regression tests are considered. Environment-only failures are reported with their full test name, traceback, and cause; security assertions are not weakened to obtain a pass.

## Delivery sequence

1. Map the current browser and service flow against the acceptance criteria and identify concrete gaps.
2. Fix only demonstrated gaps in the smallest coherent slices, with a regression test for each behavior change.
3. Verify the full synthetic analyst journey and all affected security boundaries.
4. Update user-facing workflow documentation to match the verified behavior and list any external operational gates separately.

The current dirty worktree, branch, and existing security remediation changes must be preserved throughout. No commit, push, deployment, image rebuild, migration, account provisioning, or staging/production mutation is part of this design phase.

## Design review — 2026-10-15

**Decision: APPROVE WITH SPECIFIC ADJUSTMENTS.** The workflow is achievable with the existing WSGI browser routes, coordinator, tenant-scoped read model, report projection, feedback repository, and audit service. Existing focused tests cover many security controls. The following corrections are required before implementation so the criteria match the actual WSGI app and test results:

1. **Synthetic scenario activation:** `dashboard.browser_routes` seeds its demo scenario only when `DEMO_DATA_ENABLED` is true. The WSGI-owned `dashboard.app` does not currently wire that setting, although the separate `app.create_app()` factory already uses `SENTINEL_DNA_DEMO_DATA` (default on outside production and off in production). The WSGI app must honor that existing setting and production default; add tests for explicit demo-disabled behavior and the canonical WSGI workflow. Do not add a new toggle name or enable synthetic data in production by default.
2. **Canonical test entrypoint and registration:** Current failures in demo/logout/pilot-route tests occur before their intended assertions because the fixtures use the old bare JSON registration payload. Update the fixtures to exercise `wsgi.application` and either use the verified CSRF-protected registration flow or create role-specific users through an explicit server-side test fixture. Never restore the public-registration bypass.
3. **Execution and failure truthfulness:** The acceptance criteria must prove that starting the synthetic case calls the existing coordinator and that the persisted execution/report status is shown honestly. If investigation, report projection, or feedback persistence fails, the UI/API must return a safe failure state without claiming success or exposing exception details. Add positive and failure-path tests for these outcomes.

These adjustments preserve the approved user journey and existing security boundaries; they correct configuration ownership and make the acceptance criteria observable in the code that production WSGI actually serves.
