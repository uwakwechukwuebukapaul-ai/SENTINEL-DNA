# Gate 4 external dependency-closure evidence — 2026-09-02

## Decision

`GATE 4 = BLOCKED_WITH_REASON`

This package records the final locally provable state. It does not treat
structural browser checks as staging reachability or authentication evidence.
No custody artifact, credential, token, cookie, authorization header, or
authentication response is included.

## Evidence capture

| Item | Result |
| --- | --- |
| Branch | `gate4-controlled-analyst-pilot` |
| Reviewed checkout commit | `c34a0707d2ef7a51e2cf9d90ccc933adaec300dd` |
| Reviewed checkout tree | `c1c0ebd345248206d234cee3033fcf800690d85c` |
| Working-tree policy | Unrelated existing modifications preserved |
| `git diff --check` | PASS |

## Gate 4 evidence matrix

| Gate | Requirement | Evidence | Status | Blocking dependency |
| --- | --- | --- | --- | --- |
| Provider | Reviewed provider | `node --test tests/staging/*.test.mjs`; structural verifier | PASS | None locally |
| Runtime | Trusted runtime contract | Structural verifier; runtime tests | PASS | Custody artifact still requires reconciliation |
| Origin | Exact certified origin enforcement | Origin contract tests and verifier | PASS | Live endpoint not reachable |
| Browser | Required browser/tab contract | Structural verifier; 66 Node tests | PASS | None locally |
| Cleanup | Deterministic lifecycle | Cleanup regression and bounded verifier exit | PASS | None locally |
| TCP | `127.0.0.1:18443` reachable | `Test-NetConnection` | BLOCKED | Controlled staging host/edge |
| TLS | Valid staging TLS identity | No live listener; staging TLS files external | BLOCKED | Approved TLS material and edge |
| nginx | Certified routing to private app | Static nginx/Compose contract only | BLOCKED | Docker/staging runtime |
| Ready | `/ready` through certified origin | Certified-origin curl failed | BLOCKED | Staging deployment |
| Auth bridge | Real reviewed bridge | Environment unset; no bridge artifact | BLOCKED | Operator-owned reviewed bridge |
| Session | Real authentication/session | No auth attempt made | BLOCKED | Bridge plus reachable staging |
| Custody | Runtime/manifest reconciliation | External manifest integrity and runtime contract failure | BLOCKED | Release-custody reconciliation |
| Regression | Full suite | Full suite stopped during PostgreSQL-backed collection | BLOCKED | PostgreSQL/Docker |
| Human validation | Analyst review | No live pilot started | NOT STARTED | All preceding gates |

## Controlled deployment topology

The checked-in controlled staging package preserves this path:

```text
trusted browser
  -> sentinel-dna-staging
  -> 127.0.0.1:18443
  -> edge:443 TLS
  -> app:5000 (private)
  -> PostgreSQL/Redis on staging_internal
```

Static contract evidence confirms:

- `SENTINEL_DNA_BASE_URL=https://sentinel-dna-staging:18443`.
- The staging edge binds only `127.0.0.1:18443:443`; the pilot override
  changes the reviewed app and migration images without adding another host
  publication.
- The application exposes only private port `5000`.
- PostgreSQL and Redis have no host ports.
- `staging_internal` is internal.
- Nginx uses the staging certificate paths and proxies to `app:5000`.
- Application and database credentials use Docker-secret file paths.
- No HTTP origin or localhost origin replaces the certified origin.

Live infrastructure evidence:

| Check | Result |
| --- | --- |
| Docker Engine / Compose | `DOCKER_RUNTIME_UNAVAILABLE` (command unavailable) |
| Podman | Unavailable |
| `sentinel-dna-staging` DNS | Resolves to `127.0.0.1` |
| TCP `127.0.0.1:18443` | FAIL; connection refused |
| TCP `127.0.0.1:5432` | FAIL; no PostgreSQL listener |
| TCP `127.0.0.1:6379` | FAIL; no Redis listener |
| Certified-origin TLS | NOT PROVEN; no listener |
| Certified-origin `/ready` | NOT PROVEN; connection failed |
| `https://localhost/ready` | FAIL; Schannel `SEC_E_NO_CREDENTIALS` |

The root/local Compose stack is not evidence for controlled staging. Its
historical host-facing edge is port 443 with the localhost nginx certificate;
it is not substituted for the certified staging edge.

## Trusted-browser audit

The trusted-browser implementation enforces the following locally:

- exact origin `https://sentinel-dna-staging:18443`;
- certified-origin-only navigation;
- selector strings at the authentication boundary;
- rejection of credential-shaped request fields;
- rejection of fixture/test/mock approved-runtime paths;
- bounded provider, runtime, browser, navigation, auth, application, and close operations;
- safe allowlisted diagnostic categories only;
- deterministic tab, browser, and runtime cleanup;
- fail-closed behavior when `browserAuth` is absent.

Current structural verifier result:

```json
{
  "status": "BLOCKED_WITH_REASON",
  "checks": {
    "provider": "PASS",
    "runtime": "PASS",
    "origin": "PASS",
    "browser_contract": "PASS",
    "browser_auth": "FAIL"
  },
  "failure_category": "TB_AUTH_CAPABILITY_MISSING"
}
```

## Authentication bridge classification

No repository implementation exports a real operator authentication bridge
with `requestBrowserAuth`. The discovered implementations are classified as:

| Location/type | Classification | Gate meaning |
| --- | --- | --- |
| Approved runtime bridge loader | Runtime boundary, not an auth bridge | Requires external reviewed module |
| `tests/staging/fixtures/trusted-playwright-adapter-stub.mjs` | FIXTURE/STUB | Never production evidence |
| `deployment/staging/simulation/` authentication capability | TEST/SIMULATION | Explicitly non-production |
| Inline capabilities in `tests/staging/` | TEST/MOCK | Test-only |
| Documentation/configuration references | UNRELATED contract references | No implementation |

`SENTINEL_DNA_BROWSER_AUTH_BRIDGE` is unset. Authentication therefore remains
`BLOCKED_WITH_REASON` with `TB_AUTH_CAPABILITY_MISSING`. No bridge was created
or substituted.

The future bridge must be an operator-owned local module supplied outside the
repository, export `requestBrowserAuth`, accept only the certified origin and
reviewed selector descriptors, use bounded execution, keep credential entry
outside Sentinel DNA, return only a non-secret protocol status, and be covered
by independent custody/ownership approval.

## Custody reconciliation record

| Artifact | Path | SHA-256 / result |
| --- | --- | --- |
| Repository-local runtime | `deployment/staging/scripts/trusted_browser_service/providers/approved-playwright-runtime.mjs` | `sha256:8f4e5b19fc9d4f6b8b917bf23080446b4d5465e0b531a472a11e9bd0e2cb4286` |
| Repository manifest | `pilot-evidence/gate4/trusted-browser-activation-manifest.json` | Declared runtime `sha256:0154f8ad7473f4f132c3cf0d2788d22234b82153c9fd5fb2965eb798d8074fe2`; unchanged |
| External runtime | `C:\sentinel-dna-gate4-custody\approved-playwright-runtime.mjs` | `sha256:42530c78b4d15f591d090d4da71ee2485dd20247104fdb2464705879a071831b` |
| External manifest | `C:\sentinel-dna-gate4-custody\trusted-browser-activation-manifest.json` | File SHA-256 `sha256:2cfff7565eeaa003c434bb588678fef179df82ce522cdd935801f382dc0a4002` |
| External manifest declared runtime | Same external manifest | Matches external runtime digest |
| External manifest integrity | Same external manifest | FAIL: stored `2741ecc48a74bc89904b32c82cc6adda73f20dd6103b40b09d4b400f94eee3a9`; computed `0af0998f32745c62f328061dcf6f8295bb8c74726c0ab55350f7a03d927fe921` |
| External runtime contract | Same external runtime | FAIL: returns a raw browser; required `browsers.tabs.new()` is absent |
| External image binding | Manifest image identity | `sha256:f065ce859b6b349d5ee9a159768197ee773e45ab92295a6f298fd862a9cc286e` |

Custody result: `CUSTODY_RECONCILIATION_REQUIRED`.

Required independent approval:

1. Release custody must issue an integrity-valid manifest whose canonical hash
   matches its contents and whose origin remains exact.
2. Custody must approve a runtime implementing the complete restricted browser
   contract, or supply a separately approved compatible runtime package.
3. The runtime SHA-256, image digest, provider identity, approval reference,
   and artifact provenance must be reconciled without editing evidence locally.
4. The reviewed authentication bridge must have a separate operator approval
   and ownership record.

The external artifact is not suitable for Gate 4 promotion in its current
state.

## Operator handoff

Perform these actions only on the approved controlled staging host:

1. Provision Docker Engine and Compose; verify `docker version`, `docker info`,
   and `docker compose version`.
2. Provision disposable PostgreSQL and Redis on the private staging network.
3. Provision the approved staging TLS certificate, full chain, key, and CA
   outside the repository; verify SAN coverage for `sentinel-dna-staging`.
4. Configure `sentinel-dna-staging` through approved DNS/hosts management; do
   not silently edit workstation system configuration.
5. Supply an integrity-valid custody manifest and the matching approved runtime.
6. Supply the reviewed operator authentication bridge through
   `SENTINEL_DNA_BROWSER_AUTH_BRIDGE`; do not use a test, fixture, mock, or stub.
7. Inject application/database secrets only through the approved external
   Docker-secret mechanism.
8. Set the exact origin `SENTINEL_DNA_BASE_URL=https://sentinel-dna-staging:18443`.
9. Run the controlled deployment script from a clean reviewed checkout.
10. Verify the exact loopback binding `127.0.0.1:18443->443/tcp`.
11. Verify TCP reachability from the same execution environment as the trusted
    browser.
12. Verify the TLS chain and hostname identity with the approved CA; `-k` is
    not proof of certificate validity.
13. Verify nginx routing and `/ready` through the certified origin.
14. Run the trusted-browser verifier and readiness checker.
15. Run the real browser authentication flow through the reviewed bridge.
16. Verify the authenticated session using non-secret evidence only.
17. Verify tenant isolation, CSRF, audit, provenance, and controlled pilot
    behavior.
18. Close tabs, browser, and runtime; confirm bounded completion.
19. Capture immutable, secret-free evidence and reconcile it with custody.
20. Run the full regression suite against the available staging dependencies.
21. Obtain independent human release approval before analyst access.

No analyst link is released by this package.
