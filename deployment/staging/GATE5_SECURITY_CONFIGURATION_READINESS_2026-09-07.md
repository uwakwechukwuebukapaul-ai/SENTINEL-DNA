# Gate 5 Security Configuration Readiness

## Record metadata

Project: Sentinel DNA
Gate: Gate 5 Controlled Analyst Pilot
Status: BLOCKED_PENDING_EXTERNAL_SECRET_INJECTION
Record timestamp: 2026-09-07T20:13:52.4214721Z
Performed by: static Compose and validator inspection; no secrets were accessed

Candidate commit: ca1d61467f4520f52a986e5fa1a8c13d499d2229
Candidate tree: 0c34089a3781c172c3711094b870f61964902d9

## Required external configuration

The staging operator must inject, from approved external custody only:

- application secret key file;
- PostgreSQL password file and database connection configuration;
- trusted-browser service key, host, and port;
- approved app, edge, PostgreSQL, Redis, trusted-browser, and egress image
  references and immutable digests;
- certified origin and staging TLS directory containing certificate and key;
- activation manifest and approved runtime digest;
- egress gateway bind/port, policy file, policy digest, proxy endpoint, and
  gateway network;
- external provider/MFA configuration required by the approved authentication
  path.

Exact values, paths, credentials, and keys are NOT PROVIDED in this record and
must not be committed.

## Static security observations

| Control | Result | Basis |
|---|---|---|
| Debug disabled | PASS / CONFIGURED | Compose sets `FLASK_DEBUG=0`. |
| Secure cookies | PASS / CONFIGURED | Compose sets `SENTINEL_DNA_SECURE_COOKIES=1`. |
| Pilot access gate | PASS / CONFIGURED | Compose sets `SENTINEL_DNA_PILOT_ACCESS_REQUIRED=1`. |
| Tenant isolation | PASS / CONFIGURED | Compose sets `SENTINEL_DNA_TENANT_ISOLATION_ENABLED=1`. |
| Audit logging | PASS / CONFIGURED | Compose sets `SENTINEL_DNA_AUDIT_LOGGING_ENABLED=1`. |
| Secret custody | PASS / DESIGN | Secrets are external file mounts; values not observed. |
| Live secret injection | BLOCKED | No configured staging environment is available locally. |
| Live authentication/MFA | BLOCKED | Trusted provider and external identity are unavailable. |

Configuration flags are not runtime or analyst evidence. No secret was printed,
read, generated, or stored by this review.

## Boundary

Missing external security configuration stops the controlled pilot. It does not
justify defaults, bypasses, debug mode, weakened TLS, alternate origins, or
application-code changes.

## Status classification

READY: Required external-injection names and static fail-closed controls are
documented.

BLOCKED: Required external secret/configuration values and live provider
verification are absent.

OWNER ACTION REQUIRED: Security/operator owner must inject approved values
outside Git and run startup and authentication checks.

NOT MEASURED: Secret validity, live MFA/provider behavior, runtime encryption,
and deployed security controls.
