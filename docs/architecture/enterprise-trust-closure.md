# Sentinel DNA Enterprise Trust Closure

Trust closure is the post-certification security hardening and deployment
readiness assessment. It packages the previous enterprise certification,
reviews credential boundaries, checks release evidence hygiene, and records
production blockers without deploying or changing investigation behavior.

```text
Previous certification + proof artifacts
                 |
        credential/security review
                 |
   release hygiene + deployment readiness
                 |
       EnterpriseTrustClosureRunner
                 |
   passed controls + risks + release gates
                 |
       immutable trust closure report
```

## Security closure

OTP service secrets are now required arguments. Production routes explicitly
pass `current_app.secret_key`; omitted direct service calls fail at the
boundary instead of using a development-only fallback. Production runtime
configuration continues to reject short or placeholder secrets, insecure
cookies, debug mode, and unusable database paths.

The closure assessment also consumes certification evidence for tenant
isolation, authorization boundaries, fail-closed behavior, audit integrity,
append-only evidence, provenance, and advisory memory boundaries.

## Release hygiene

The report verifies artifact presence, evidence digests, append-only report
writers, replay preservation, and release-manifest prerequisites. The release
manifest intentionally remains blocked when the repository worktree is dirty;
this is a release safety gate, not a reason to delete evidence artifacts.

## Deployment readiness

The assessment distinguishes repository evidence from deployment evidence. It
records whether production configuration validation, migrations, PostgreSQL
rehearsal, backup/restore, monitoring, and operational ownership are proven.
No PostgreSQL deployment or backup operation is performed by this task.

## Run

```text
python scripts/generate_enterprise_trust_report.py --generated-at 2026-08-25T00:00:00+00:00 --output artifacts/enterprise-trust-closure-2026-08-25.json
```

The CLI runs the assessment twice and requires identical replay digests. The
report is append-only and refuses overwrite. It contains previous
certification evidence, hardening findings, remaining risks, production
blockers, and recommended release gates.
