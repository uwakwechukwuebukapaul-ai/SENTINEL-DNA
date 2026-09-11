# Signed manifest schema 2.0

The manifest payload is encoded as UTF-8 JSON with recursively sorted object
keys, compact separators, `ensure_ascii=false`, and no insignificant
whitespace. This is `sorted-json-v1`, versioned so future canonicalization
changes cannot silently invalidate old records.

`integrity.manifest_hash` is SHA-256 over the canonical payload excluding the
`integrity` and `signature` members.

The Ed25519 signature is over:

```text
SENTINEL-DNA-GATE5-MANIFEST-V2\n + canonical_payload_bytes
```

The manifest includes runtime, lockfile, dependency metadata, image, bridge,
provider, environment, origin, policy, issuer, approval, evidence, integrity,
and signature identities. Local Phase 1 manifests use
`approval_status=STAGING_LOCAL_APPROVED` and are not Gate 5 certification.
