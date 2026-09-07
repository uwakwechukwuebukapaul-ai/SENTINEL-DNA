# Gate 5 Approved Artifact Digest Record

## Record metadata

Project: Sentinel DNA  
Gate: Gate 5 Controlled Analyst Pilot  
Record timestamp: 2026-09-07T20:06:55.1294813Z  
Performed by: repository inspection and static configuration review; no human analyst action

Observed repository HEAD: e4716c9c7543f9fc2919bbd92cc833b570310df1  
Observed repository tree: 4c78a1a8906290ef720e9102b87e83e1325b60f6  
Branch: gate5-controlled-analyst-pilot-preparation

Authorized release-candidate commit: ca1d61467f4520f52a986e5fa1a8c13d499d2229  
Authorized release-candidate tree: 0c34089a3781c172c3711094b870f61964902d9

## Artifact identity status

Status: BLOCKED_PENDING_EXTERNAL_ARTIFACT_DIGEST

Image identity: NOT PROVIDED  
Immutable image digest: NOT PROVIDED  
Build source: Sentinel DNA repository candidate above; external image build or
registry record was not available for inspection.  
Build commit SHA: ca1d61467f4520f52a986e5fa1a8c13d499d2229  
Build tree SHA: 0c34089a3781c172c3711094b870f61964902d9

No image digest was generated or inferred. The repository does not contain
proof of a built image, registry push, or deployment image resolution.

## Immutable reconciliation procedure

The authorized operator must, outside Git and through approved custody:

1. Build or retrieve the candidate image from the exact candidate commit and
   tree above.
2. Record the immutable image reference and SHA-256 digest.
3. Record the external build provenance, UTC build timestamp, registry/custody
   reference, and image config digest without recording credentials.
4. Set `SENTINEL_DNA_IMAGE_DIGEST` and the staged image references from external
   injection only.
5. Reconcile the digest against the activation manifest, Compose deployment
   inspection, and runtime image identity.

Required fields remain pending: image identity, digest, build source, exact UTC
build timestamp, and external custody reference.

This record establishes a fail-closed workflow only. It does not authorize
deployment or prove successful production operation.
