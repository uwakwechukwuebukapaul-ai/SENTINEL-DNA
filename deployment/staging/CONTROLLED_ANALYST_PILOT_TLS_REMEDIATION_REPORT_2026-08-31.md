# Controlled analyst pilot TLS remediation report — 2026-08-31

## Scope

This append-only addendum records the staging TLS architecture correction. It
does not replace or revise the existing Gate 2 reports, pilot evidence, tenant
isolation evidence, audit/provenance chain, or release decision.

## Correction

The legacy `staging.crt` artifact was not accepted as an HTTPS leaf because it
was a CA certificate. The staging generator now creates distinct material:

- `staging-ca.crt` and `staging-ca.key`: private staging root CA material;
- `staging-server.crt` and `staging-server.key`: HTTPS server leaf material.

The server leaf is issued for the reviewed pilot identity:

- `DNS:sentinel-dna-staging`;
- `IP:127.0.0.1`;
- `IP:192.168.1.115`, when required by pilot network policy.

The leaf requires critical `Basic Constraints: CA=FALSE`, includes the
`serverAuth` Extended Key Usage, and is validated against the staging CA.
Both private keys remain outside Git with mode `0600`; only the server pair is
mounted into Nginx. The CA private key is not mounted into any container.

## Validation evidence

- Staging security contract: `18 passed`.
- Deployment contract subset: `91 passed`, `2 skipped` for platform-specific
  POSIX permission semantics.
- Generator regression coverage rejects a CA certificate placed in the server
  leaf slot.
- Nginx contract points to `/etc/nginx/tls/staging-server.crt` and
  `/etc/nginx/tls/staging-server.key`.
- `validate_staging_tls.py` performs a verified TLS 1.2/1.3 handshake using
  only `staging-ca.crt` as the trust anchor and SNI
  `sentinel-dna-staging`.

## Operator actions still required

On the pilot host, generate the new material, copy the reviewed Nginx
configuration, and reload/recreate the edge. Import only `staging-ca.crt` into
the approved Windows current-user Trusted Root store. Then run the handshake
validator and record its protocol result and certificate fingerprint in a new
run-specific evidence artifact. Do not overwrite the existing evidence.

The authenticated pilot remains blocked until the approved browser confirms
chain trust and all existing tenant, audit, provenance, denial, and revocation
gates are directly measured. No analyst URL is issued by this remediation.

## Follow-up inspection

The repository contains no `staging.crt` certificate artifact, and no such
certificate is tracked in Git. The historical generator configured that legacy
name as a self-signed certificate with `Basic Constraints: CA=FALSE`; the
actual external file therefore cannot be classified from repository contents
alone. Operators must inspect any retained external file before quarantine.

The corrected generator now creates a self-signed root CA with
`CA=TRUE; pathlen:0` and a separately issued `staging-server.crt` leaf with
`CA=FALSE`. The handshake validator requires the root CA as its trust anchor,
rejects a server leaf supplied as the CA file, and retains normal hostname and
certificate-chain verification.

Follow-up validation: staging TLS contract tests `19 passed`; shell, Python,
Node, and diff checks passed. Existing Gate 2 artifacts, manifests, and
append-only evidence were not overwritten.
