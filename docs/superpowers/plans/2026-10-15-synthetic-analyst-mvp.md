# Sentinel DNA Synthetic Analyst MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the existing, tenant-scoped synthetic analyst journey usable end to end through the canonical WSGI app and prove its security and failure behavior with repeatable local tests.

**Architecture:** Reuse `wsgi.application`, the existing browser routes, investigation coordinator, tenant-scoped read model, report projection, feedback repository, and audit service. Align the WSGI demo-data configuration with the existing `SENTINEL_DNA_DEMO_DATA` setting, repair stale test setup without restoring legacy registration, then add verified execution/failure evidence and user-facing run instructions.

**Tech Stack:** Python 3.12, Flask, pytest, SQLite test databases, canonical WSGI app, existing coordinator and service container.

**Spec:** `docs/superpowers/specs/2026-10-15-synthetic-analyst-workflow-design.md`

## Global Constraints

- Use synthetic data only; do not use customer or production data.
- Keep AI output advisory and analyst decisions explicit.
- Preserve CSRF, MFA, OTP replay protection, canonical identity, tenant isolation, pilot authorization, audit, and append-only feedback.
- Do not create default accounts or credentials.
- Do not create a parallel investigation route, alternate feedback store, client-selected tenant, or privileged bypass.
- Preserve the current dirty worktree and all existing remediation changes.
- Do not commit, push, deploy, rebuild images, run migrations against live systems, provision live accounts, or mutate staging/production.
- Use `SENTINEL_DNA_DEMO_DATA`; keep its default disabled in production and consistent with the existing factory's non-production behavior.
- Report any environment-only failure separately from application failures; never weaken a security assertion to obtain a pass.

## Review Focus

1. **Registration challenge or CSRF is absent, expired, replayed, or bound to another session:** keep public signup on the verified flow; cover in `tests/auth/test_auth_v3.py` and `tests/dashboard/test_auth_experience.py`.
2. **Demo data is disabled or deployment environment is production:** keep demo seeding conditional on the canonical WSGI config; cover enabled/disabled behavior in `tests/security/test_analyst_demo_workflow.py` and inspect the production default.
3. **Tenant, role, or organization is supplied or altered by the client:** preserve server-derived authorization; cover in `tests/security/test_production_entrypoint_reconciliation.py`, `tests/security/test_pilot_route_boundary.py`, and `tests/security/test_analyst_demo_workflow.py`.
4. **Coordinator, report projection, or feedback persistence fails:** show a safe failure and do not claim successful execution or feedback; cover in `tests/security/test_analyst_demo_workflow.py`.
5. **Windows denies a localhost socket:** keep the canonical end-to-end path repeatable with Flask's test client and report `tests/auth/test_http_v3.py` independently; do not skip or relabel the socket test as an application pass.

---

## Verified baseline and design decision

- Repository: `C:\Users\HP\Documents\Codex\sentinel-dna-pr26-fixture-fix-136c8aa`.
- Branch: `fix/signup-registration-security-20261014`.
- HEAD: `980a1bcdda07a422ad9b4ae4000389a295083149` (matches expected checkpoint).
- Existing tracked modifications: `dashboard/app.py`, `dashboard/templates/signup.html`, `services/auth/auth_service.py`, `services/auth/routes.py`, four auth test files, `tests/dashboard/test_auth_experience.py`, `tests/security/test_production_entrypoint_reconciliation.py`, and `wsgi.py`.
- Existing untracked design: `docs/superpowers/specs/2026-10-15-synthetic-analyst-workflow-design.md`.
- `git diff --check`: pass; existing signup-template CRLF normalization warning only.
- Python environment: `C:\Users\HP\Documents\Codex\sentinel-dna-venv-diagnostic-20261014\Scripts\python.exe`, Python 3.12.10, pytest 9.1.1. Use `C:\Users\HP\Documents\Codex\sentinel-dna-python-temp-20261014` as pytest basetemp and disable its cache plugin because default Windows sandbox temp/cache writes are denied.
- Focused baseline: 49 passed, 1 failed. The failure is `tests/auth/test_http_v3.py::test_canonical_wsgi_http_v3_journey`; `requests.get("http://127.0.0.1:5000/login")` fails with `PermissionError: [WinError 10013]` before Flask receives the request.
- Related workflow/security baseline: 18 tests; 8 passed and 10 failed. All 10 fail at bare `POST /api/auth/register` assertions (`400 != 201`) before reaching intended assertions. These fixtures still use the legacy registration payload. Failures are test setup incompatibilities, not demonstrated application authorization failures.
- Design review: **APPROVE WITH SPECIFIC ADJUSTMENTS**, recorded in the spec: align WSGI demo config with `SENTINEL_DNA_DEMO_DATA`, use the canonical WSGI app and current registration in tests, and assert truthful/safe execution/report/feedback failures.

## Tasks

### Task 1: Repair stale security and analyst-workflow test setup

**Priority:** P0 — needed to make the intended assertions executable.

**Files:**
- Modify: `tests/security/test_analyst_demo_workflow.py`
- Modify: `tests/security/test_logout_navigation.py`
- Modify: `tests/security/test_pilot_route_boundary.py`
- Reuse or add: `tests/security/conftest.py` for one isolated canonical WSGI fixture and current registration helper, only if it removes duplicated setup.
- Reference: `tests/security/test_production_entrypoint_reconciliation.py`, `tests/dashboard/test_auth_experience.py`

**Observed issue:** The related baseline's 10 failures occur during setup because these tests use bare JSON registration that the current public endpoint intentionally rejects. They do not reach the tenant, pilot, logout, demo, or feedback assertions.

**Minimal change:** Exercise `wsgi.application` for browser behavior. Use the existing CSRF-protected email-code registration sequence for analyst accounts. For tests requiring a privileged role, construct that role through an explicit server-side test fixture and canonical membership binding; never submit a client-selected role or reinstate legacy registration compatibility. Ensure auth, canonical authority, MFA, audit, coordinator, and repositories use the same temporary SQLite target, and restore global app/container state after each test.

**Security implications:** Preserve the public signup role as analyst-only. Keep role escalation, CSRF, tenant conflict, and pilot boundary assertions meaningful. No change to production authorization.

**Tests:**
- `tests/security/test_analyst_demo_workflow.py`
- `tests/security/test_logout_navigation.py`
- `tests/security/test_pilot_route_boundary.py`
- `tests/security/test_production_entrypoint_reconciliation.py`

**Dependencies:** Existing auth, MFA, audit, canonical authority, and test-provider classes.

**Completion evidence:** All corrected tests reach their intended assertions; authorization denials and logout behavior remain unchanged; fixture setup/teardown leaves the global app and database target restored.

**Blocked by external dependency:** No.

**Steps:**

- [ ] **Step 1: Capture the current red state for the three affected test modules.** Run the Task 1 tests with the isolated Python environment and writable `--basetemp`. Expected: registration setup fails before the intended demo, logout, or pilot assertions, matching the baseline traceback.
- [ ] **Step 2: Add an isolated canonical WSGI fixture.** In `tests/security/conftest.py`, create a `canonical_application` fixture that redirects the shared database path to `tmp_path`, migrates only that disposable test database, installs matching auth/canonical-authority/MFA/audit services and test email/SMS providers, sets `TESTING=True` and `PILOT_ACCESS_REQUIRED=False`, and restores all changed registry/config/database state in `finally`.
- [ ] **Step 3: Add `register_and_login_analyst(client, username, email)` to the same fixture module.** It must fetch the current CSRF token, send and verify the test email code, register with DOB and challenge ID, then log in. Assert each expected status before proceeding.
- [ ] **Step 4: Migrate the demo and logout tests to `wsgi.application` plus the shared fixture/helper.** Keep the route assertions and use the fixture's explicit `DEMO_DATA_ENABLED=True` for demo tests.
- [ ] **Step 5: Migrate pilot-route tests to the WSGI app.** Use the verified analyst helper for analyst cases. For the role-escalation case, promote only the legacy user role inside the isolated test database while leaving canonical membership as analyst; preserve the denial assertions.
- [ ] **Step 6: Run the four Task 1 test modules.** Expected: all tests pass and each reaches its authorization/workflow assertion; no application code changes are needed for this task.

### Task 2: Wire synthetic scenario mode into the WSGI-owned app

**Priority:** P0 — without this, the real WSGI workspace can remain empty even though the synthetic scenario service exists.

**Files:**
- Modify: `dashboard/app.py`
- Test: `tests/security/test_analyst_demo_workflow.py`
- Reference: `app/__init__.py`, `dashboard/browser_routes.py`, `services/intelligence/demo/analyst_scenario.py`

**Observed issue:** `dashboard.browser_routes._ensure_demo_scenario()` and `/start` require `DEMO_DATA_ENABLED`, but `dashboard.app.app` does not set it. The separate `app.create_app()` already reads `SENTINEL_DNA_DEMO_DATA`, defaulting on outside production and off in production. The actual WSGI entrypoint is `dashboard.app.app`.

**Minimal change:** Initialize `DEMO_DATA_ENABLED` in `dashboard.app` from the existing `SENTINEL_DNA_DEMO_DATA` contract, matching the existing factory's default behavior. Do not add a new toggle or seed when the effective setting is false. Confirm that workspace access still requires canonical authentication and tenant context before scenario seeding.

**Security implications:** Synthetic data remains tenant-specific, opt-out, and off by default in production. Do not change public access, pilot authorization, or any authentication boundary.

**Tests:**
- `test_workspace_provisions_one_tenant_scoped_synthetic_case`
- `test_disabled_demo_mode_preserves_honest_empty_states`
- `test_demo_case_is_not_readable_across_tenants`
- `test_wsgi_application_preserves_pilot_analyst_boundary`

**Dependencies:** Task 1's canonical WSGI fixture.

**Completion evidence:** In the canonical WSGI app with demo mode enabled, the approved synthetic case is tenant-bound and repeatable; with it disabled, honest empty states remain; production default evaluates false.

**Blocked by external dependency:** No.

**Steps:**

- [ ] **Step 1: Write `test_demo_data_setting_defaults_and_override` in `tests/security/test_analyst_demo_workflow.py`.** Assert `_demo_data_enabled("development", None)` and `_demo_data_enabled("testing", None)` are true, `_demo_data_enabled("production", None)` is false, and explicit `"0"`/`"1"` override the respective default.
- [ ] **Step 2: Run the new test before implementation.** Expected: fail because `dashboard.app` has no `_demo_data_enabled` helper.
- [ ] **Step 3: Implement `_demo_data_enabled(environment: str | None, configured_value: str | None) -> bool` in `dashboard/app.py`.** Use the same environment fallback and `SENTINEL_DNA_DEMO_DATA` default contract as `app/__init__.py`; set `app.config["DEMO_DATA_ENABLED"]` from it during WSGI app setup.
- [ ] **Step 4: Run the config test and Task 1 demo tests.** Expected: all pass; disabled mode stays empty and enabled cases remain tenant-scoped.

### Task 3: Prove the coordinator-backed analyst journey and safe failures

**Priority:** P1 — proves that the MVP runs investigations rather than only rendering persisted pages.

**Files:**
- Modify as required by failing tests: `dashboard/browser_routes.py`
- Modify as required by failing tests: `dashboard/templates/error.html` or existing detail/report templates
- Test: `tests/security/test_analyst_demo_workflow.py`
- Reference: `services/intelligence/orchestration/investigation_coordinator.py`, `services/intelligence/reporting/ai_investigator_report.py`

**Observed issue:** Existing intended workflow tests assert that `/start` invokes the coordinator and that detail/report views expose evidence, but stale registration prevents them from running. The browser start and report handlers also lack explicit generic safe responses for unexpected coordinator/projection errors.

**Minimal change:** Extend the canonical WSGI workflow test to sign in, see the tenant's synthetic case, start it through `InvestigationCoordinator.investigate`, inspect persisted execution status/evidence/provenance/reasoning/confidence, view the report, submit feedback, verify server-attributed persistence/audit, and sign out. Add failure tests for coordinator failure, report projection failure, and feedback persistence failure. Where current behavior exposes an unhandled exception or ambiguous success, add a generic safe error response and assert that internal exception text is absent and no success is reported. Preserve persisted failed execution status when the coordinator returns a failed result.

**Security implications:** Use authenticated test clients and CSRF tokens. Keep feedback append-only and tenant-scoped. Do not fabricate findings or promote unavailable evidence to success.

**Tests:**
- Extend `test_start_uses_canonical_coordinator_and_report` to assert actual successful execution status.
- Add focused failure-path tests in `tests/security/test_analyst_demo_workflow.py` for start, report, and feedback errors.
- Retain and run cross-tenant case/feedback denial tests.

**Dependencies:** Tasks 1 and 2.

**Completion evidence:** The canonical WSGI test proves the complete local synthetic journey with Flask's test client and shows accurate success/failure state without a socket.

**Blocked by external dependency:** No. The separate real-socket test remains subject to Windows sandbox permissions.

**Steps:**

- [ ] **Step 1: Extend `test_start_uses_canonical_coordinator_and_report` to assert the persisted execution status is `completed` and the report contains provenance/evidence references.** Run the test; expected: pass after Tasks 1–2, establishing the success baseline.
- [ ] **Step 2: Add one test each for unexpected coordinator, report projection, and feedback persistence exceptions.** Inject an exception containing a unique sentinel string. Assert a safe 503 response, no sentinel or traceback in the body, and no success response/redirect that implies the failed action completed.
- [ ] **Step 3: Run the three failure tests before changing route code.** Expected: fail because the unexpected exceptions currently escape the browser handlers under `TESTING=True`.
- [ ] **Step 4: Add narrow exception handling in `dashboard/browser_routes.py`.** Return the existing generic error page with status 503 for start/report failures; return a generic JSON 503 for JSON feedback requests and the same generic error page for form feedback. Do not include exception text and do not emit success audit/feedback state on failure.
- [ ] **Step 5: Run the full analyst demo workflow module.** Expected: success and failure cases pass, cross-tenant access remains 404, and feedback remains persisted/audited only on success.

### Task 4: Publish one acceptance matrix and synthetic demonstration procedure

**Priority:** P1 — makes the verified behavior repeatable for a reviewer.

**Files:**
- Create/update: `docs/product/SYNTHETIC_ANALYST_MVP_ACCEPTANCE.md`
- Reference/update if needed: `docs/product/MVP-definition.md`
- Reference: `docs/release/SOC_ANALYST_PILOT_READINESS.md`

**Observed issue:** `docs/product/MVP-definition.md` ends mid-example and does not define a complete, measurable synthetic analyst acceptance path. Existing pilot-readiness docs correctly distinguish synthetic evidence from real-analyst and release authorization.

**Minimal change:** Add one matrix mapping each approved criterion to the exact test or inspectable artifact and status. Include a local synthetic demonstration procedure using the supported app entrypoint, safe test data, and expected outcomes. Keep real analyst activation, external evaluation, and release gates clearly marked as separate and not performed.

**Security implications:** Documentation must not tell operators to expose a development endpoint, use customer data, create default credentials, or treat synthetic results as external validation.

**Tests:** No new application tests; validate every documented command against actual local test results and run Markdown/link/path checks already used by the repository if available.

**Dependencies:** Tasks 1–3 provide verified behavior and test names.

**Completion evidence:** The matrix contains no unsupported PASS claim; the demo procedure records environment assumptions and limitations.

**Blocked by external dependency:** External analyst evaluation and production/staging evidence remain blocked by separate authorization and infrastructure requirements; neither is required to complete the local synthetic MVP.

**Steps:**

- [ ] **Step 1: Create `docs/product/SYNTHETIC_ANALYST_MVP_ACCEPTANCE.md` with a table for each criterion, exact evidence source, status, and limitation.** Mark the socket-bound HTTP criterion `BLOCKED` if `WinError 10013` persists; do not count it as an application failure or PASS.
- [ ] **Step 2: Add a local demonstration procedure using the verified WSGI app and synthetic scenario.** Include safe environment assumptions, sign-in, workspace/case selection, investigation, evidence/report, feedback, and sign-out outcomes. State that no live account, staging, or production action is part of the procedure.
- [ ] **Step 3: Compare each acceptance criterion with the actual tests and run documented non-mutating commands.** Expected: no unsupported PASS entries, and all links/paths point to existing files.

### Task 5: Final focused and regression verification

**Priority:** P0 — required before calling this synthetic MVP verified.

**Files:** No product changes unless a demonstrated defect is found; any fix gets its own failing regression test first.

**Commands:**

```powershell
& 'C:\Users\HP\Documents\Codex\sentinel-dna-venv-diagnostic-20261014\Scripts\python.exe' -m pytest -p no:cacheprovider --basetemp='C:\Users\HP\Documents\Codex\sentinel-dna-python-temp-20261014\pytest-sentinel-final' tests/auth/test_auth_security.py tests/auth/test_auth_v3.py tests/auth/test_http_v3.py tests/auth/test_mfa.py tests/dashboard/test_auth_experience.py tests/security/test_production_entrypoint_reconciliation.py tests/security/test_analyst_demo_workflow.py tests/security/test_logout_navigation.py tests/security/test_pilot_route_boundary.py tests/dashboard/test_analyst_workspace_security.py tests/intelligence/investigation/test_analyst_feedback_pilot.py -vv --tb=short
```

Also run Python syntax compilation on changed Python files, relevant repository static checks if configured, `git diff --check`, and the broader non-container suite if the final focused group has no application regressions. Keep any socket-denied HTTP test's exact traceback in the final report and report pass/fail/skip/environmental-blocker counts separately.

**Dependencies:** Tasks 1–4.

**Completion evidence:** Captured test summary; all application tests pass; any remaining failures are classified with exact test name and root cause; branch, HEAD, status, and diff-check are reported. No commit or external action is performed.

**Blocked by external dependency:** Local socket test may remain blocked by Windows sandbox policy. Broader tests may be limited by optional PostgreSQL/Docker services.

**Steps:**

- [ ] **Step 1: Run the complete command above after Tasks 1–4.** Expected: all application tests pass; if `test_canonical_wsgi_http_v3_journey` still fails, its traceback is the known socket denial and is reported separately.
- [ ] **Step 2: Run Python syntax compilation on changed Python files, configured relevant static checks, and `git diff --check`.** Expected: no syntax/static/diff errors; any line-ending notice is reported.
- [ ] **Step 3: If all focused application tests pass, run the broader non-container regression suite using the same isolated temp/cache settings.** Expected: exact counts and each failure classified; do not run Docker, PostgreSQL integration, migrations, staging, or deployment actions.
- [ ] **Step 4: Review the final diff and status against the original checkpoint.** Expected: all pre-existing edits remain and only plan-scoped files changed; no commit or external operation occurred.

## Work log

| Task | Status | Evidence |
|---|---|---|
| Phase A: preserve and baseline | Complete | Expected repository/branch/HEAD verified; 11 pre-existing tracked modifications retained; design file untracked and preserved; initial diff-check clean apart from CRLF warning. |
| Design review | Complete — approve with adjustments | Decision and three specific corrections recorded in the design. |
| Workspace ruling | Complete | Continued in the user-designated dirty checkout. A fresh worktree would omit the unsaved remediation changes the user explicitly asked to preserve; cost if wrong is reduced isolation. No pre-existing change was reset or discarded. |
| Task 1: repair test setup | Complete | Migrated stale demo/logout/pilot tests to canonical WSGI and CSRF-protected verified signup. Four-module final run: 25 passed. Both canonical test fixtures restore registry/config/global database state and initialize coordinator repositories only on the disposable test DB. |
| Task 2: WSGI demo config and route | Complete | WSGI now resolves `SENTINEL_DNA_DEMO_DATA` with production default off; both workspace slash forms share the permission guard, canonical principal resolution, queue, and pilot allowlist. Config and parity tests pass. |
| Task 3: workflow and safe failures | Complete | End-to-end synthetic execution persists `completed` status and evidence references; coordinator/report/feedback exceptions produce safe 503 responses. Cross-tenant, pilot feedback POST allowlisting, and feedback checks pass. |
| Task 4: acceptance matrix/demo procedure | Complete | Added `docs/product/SYNTHETIC_ANALYST_MVP_ACCEPTANCE.md` and completed the previously truncated MVP definition. Claims match focused test evidence; release gates remain separate. |
| Task 5: final verification | Complete with blockers | Final focused: 73 passed, 1 loopback-only failure (`WinError 10013`), 0 skipped. Temp-corrected broad non-container run: 3,071 passed, 32 failed, 64 errors, 6 skipped, 10 deselected. A follow-up confirms the stale audit self-promotion test now passes with verified registration. Remaining representative blockers: Git/MSYS clone fails `NtCreateDirectoryObject ... 0xC0000022`; immutable evidence writing hits Windows hard-link `WinError 5`; several older integration tests still use rejected bare registration and receive 400/401; release-hygiene tests expect a clean checkout while this user-designated tree is intentionally dirty. Python syntax compilation passed; final `git diff --check` has no errors (signup-template CRLF notice only). |
