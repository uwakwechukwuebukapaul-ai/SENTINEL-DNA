# Controlled Analyst Pilot Activation Simulation

**NON-PRODUCTION ONLY**

This package demonstrates the operator activation lifecycle without connecting
to the reviewed external Playwright/RPC runtime, creating a network listener,
authenticating, invoking `browserAuth`, creating an account, or authorizing a
pilot. It does not change or register a production provider.

The simulation uses:

- an in-memory synthetic external runtime registration;
- an exact-origin synthetic endpoint model with no listener;
- a generated non-secret activation manifest with an ephemeral detached
  signature bundle whose private key is never written;
- synthetic tenant-isolation and audit evidence fixtures;
- the checked-in `codex-app` runtime interface and readiness checks, supplied
  only with simulation-scoped inputs;
- a separate report status, `SIMULATION_READY_FOR_ANALYST_PILOT`, which is
  never accepted by the production pilot runner.

## Run the demonstration

The explicit flag and environment guard are both required:

```powershell
$env:SENTINEL_DNA_SIMULATION_MODE = "1"
node .\deployment\staging\simulation\simulate_controlled_analyst_pilot_activation.mjs --non-production-simulation
```

The output contains both phases:

```text
initial phase: BLOCKED_WITH_REASON
simulation phase: SIMULATION_READY_FOR_ANALYST_PILOT
```

The report is written below `deployment/staging/simulation/output/` in a
run-specific directory. It contains no absolute paths, secrets, credentials,
cookies, tokens, or browser sessions. The output is not pilot evidence and
must not be copied into `pilot-evidence/`.

Generate only the synthetic manifest bundle:

```powershell
$env:SENTINEL_DNA_SIMULATION_MODE = "1"
node .\deployment\staging\simulation\generate_simulation_activation_manifest.mjs --non-production-simulation
```

The manifest and report formats are described by:

- `CONTROLLED_ANALYST_PILOT_SIMULATION_REPORT.schema.json`;
- `../CONTROLLED_ANALYST_PILOT_READINESS_REPORT.schema.json` for the separate
  production readiness report.

## Production separation

The simulation package is not imported by:

- `run_controlled_analyst_pilot.mjs`;
- `trusted_browser_execution_adapter.mjs`;
- `trusted_browser_service/browser-client.mjs`;
- `check_controlled_pilot_activation.ps1`.

The production activation gate continues to require the real external
reviewed runtime, real trusted RPC bridge, real activation manifest, certified
origin reachability, deployment security assertions, and human approval. A
simulation-ready result does not satisfy those requirements.

## Security review notes

- The simulation runtime is an in-memory contract fixture, not a production
  provider and not a fallback.
- The synthetic endpoint performs exact string origin matching and makes no
  network request or public listener.
- The simulated provider accepts only `environment: "codex-app"`, exposes the
  same required browser/tab surfaces, and is contract-checked before the
  simulation report is marked ready.
- `browserAuth` is discovered but never invoked; no credential value exists in
  the simulation.
- The manifest hash uses the repository's canonical SHA-256 helper. The
  detached signature uses a key generated in memory for demonstration; only
  the public key and signature are written, and neither is trusted by
  production.
- Tenant and audit fixtures contain synthetic references only and are not
  evidence of a deployed tenant boundary or audit service.
- The report sets `simulation_only: true` and
  `production_authorization: false` and uses a status that the production gate
  does not accept.
- Missing simulation guard, invalid output custody, contract failure, invalid
  origin, or fixture failure returns `BLOCKED_WITH_REASON` with a safe
  diagnostic code.

## Real activation remains separate

Use the real operator sequence only from the approved environment after the
external runtime is installed and reviewed:

```powershell
.\deployment\staging\scripts\configure_trusted_browser_provider.ps1 -DryRun
node .\deployment\staging\scripts\verify_trusted_browser_provider.mjs
.\deployment\staging\scripts\check_controlled_pilot_activation.ps1 -Json -DryRun
```

Only `READY_FOR_ANALYST_PILOT`, followed by human approval, can advance real
activation. `SIMULATION_READY_FOR_ANALYST_PILOT` is never sufficient.
