# Live synthetic authentication validation

This suite validates pre-provisioned synthetic pilot identities through the
real staging HTTPS edge. It is validation infrastructure only. It is not an
external analyst account, Gate 5 custody evidence, release authority, or
production authorization.

## Safety contract

Run only against a separately controlled, disposable staging runtime. The
suite refuses to run unless all of the following are true:

- `SENTINEL_DNA_LIVE_AUTH_ENABLE=1` is explicitly set.
- `SENTINEL_DNA_LIVE_AUTH_ENVIRONMENT=staging`.
- `SENTINEL_DNA_LIVE_AUTH_SCOPE=disposable_synthetic`.
- `SENTINEL_DNA_LIVE_AUTH_RUN_ID` starts with `live-synthetic-`.
- The target is exactly `https://127.0.0.1:18443`.
- URL userinfo, query strings, fragments, paths, alternate hosts, schemes, and
  ports are rejected.
- The identity, tenant, and actor markers are synthetic.
- Credentials and the TOTP seed are supplied at runtime only.
- TLS verification remains enabled. `-k`, `verify=False`, and HTTP fallback
  are not supported.

The suite never creates or deletes users, tenants, passwords, TOTP seeds,
provisioning URIs, or bootstrap endpoints. It never reads or prints cookies,
tokens, credentials, or response bodies containing sensitive data. Plain
`pytest` never contacts live staging. Live read-only checks require only the
explicit live-auth opt-in; state-mutating checks additionally require
`SENTINEL_DNA_LIVE_AUTH_ALLOW_STATE_MUTATION=1`, per-test disposable identity
credentials, and the exact reviewed reset contract
`reviewed_external_teardown_v1`.

## Runtime variables

Required variables are:

```text
SENTINEL_DNA_LIVE_AUTH_ENABLE=1
SENTINEL_DNA_LIVE_AUTH_BASE_URL=https://127.0.0.1:18443
SENTINEL_DNA_LIVE_AUTH_ENVIRONMENT=staging
SENTINEL_DNA_LIVE_AUTH_SCOPE=disposable_synthetic
SENTINEL_DNA_LIVE_AUTH_RUN_ID=live-synthetic-<run-id>
SENTINEL_DNA_LIVE_AUTH_USERNAME=<pre-provisioned synthetic username>
SENTINEL_DNA_LIVE_AUTH_PASSWORD=<runtime secret>
SENTINEL_DNA_LIVE_AUTH_TOTP_SECRET=<runtime secret>
SENTINEL_DNA_LIVE_AUTH_EXPECTED_USER_ID=<positive numeric user id>
SENTINEL_DNA_LIVE_AUTH_EXPECTED_TENANT_ID=synthetic-<tenant>
SENTINEL_DNA_LIVE_AUTH_EXPECTED_ACTOR_ID=synthetic-<actor>
```

`SENTINEL_DNA_LIVE_AUTH_CA_BUNDLE` may point to an existing trusted CA bundle.
It must not be used to bypass verification. No value is written to the
repository.

Mutating checks require four separate pre-provisioned disposable cases. Each
case uses the same fields with the case prefix shown below:

```text
SENTINEL_DNA_LIVE_AUTH_DISPOSABLE_RESET_CONTRACT=reviewed_external_teardown_v1
SENTINEL_DNA_LIVE_AUTH_CASE_<VALID_TOTP|REPLAY|CONCURRENT|LOGOUT>_RUN_ID=live-synthetic-<case-run-id>
SENTINEL_DNA_LIVE_AUTH_CASE_<VALID_TOTP|REPLAY|CONCURRENT|LOGOUT>_USERNAME=...
SENTINEL_DNA_LIVE_AUTH_CASE_<VALID_TOTP|REPLAY|CONCURRENT|LOGOUT>_PASSWORD=...
SENTINEL_DNA_LIVE_AUTH_CASE_<VALID_TOTP|REPLAY|CONCURRENT|LOGOUT>_TOTP_SECRET=...
SENTINEL_DNA_LIVE_AUTH_CASE_<VALID_TOTP|REPLAY|CONCURRENT|LOGOUT>_EXPECTED_USER_ID=...
SENTINEL_DNA_LIVE_AUTH_CASE_<VALID_TOTP|REPLAY|CONCURRENT|LOGOUT>_EXPECTED_TENANT_ID=synthetic-...
SENTINEL_DNA_LIVE_AUTH_CASE_<VALID_TOTP|REPLAY|CONCURRENT|LOGOUT>_EXPECTED_ACTOR_ID=synthetic-...
```

The harness never provisions or resets these cases. The reviewed disposable
runtime owner must tear down or reset the case identities, MFA enrollment,
durable counters, tenants, and authorizations after the run. The harness
revokes its own tracked MFA sessions by logging out in an exception-safe
finalizer; cleanup failure fails the test. If this contract is not present,
live mutating validation refuses to run.

## Coverage and limits

The suite uses `requests.Session` and real HTTPS requests, not Flask's test
client. It covers live readiness, password-only MFA blocking, pre-provisioned
TOTP verification, server-side MFA access, replay handling, concurrent reuse,
logout invalidation, forged client-state rejection, and analyst-role binding.
Successful protected access is checked against the configured synthetic user,
analyst actor, tenant, and role identifiers.

Session-version changes, recovery OTP separation, cross-user enrollment
inspection, cross-tenant access, and privileged provisioning require additional
reviewed live fixtures and remain `NOT COVERED LIVE`. They remain covered only
by in-process tests until such fixtures exist. The suite fails closed rather
than creating identities or guessing deployment values.

The harness establishes environment classification and the configured
synthetic test identity. It does not inspect the full database or prove that
all database contents are synthetic-only:

`SYNTHETIC-ONLY DATABASE CONTENTS REQUIRE INDEPENDENT VALIDATION`

Run with:

```text
python -m pytest -m live_auth tests/integration/test_live_synthetic_auth.py -q
```

An unconfigured run is skipped by design. An explicitly enabled run with
missing or unsafe guards fails closed. The output is sanitized test status only.
Read-only and mutating live evidence are distinct from in-process test
evidence; neither establishes Gate 5 custody or release authority.

Because replay protection is durable, each mutating check has its own
pre-provisioned identity and TOTP counter. The external disposable runtime
must reset or remove all case state after each invocation. The suite does not
reset or mutate provisioning state itself.

This suite must never run against production, Gate 5, the frozen evaluation
runtime, or the external analyst identity.
