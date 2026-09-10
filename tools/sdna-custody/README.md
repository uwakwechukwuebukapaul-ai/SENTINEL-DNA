# Sentinel DNA Artifact Custody Authority

This is a standalone, staging-only custody authority. It is intentionally
separate from the Flask application, browser runtime, Docker configuration,
and existing Gate 5 validators.

The authority creates signed schema-2.0 staging manifests and append-only
custody evidence. It does not make Gate 5 ready and does not replace the
external approval required by the current Gate 5 process.

## Safety boundary

- Default state is outside the repository at
  `C:\ProgramData\Sentinel-DNA\custody` on Windows or
  `/var/lib/sentinel-dna/custody` on POSIX.
- Private keys are stored only below the custody state root and are never
  exported in manifests, evidence, logs, or Docker configuration.
- Phase 1 creates only a staging root and staging signing key. Production key
  creation is rejected.
- Image digests are recorded as externally verified claims with an approval
  reference; this package cannot inspect a registry or running container.
- Evidence exports use exclusive creation and historical ledger rows are
  protected by SQLite triggers against UPDATE and DELETE.

## Development invocation

From this directory after installing the package:

```powershell
python -m pip install -e .
sdna-custody --help
```

Use `--state-root` with a temporary directory for tests or development. Do
not point it at the repository or at the healthy pilot's state.
