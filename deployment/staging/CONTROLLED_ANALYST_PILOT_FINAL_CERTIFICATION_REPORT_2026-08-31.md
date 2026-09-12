# Controlled analyst pilot final certification report — 2026-08-31

## Decision

`BLOCKED_WITH_REASON`.

The private staging boundary is verified, but the authenticated pilot could
not start because the approved trusted browser service was unavailable. No
tenant, analyst account, credential, or analyst URL was created or issued.

## Exact manual browser procedure when the approved browser is available

1. Open `https://sentinel-dna-staging:18443/` in the approved browser. Confirm
   the certificate and hostname before interacting with the page.
2. Inspect the visible login form. Use the browser's secure authentication
   handoff for the manager username and password. Never enter credentials in a
   terminal, chat, runner argument, screenshot, or evidence file.
3. Confirm `/api/auth/me` returns HTTP 200 and a manager role of `admin` or
   `soc_manager`. Confirm cookies are secure and scoped to the staging origin.
4. In the same-origin browser context, submit a manager-only provisioning
   request without CSRF. Confirm HTTP 403 and no state change. Then obtain the
   valid CSRF token only inside the browser context.
5. With explicit manager approval, submit exactly one provisioning request
   using only synthetic identity values and reviewed approved scenario IDs.
   Verify exactly one tenant and exactly one analyst exist. Confirm the
   analyst has only role `analyst`, only that tenant, bounded authorization,
   and bounded activation expiry. Do not record the activation token.
6. Transfer activation out-of-band. In the analyst browser session, confirm
   `/api/auth/me` shows the expected analyst role and tenant, and confirm the
   current pilot authorization is active and unexpired.
7. Perform one non-destructive synthetic investigation with valid CSRF. Verify
   the canonical workflow completes, the analyst sees only the assigned
   tenant, and audit and provenance references are tied to the action and
   tenant.
8. Verify the analyst conclusion and AI recommendation are separate, the AI
   result is advisory-only, and an explicit human decision is required.
9. Using only reviewed safe denial paths, verify cross-tenant, admin
   escalation, database, shell/container, and destructive requests return the
   documented denial without state mutation.
10. Revoke the pilot authorization, deactivate the analyst, invalidate active
    sessions, and verify login renewal, workspace reads, investigation reads,
    and feedback/action writes fail closed.
11. Create a new unique append-only evidence file containing only non-secret
    identifiers, statuses, UTC timestamps, audit/provenance references, and
    hashes. Mark no unobserved item `PASS`.
12. Run the unchanged validator against that evidence file. Only an exact
    `READY_FOR_CONTROLLED_ANALYST_PILOT` result permits the human release
    authority to prepare private analyst access instructions.

## Current evidence

The current attempt is recorded in
`pilot-evidence/controlled-analyst-pilot-final-manual-attempt-20260831T200208Z.json`.
It is intentionally incomplete and must not be treated as certification.
