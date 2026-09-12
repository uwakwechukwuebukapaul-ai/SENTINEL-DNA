# Sentinel DNA SOC Analyst Pilot Readiness

**Validation date:** 2026-08-28  
**Target:** Ubuntu Linux, Docker Engine, PostgreSQL 16, Redis 7  
**Promotion status:** host-runtime gates remain open

## Architecture summary

The controlled pilot path is:

```
Nginx edge -> Gunicorn Flask app -> canonical tenant/identity authority
                                      -> PostgreSQL
                                      -> Redis
                                      -> AI Investigator V1/evidence projections
```

The authoritative database registry contains migrations 001 through 008.
Compose runs the one-shot `migration` service before the application; WSGI
import does not run migrations. The analyst workspace is tenant-scoped and
keeps AI findings advisory until an authenticated analyst submits a review.

The existing canonical append-only investigation feedback repository now also
captures `helpful_rating`, `confidence_rating`,
`estimated_time_saved`, and `analyst_comments`. These metrics are stored
in its existing `metadata_json` column for backward compatibility; tenant,
case, analyst, decision, feedback ID, and server-authored timestamp remain
canonical record fields. No second feedback store was added.

## Root cause addressed

The production runner previously registered only the normalized core schema.
Fresh PostgreSQL targets therefore lacked `schema_migrations` and canonical
authority tables. The remediation added the ordered 001-008 registry,
contiguous-version validation, transactional execution, and an explicit
migration service. The final pass also removed SQLite-only `rowid` ordering
from feedback reads; ordering is now `created_at, feedback_id`, portable to
PostgreSQL.

## Validation evidence

Registry inspection confirmed:

```
001_baseline
002_canonical_authority
003_identity_bindings
004_provider_tenant_trust
005_billing
006_crypto_intents
007_investigation_memory
008_organizational_cyber_memory
```

The runner contract confirms:

```
first run:  (1, 2, 3, 4, 5, 6, 7, 8)
second run: ()
```

Repository-side results:

```
python -m pytest -q tests/database tests/staging tests/intelligence/ioc
59 passed, 2 skipped

python -m pytest -q tests/identity
116 passed

python -m pytest -q tests/audit
16 passed

python -m pytest -q tests/intelligence/investigation/test_analyst_feedback_pilot.py tests/security/test_analyst_demo_workflow.py
8 passed

python -m pytest -q tests/dashboard/test_analyst_workspace_security.py tests/intelligence/command_center/test_feedback.py
6 passed
```

The two PostgreSQL integration tests were skipped because
`SENTINEL_DNA_TEST_POSTGRES_URL` was not configured. Docker was not installed
in this workspace, so image build, container health, and host SQL checks are
not claimed as locally executed evidence.

The queue presents case ID, severity, status, priority, affected asset count,
created/last-activity timestamps, and assigned analyst. The review view
presents alert source, timeline, entities, findings, reasoning, confidence,
uncertainty, evidence references, IOC reputation/enrichment, provenance,
ATT&CK mapping, execution/provider health, and analyst actions.

## Security controls

- Canonical tenant and identity resolution is required for the browser path.
- Investigation reads and writes use the existing authorization boundary.
- Feedback cannot supply tenant ID, analyst ID, feedback ID, or created time.
- Unknown feedback fields and incomplete pilot metrics are rejected.
- CSRF is required for the browser feedback form.
- Feedback is an append-only application record and is audited as
  `INVESTIGATION_FEEDBACK_RECORDED`; no update or delete API is exposed.
- Evidence is loaded from tenant-scoped repositories and provenance remains
  visible; unavailable providers are not represented as successful evidence.
- No default users, tenants, credentials, or administrator accounts are
  created by the migration or feedback workflow.
- Static review found no destructive operations in authoritative migrations.
- Existing HTTP-only, SameSite cookie controls remain configuration-driven.
- AI output remains advisory; review actions do not silently close cases or
  execute remediation.

## Ubuntu staging validation commands

Run from the reviewed checkout on `Sentinel-DNA-Staging`. Use a protected
environment file and never paste secrets into shell history.

```bash
cd ~/SENTINEL-DNA
export STAGING_ENV_FILE=/etc/sentinel-dna/staging.env
docker compose --env-file "$STAGING_ENV_FILE" -f deployment/staging/docker-compose.yml config
sh deployment/scripts/deploy.sh
# Set SENTINEL_DNA_FAVP_OPERATIONS_ENABLED=1 in the approved staging
# environment only when the FAVP schema and evidence custody are in scope.
docker compose --env-file "$STAGING_ENV_FILE" -f deployment/staging/docker-compose.yml run --rm --build migration
docker compose --env-file "$STAGING_ENV_FILE" -f deployment/staging/docker-compose.yml run --rm --build migration
```

Expected migration output:

```
database migrations applied: 1,2,3,4,5,6,7,8
database migrations applied: none
```

If FAVP staging is explicitly enabled, the expected first-run output includes
`1,2,3,4,5,6,7,8,9`; otherwise migration 9 remains disabled and the base
staging chain ends at 8.

Verify versions:

```bash
docker compose --env-file "$STAGING_ENV_FILE" -f deployment/staging/docker-compose.yml exec -T postgres psql -U sentinel -d sentinel_dna -c "SELECT version FROM schema_migrations ORDER BY version;"
```

Expected rows are 1 through 9. Verify required tables:

```bash
docker compose --env-file "$STAGING_ENV_FILE" -f deployment/staging/docker-compose.yml exec -T postgres psql -U sentinel -d sentinel_dna -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('schema_migrations','canonical_tenants','canonical_identities','canonical_memberships','canonical_identity_bindings','canonical_provider_tenant_trusts','billing_customers','crypto_payment_intents','investigation_memory','organizational_memory') ORDER BY table_name;"
```

Expected table names are all ten names in the query. Verify runtime state:

```bash
docker compose --env-file "$STAGING_ENV_FILE" -f deployment/staging/docker-compose.yml ps
curl --fail --silent --show-error https://staging.example.internal/health
curl --fail --silent --show-error https://staging.example.internal/ready
```

Expected state is PostgreSQL healthy, Redis healthy, migration exit code 0,
Sentinel DNA healthy, and Nginx running.

## Operational checklist

- [ ] Reviewed commit and image digest recorded.
- [ ] Protected staging env file and secret custody verified.
- [ ] Staging backup/snapshot and restore owner recorded.
- [ ] First and second migration outputs attached.
- [ ] Version/table SQL output attached.
- [ ] PostgreSQL, Redis, app, and Nginx health evidence attached.
- [ ] Authenticated analyst can load only the pilot tenant's queue/cases.
- [ ] Evidence references, provenance, and uncertainty are visible.
- [ ] Feedback submission and audit event verified.
- [ ] Inactive-user and cross-tenant denial verified.
- [ ] TLS, proxy headers, log redaction, monitoring, and retention owners named.
- [ ] Baseline analyst handling time and pilot acceptance criteria recorded.
- [ ] Independent release approval recorded before analyst access is issued.

## Known limitations and remaining pilot blockers

1. Docker and disposable PostgreSQL were unavailable here. Ubuntu deployment,
   health, migration logs, and SQL outputs remain release gates.
2. PostgreSQL integration tests require
   `SENTINEL_DNA_TEST_POSTGRES_URL`.
3. The checkout is dirty from the migration remediation and the local branch
   is `fix/auth-inactive-user-lookup`; release custody must reconcile this.
4. One controlled-deployment fixture requires a clean Ubuntu Git checkout
   because its historical blob cannot be materialized in this Windows copy.
5. TLS/edge, backup/restore, monitoring, log-retention, onboarding, and
   independent security approval remain pilot gates.
6. `estimated_time_saved` is an analyst estimate. A documented baseline must
   be collected before using it as pilot improvement evidence.

This document does not authorize production promotion or pilot access alone.
