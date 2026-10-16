# Synthetic Analyst MVP Acceptance

## Scope

This acceptance record covers the local synthetic analyst workflow served by
the canonical WSGI application. It demonstrates a verified analyst signup, a
tenant-scoped synthetic investigation, an investigation run through the
canonical coordinator, evidence/report review, append-only analyst feedback,
and sign-out. It does not authorize a real analyst pilot or a release.

## Acceptance matrix

| Criterion | Evidence | Status / limitation |
|---|---|---|
| Public registration requires CSRF and a verified email challenge; public signup cannot select tenant or role. | `tests/auth/test_auth_v3.py`, `tests/dashboard/test_auth_experience.py`; current combined focused run | **PASS** — both modules passed; total focused result was 87 passed and one separately blocked HTTP test. |
| MFA boundary and OTP replay protection remain enforced. | `tests/auth/test_mfa.py`, `tests/auth/test_auth_security.py`; current combined focused run | **PASS** — all cases passed. |
| Both `/workspace` and `/workspace/` require the same authenticated canonical tenant context. | `tests/security/test_analyst_demo_workflow.py::test_workspace_slash_forms_share_authorization_and_queue`; `tests/security/test_production_entrypoint_reconciliation.py` | **PASS** — authenticated and unauthenticated path pairs were exercised through the WSGI test client. |
| Demo data is synthetic, tenant-scoped, repeatable, configurable, and off by default in production. | `tests/security/test_analyst_demo_workflow.py::test_demo_data_setting_defaults_and_override`, `test_workspace_provisions_one_tenant_scoped_synthetic_case`, `test_disabled_demo_mode_preserves_honest_empty_states` | **PASS** — test-client demonstration used disposable SQLite and synthetic fixture data. |
| A run persists an execution status and evidence references; report projection remains advisory. | `tests/security/test_analyst_demo_workflow.py::test_start_uses_canonical_coordinator_and_report` | **PASS** — coordinator execution persisted as completed with evidence references; detail and advisory report returned expected evidence/provenance markers. |
| Unexpected execution, report, and feedback failures return safe unavailable responses. | Three `*_failure_returns_safe_unavailable_response` tests in `tests/security/test_analyst_demo_workflow.py` | **PASS** — injected failures returned 503 without exception details or false success. |
| Cross-tenant case and feedback reads/writes are denied. | `tests/security/test_analyst_demo_workflow.py`, `tests/security/test_pilot_route_boundary.py`, `tests/dashboard/test_analyst_workspace_security.py` | **PASS** — tenant-bound read/write denials passed. |
| Pilot analysts remain constrained by the pilot authorization boundary. | `tests/security/test_pilot_route_boundary.py`, `tests/security/test_production_entrypoint_reconciliation.py`, `tests/intelligence/investigation/test_analyst_feedback_pilot.py` | **PASS** — pilot route and permission checks passed. |
| Browser logout requires CSRF and invalidates the session. | `tests/security/test_logout_navigation.py`, `tests/security/test_production_entrypoint_reconciliation.py` | **PASS** — missing CSRF was denied; protected access after logout was denied. |
| Real localhost HTTP journey. | `tests/auth/test_http_v3.py::test_canonical_wsgi_http_v3_journey`; captured traceback in the focused run log | **BLOCKED** — `PermissionError: [WinError 10013]` at `sock.connect()` for `GET /login`; request never reached Flask. Needs an authorized runner that permits loopback to an unused `127.0.0.1:5000`. |
| Broader regression suite. | Final captured broad run; exact node IDs and evidence in [`SYNTHETIC_ANALYST_MVP_FAILURE_CLASSIFICATION.md`](SYNTHETIC_ANALYST_MVP_FAILURE_CLASSIFICATION.md) | **NOT VERIFIED** — 3,079 passed, 30 failed, 58 errors, 6 skipped, 10 deselected (exit 1). The 87 clone setup cases and one hard-link case need fresh execution on a capable authorized runner; prior classification is not proof they pass there. |
| Existing GitHub Actions full-suite run for the checkpoint commit. | [Tests run 38594149280](https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA/actions/runs/38594149280); [security run 38594149331](https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA/actions/runs/38594149331) | **PASS — merge-ref only** — tests job completed on Ubuntu 24.04 with 3,175 passed and 12 skipped; it checked out merge commit `f3ccc3da7581d0889eede4e3ff1172558773510c` (expected HEAD merged into `e98ecc9b84ef7346ea5e5415ec772ccec9caf8c6`). This does not validate the dirty local modifications or a Windows runner. |
| Authorized Windows runner validation of the focused and broad selections, including localhost HTTP. | [`SYNTHETIC_ANALYST_MVP_WINDOWS_RUNNER_HANDOFF.md`](SYNTHETIC_ANALYST_MVP_WINDOWS_RUNNER_HANDOFF.md) | **NOT VERIFIED** — no separate authorized runner was available in this session; runbook prepared, execution pending. |

The local focused run covered the analyst demonstration, registration/security,
MFA, audit, pilot-boundary, and logout suites: **87 passed, 1 blocked**. The
captured output and JUnit report are in the isolated diagnostic directory
recorded in the failure-classification document; they are not repository
artifacts. Python syntax compilation and `git diff --check` passed (Git emitted
only the existing signup-template line-ending normalization warning).

## Local synthetic demonstration

Use the repository's existing isolated Python environment and disposable local
SQLite database. Do not use customer data or credentials from any shared
environment.

1. Set `SENTINEL_DNA_ENV=testing`, `SENTINEL_DNA_DEMO_DATA=1`, and
   `SENTINEL_DNA_DB_PATH` to a new disposable local path. The application
   entrypoint is `wsgi.application`.
2. Start the app only on a local development interface. Open `/signup` and
   complete email-code verification, CSRF-protected registration, and MFA if
   the active policy requires it. No default account or password exists.
3. Sign in and open `/workspace` or `/workspace/`. Confirm that the page shows
   the synthetic PowerShell case for the authenticated tenant. The two paths
   must have the same authorization behavior.
4. Open the case, start the investigation, and inspect its persisted execution
   status, evidence references, provenance, uncertainty, confidence, and
   advisory report. A failed or unavailable execution must remain visibly
   failed/unavailable; it must not be presented as a successful result.
5. Submit analyst feedback with the page's CSRF token. Confirm that the saved
   feedback is attributed to the authenticated analyst and tenant. Sign out
   through the CSRF-protected control.
6. Repeat with `SENTINEL_DNA_DEMO_DATA=0`; the queue should show its honest
   empty state and should not create the sample case. In production the default
   is off unless an operator explicitly configures the setting.

The repeatable automated demonstration was executed with Flask's test client,
test email provider, and isolated SQLite fixtures. It verified signup/sign-in,
both workspace paths, tenant-scoped case creation, canonical coordinator
execution, persisted execution/evidence references, advisory report review,
feedback attributed to the authenticated analyst and tenant, cross-tenant
denial, and CSRF-protected sign-out/session invalidation. The separate live
localhost HTTP journey remains **BLOCKED** by the Windows socket restriction
above; it is not counted as an application pass. A manual browser session may
require configured local email/SMS providers and MFA policy. Do not expose a
development server to a network.

## Gate readiness decision

| Gate | Decision | Evidence / remaining requirement |
|---|---|---|
| Local synthetic MVP functionality | **READY** | The test-client workflow verified the synthetic case, canonical execution, evidence/report, feedback attribution, tenant denials, and sign-out. |
| Focused automated regression validation | **BLOCKED** | 87 passed; the live HTTP test was denied before Flask. Run the documented selection on the authorized Windows runner. |
| Real localhost HTTP validation | **BLOCKED** | Needs loopback permission and an unused port 5000 on that runner. |
| Broader regression validation | **BLOCKED** | 87 tests stopped during Git/MSYS fixture setup and one report-writer test hit hard-link denial; fresh runner evidence is required. |
| Controlled external analyst evaluation readiness | **NOT READY** | No external analyst authorization, evaluation approval, or analyst acceptance has been established. |
| Independent trust/custody verification | **NOT VERIFIED** | Independent custody evidence and identity reconciliation have not been performed for this checkpoint. |
| Production/release authorization | **NOT READY** | No release authorization or staging/production validation is claimed. |

These gates are separate. Local synthetic workflow readiness does not authorize
external evaluation or a release.

## Separate release gates

Real analyst evaluation, external validation, PostgreSQL migration evidence,
container health, TLS/edge controls, backup/restore, monitoring, and release
approval remain separate gates listed in
[`SOC_ANALYST_PILOT_READINESS.md`](../release/SOC_ANALYST_PILOT_READINESS.md).
No staging or production validation is claimed here.
