# Phase 1 security review

## Trust boundary

The authority is separate from the Flask process, Sentinel DNA application
database, Docker, browser runtime, and pilot state. Its default state root is
outside the repository. The Phase 1 trust root and signing key are staging-only
software keys. No production key is generated.

## Fail-closed controls

- Exact regular-file checks reject missing files and symlinks.
- Runtime, lockfile, bridge, and dependency metadata are hashed at request time
  and rehashed immediately before approval to detect TOCTOU replacement.
- Image digests require an external verification reference and are explicitly
  labeled `EXTERNAL_REQUIRED`; local code does not pretend to inspect images.
- The certified origin is a fixed policy constant and cannot be supplied as an
  arbitrary origin.
- Schema, environment, approval, expiration, canonical hash, signature, key
  certificate, key status, and revocation are verified before a manifest passes.
- SQLite triggers reject application-level UPDATE and DELETE on custody tables.
- Evidence and manifest exports use exclusive creation.
- Requester and approver identities must differ.
- Staging key creation is the only environment supported by Phase 1.

## Known Phase 1 limits

- A software staging private key is not equivalent to an HSM/KMS-backed
  production root. The signer interface is intentionally replaceable.
- SQLite hash chaining detects normal application-level tampering but is not a
  WORM store. Operational deployment must protect the state directory and
  export signed checkpoints to independent custody.
- The authority creates a `STAGING_LOCAL_APPROVED` manifest. This is not
  external approval and must not be used to claim Gate 5 certification.
- Image verification remains external and must be independently established
  before any production or Gate 5 promotion.
- The current Gate 5 schema-1 validators are unchanged; Phase 1 is shadow mode.

## Review items

Threats considered: key theft, replay, artifact replacement, TOCTOU, database
tampering, evidence deletion, path traversal, symlinks, arbitrary file hashing,
malformed manifests, signature confusion, algorithm downgrade, cross-environment
approval, revoked/expired keys, and secret leakage.

Production promotion requires a separate review of OS ACLs, backup/recovery,
two-person approval, key ceremony, independent evidence storage, and a KMS/HSM
signer implementation.
