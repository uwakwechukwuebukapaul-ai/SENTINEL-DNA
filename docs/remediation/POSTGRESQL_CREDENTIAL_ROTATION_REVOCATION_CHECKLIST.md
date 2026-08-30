# PostgreSQL credential rotation and revocation checklist

This checklist includes a bounded manually reported disposable rotation
operation. It does not claim production credential access or complete
rotation/revocation closure.

## Scope and controls

- [x] Scope was reported as disposable rehearsal credentials; independent
      review remains required.
- [ ] Credential owner, approver, expiry, and secret-store reference recorded
      without recording the secret value.
- [x] Production `DATABASE_URL` was not used.
- [x] Customer data was not used.
- [ ] Evidence output and operator/reviewer records supplied externally.

## Rotation test

- [x] `ALTER USER` completed successfully in the disposable PostgreSQL
      environment.
- [x] Replacement credential identity and least-privilege scope evidenced by
      the rotated disposable credential.
- [x] Rotated credential acceptance evidenced.
- [x] Old password rejection evidenced.
- [ ] Replacement credential revoked or expired after the rehearsal.
- [ ] Final revocation verified.
- [ ] Logs reviewed for absence of secret values and credential-bearing URLs.

## Manual evidence fields

- Target environment: `sentinel-dna-postgres-rehearsal-postgres-1`
- Credential identifiers/references: `NOT SUPPLIED`
- Rotation/revocation timestamps (UTC): `NOT SUPPLIED`
- Old-credential failure evidence: `old password rejected`
- Replacement-credential success evidence: `rotated credential accepted`
- Final revocation evidence: `NOT SUPPLIED`
- Operator: `NOT SUPPLIED`
- Independent reviewer: `NOT SUPPLIED`
- Remediation HEAD: `94e3da4f4fa3952981fb68e9d0d3205ec6aa6a7c`

The bounded credential rotation/revocation rehearsal is evidenced. Final
operational custody and independent attestation remain required; no secret
values are recorded here.
