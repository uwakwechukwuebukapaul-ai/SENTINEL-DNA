# Non-Production Simulation Security Review

**Scope:** `deployment/staging/simulation/` only
**Classification:** demonstration fixture; not production evidence
**Decision:** approved for local operator training only

## Boundary review

- The simulation is not imported by the production pilot runner, execution
  adapter, trusted browser facade, provider boundary, or activation gate.
- It requires both `SENTINEL_DNA_SIMULATION_MODE=1` and
  `--non-production-simulation`; without both, it returns
  `BLOCKED_WITH_REASON`.
- `SIMULATION_READY_FOR_ANALYST_PILOT` is a simulation-only status and is not a
  valid production activation status.
- Real production activation continues to require the external reviewed
  Playwright/RPC runtime, trusted RPC bridge, activation manifest, certified
  origin, deployment controls, and human approval.

## Data and transport review

- No credentials, cookies, tokens, customer data, browser sessions, or private
  signing keys are present in the fixtures or reports.
- The synthetic endpoint is an in-memory exact-origin model; it creates no
  network listener and performs no HTTP/TLS operation.
- The simulated browserAuth capability is discovered but never invoked.
- No CDP, browser-debugging port, insecure launch flag, direct login, or
  alternate provider path is present.
- Simulation output rejects production evidence custody paths and is isolated
  below the simulation output directory.

## Integrity review

- The synthetic image identity is a SHA-256 digest of a non-production label,
  not a real deployment image digest.
- The activation manifest is validated with the repository's canonical
  manifest hash function.
- The detached signature demonstration generates an ephemeral Ed25519 key in
  memory, writes only its public key and signature, and verifies the signature
  before reporting success.
- The manifest/signature artifacts are not trusted by the production gate.

## Evidence review

- Tenant-isolation and audit fixtures contain synthetic references only.
- They demonstrate report shape and workflow, not a deployed tenant boundary or
  audit service.
- They must never be copied into `pilot-evidence/` or presented as analyst
  pilot evidence.
- Real customer pilot evidence must be captured and validated through the
  existing production evidence workflow and human approval gate.

## Failure review

The simulation remains fail-closed for missing mode guard, invalid output
location, invalid manifest/signature, invalid certified origin, invalid
browser contract, missing browserAuth, or invalid evidence fixture. Failures
emit safe categories only and never expose paths, secrets, or stack traces.
