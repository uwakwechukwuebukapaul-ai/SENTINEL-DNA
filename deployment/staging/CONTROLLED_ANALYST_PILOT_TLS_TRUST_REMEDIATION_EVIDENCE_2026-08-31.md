# Controlled analyst pilot TLS trust remediation evidence — 2026-08-31

This is a new append-only evidence record. Existing Gate 2, release-manifest,
and pilot-evidence artifacts were not modified or deleted.

## CA verification

- Certificate: `C:\ProgramData\Sentinel-DNA\staging\staging-ca.crt`
- Command: `certutil -dump C:\ProgramData\Sentinel-DNA\staging\staging-ca.crt`
- Result: PASS; subject and issuer are `CN=Sentinel DNA Staging Root CA`.
- Basic Constraints: `CA=TRUE`, path length `0`.
- Self-signature: `Signature matches Public Key`; `Root Certificate: Subject matches Issuer`.
- Server leaf import: NOT PERFORMED.
- CA trust import: only the CA certificate was imported into `Cert:\LocalMachine\Root`.

## Leaf contract

- Leaf: `staging-server.crt`, CN `sentinel-dna-staging`.
- SANs: `sentinel-dna-staging`, `localhost`, `127.0.0.1`, `192.168.1.115`.
- EKU: Server Authentication.
- Private key contents were not exposed.

## Status

`BLOCKED_WITH_REASON`: Docker edge recreation, live TLS handshake, Chrome warning
check, `/health` HTTP 200, and `/ready` HTTP 200 remain unmeasured.
