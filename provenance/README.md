# Artifact and image provenance milestone

This directory contains the machine-readable, non-signing provenance
observation manifest for the exact staging artifacts inspected by the
workspace. It is separate from Gate 5 activation, custody acceptance, and
historical evidence.

`artifact-image-provenance-manifest.json` is canonicalized before its
`manifest_sha256` is calculated. `LOCAL_OBSERVED` and `LOCAL_VERIFIED` are
local observations only; they cannot satisfy external or independent
certification. A digest mismatch, missing bridge, incomplete dependency
closure, mutable image reference, missing attestation, expired evidence, or
caller-supplied identity remains fail-closed.
## Historical Gate4 records

The following records are historical snapshots and are not current release,
custody, or live-deployment evidence:

- `gate4-artifact-manifest-1.json` records an earlier source commit/tree.
- `gate4-final-readiness.json` records an earlier readiness observation only.
- `gate4-final-runtime-state.txt` records an earlier runtime snapshot only.
- `pilot-evidence/gate4/trusted-browser-activation-manifest.json` is a
  historical activation fixture, not current approval or custody.

No record in this workspace represents the dirty worktree as an immutable
release boundary. A current provenance record requires a later approved
release commit, immutable artifacts, and independently verified custody.
