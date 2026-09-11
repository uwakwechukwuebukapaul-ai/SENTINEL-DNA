# Gate 5A Read-Only External Authorization Handoff

**State:** `BLOCKED_PENDING_EXTERNAL_AUTHORIZATION`

This is a metadata-only handoff checklist. It is not an authorization, approval,
signature, verifier identity, trust root, or staging-activation instruction.

## Candidate binding

| Field | Required value |
|---|---|
| Candidate repository | `uwakwechukwuebukpaul-ai/SENTINEL-DNA` |
| Candidate branch | `gate5-controlled-pilot-activation` |
| Candidate commit | `4e35f0cb20cfab4779e1a567342e1855962ac58e` |
| Candidate image reference | `sentinel-dna:pilot-staging-candidate-4e35f0c` |
| Candidate immutable image digest | `sha256:45ce0498839eb12fe07f08c9bb153bab5c9c7f2531b2b7a991f2ad1eec2e3995` |
| Staging origin | `controlled-pilot-staging` |
| Activation scope | Gate 5 controlled pilot staging only; no production promotion |
| Request issued at | `2026-09-10T00:00:00Z` |
| Request expires at | `2026-09-17T00:00:00Z` |
| Request status | `PENDING_EXTERNAL_AUTHORIZATION` |

The candidate commit above is the exact 40-character commit bound by the local
custody request and current checked-out `HEAD`. Any differing or shortened
commit string must be rejected as a candidate-binding mismatch.

## Provenance and runtime requirements

The external authority must independently verify these provenance identities:

- `com.sentinel-dna.git.revision.full:4e35f0cb20cfab4779e1a567342e1855962ac58e`
- `org.opencontainers.image.revision:4e35f0cb20cfab4779e1a567342e1855962ac58e`
- `org.opencontainers.image.source:https://github.com/uwakwechukwuebukpaul-ai/SENTINEL-DNA`

The authorization must bind an independently verified runtime identity and
immutable runtime/image digest. The request deliberately has
`approved_runtime_digest: null`; the repository cannot fill, approve, or
self-attest that value.

The authority must also preserve the staging-origin and activation-scope
requirements above, and provide an independently controlled rollback reference
and evidence reference. The local request records
`rollback_reference: REQUIRED_FROM_EXTERNAL_AUTHORITY`.

## Prohibition on credential-bearing material

The independent reviewer must **not receive, request, inspect, copy, print,
paste, or disclose** any passwords, MFA codes, API keys, access tokens, private
keys, secret files, database credentials, TLS private keys, or other
credential-bearing material. The reviewer may receive and verify only non-secret
metadata and authorization evidence necessary to establish candidate identity,
provenance, immutable image digest, approved runtime identity/digest, staging
scope, rollback reference, evidence reference, expiry, reviewer identity,
approval reference, and integrity/signature metadata.

## Evidence the independent authority must issue

The externally issued authorization must contain, at minimum:

1. An authorization type identifying a Gate 5 custody authorization.
2. A request identifier bound to `gate5-custody-request-4e35f0c`.
3. The exact repository, branch, commit, image reference, and image digest above.
4. An external verifier identity controlled independently of this repository.
5. An operator approval reference issued through the independent authority.
6. A signature and/or integrity evidence reference issued and verified externally.
7. A trusted verification-root reference controlled independently of this repository.
8. An independently verified evidence reference and evidence digest.
9. An issued-at timestamp and expiry timestamp for the authorization. The
   authorization must be valid at the time of use and must not outlive the
   request validity window without a separately reviewed request.
10. A rollback reference sufficient for the authority to direct safe rollback.

## Candidate-binding checks

Before issuing anything, the external authority must independently:

- compare the repository, branch, exact 40-character commit, image reference,
  and immutable digest with the authoritative source;
- verify that image provenance identities resolve to the same candidate;
- verify the runtime identity and immutable runtime digest;
- verify that the request is unmodified, pending, unexpired, and integrity-bound;
- verify the staging origin and confirm that the scope excludes production;
- validate the evidence reference, evidence digest, rollback reference, and
  trusted verification root;
- record the independent verifier identity and operator approval reference; and
- reject any repository-local callback, self-attested boolean, synthetic
  identity, locally generated signature, or locally generated trust root.

## Authority boundary

The external release/security authority must independently issue the
authorization artifact after completing its own verification and approval
process. This repository cannot manufacture, sign, approve, verify, or promote
that authorization. No Gate 5A PASS is claimed here, and no staging activation
is authorized by this handoff.
