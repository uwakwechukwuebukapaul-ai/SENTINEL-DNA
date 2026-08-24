# Sentinel DNA Production Custody Handoff

This is a production-custody evidence handoff record. It is not a deployment
guide and does not authorize production, Gate 1, or any production mutation.

**CUSTODY HANDOFF READY does NOT mean production ready.** It means the
repository-side contract for receiving and validating external production
prerequisites is complete.

## 1. Release identity

| Artifact | Certified value |
| --- | --- |
| SHA | `8eef9afd588a1dda80975bb997e4baae06a1d06d` |
| Git tree | `6ca1c289586f84e93d5e9bb29fa4490f3dfbae9a` |
| Image ID | **NOT MEASURED FOR THIS COMMIT** |
| RepoDigest | **NOT MEASURED FOR THIS COMMIT** |
| OCI revision | `8eef9afd5` |
| OCI source | `https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA` |
| OCI version | Exact full certified SHA |
| Runtime user | `sentinel` |
| Command | `gunicorn wsgi:application` |
| Port | `5000/tcp` |

## 2. Certified artifact statement

The application source release is frozen at the exact SHA and Git tree above.
The immutable image ID and RepoDigest remain external gates until independently
measured for this commit. Every externally provisioned production input must be
associated with the exact SHA, Git tree, image ID, RepoDigest, and verified
release manifest. Mutable tags, working-tree files, stale metadata, and local development TLS are not release
authority.

## 3. Infrastructure custody requirements

The protected production environment must be supplied through an authorized
external path passed as `--env-file`. It must be an absolute regular file
outside the repository, non-reparse, and protected together with its parent
directory.

On Windows, the validator requires:

- `SYSTEM` and `BUILTIN\Administrators` allow Full Control.
- No Deny entry for either privileged principal.
- No non-privileged Allow entry granting write, create, delete, modify, or
  replace rights.
- The file and parent directory must remain outside the repository and free of
  symlink/reparse indirection.

The protected configuration must contain the required names:

- `SENTINEL_DNA_ENV=production`
- `SENTINEL_DNA_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `SENTINEL_DNA_IMAGE_TAG`
- `SENTINEL_DNA_IMAGE_REVISION`
- `SENTINEL_DNA_IMAGE_REVISION_FULL`
- `SENTINEL_DNA_IMAGE_CREATED`
- `SENTINEL_DNA_IMAGE_DIGEST`
- `SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE`
- `SENTINEL_DNA_TLS_DIR`
- `SENTINEL_DNA_SECURE_COOKIES=1`

Release metadata must match the certified SHA, short revision, full revision,
UTC creation value, and exact image digest. The protected metadata path must
match the controller's `--metadata-file`; the configured image digest must
match `--expected-digest`.

## 4. Secret custody requirements

Secret-bearing variables are identified by name only:

- `SENTINEL_DNA_SECRET_KEY`
- `POSTGRES_PASSWORD`

Values must be provisioned by an approved secret custodian. They must never:

- Appear in handoff evidence, command lines, logs, reports, or Git.
- Be printed, serialized, or included in failure output.
- Be supplied through the repository `.env`.

Validation may report only safe categories such as present, missing, or
invalid. Custody evidence should identify the authorized custodian, protected
path, ACL result, validation result, and timestamp without disclosing values.

## 5. Production TLS requirements

Production TLS must be supplied in an authorized external directory referenced
by `SENTINEL_DNA_TLS_DIR`. The directory must be absolute, outside the
repository, existing, regular, and non-reparse.

Infrastructure must provide evidence that:

- The expected certificate and private-key files exist.
- The certificate is CA-issued and valid for the production identity/SANs.
- Certificate lifecycle and renewal ownership are defined.
- The private key remains in protected custody and is never included in
  evidence.
- SYSTEM and Administrators have required control.
- Non-privileged principals have no write/create/delete/replace rights.
- The Compose TLS mount is read-only.

The checked-in `localhost.crt`, `localhost.key`, and related local material are
development/localhost validation assets only. They are not production CA TLS
and must not be substituted for it.

## 6. Trusted metadata requirements

The authorized metadata destination is:

`C:\ProgramData\Sentinel-DNA\release\metadata.json`

The exact expected schema for this release is:

```json
{
  "release_sha": "8eef9afd588a1dda80975bb997e4baae06a1d06d",
  "image_digest": "<EXTERNAL_RELEASE_GATE_IMAGE_DIGEST>"
}
```

The existing generator must be used only after authorization. It verifies the
current checkout, image revision/source, and actual RepoDigest, rejects stale
or mismatched identity, writes outside the source tree, and uses a temporary
file followed by flush, fsync, and atomic replacement.

After authorized replacement, the operator must verify the exact two-field
schema, SHA, digest, destination path, and ACL. Existing stale metadata must
not be treated as current and must not be repaired by an unauthorized party.

## 7. Evidence requirements

Safe custody evidence must cover:

- Protected configuration path, type, reparse status, ACL, and safe validator
  categories.
- Secret-custody authorization without secret values.
- TLS path, file names/types, CA/identity/validity evidence, ACL, and
  read-only mount evidence without private-key contents.
- Trusted metadata schema, SHA, digest, path security, ACL, and post-write
  verification.
- Image ID, RepoDigest, OCI provenance, runtime user, command, and port.
- Git SHA, tree, clean checkout, release-boundary hashes, and manifest
  verification with `--require-image`.
- Checked-in Compose topology and read-only metadata/TLS mounts.
- Regression and deployment/security test results.
- Custody authorization, independent review, and the explicit safety boundary.

Evidence must never disclose secrets, private keys, credentials, or sensitive
configuration values.

## 8. Custody authority

Responsibilities remain separate:

- **Infrastructure custody:** protected environment path, host ACLs, Compose
  host boundary, and production runtime prerequisites.
- **Secret custody:** secret generation, storage, rotation, and revocation.
- **TLS custody:** CA-issued material, SAN/validity lifecycle, private-key
  protection, and TLS ACLs.
- **Release operator:** exact checkout, image, manifest, and authorized
  metadata preparation.
- **Independent reviewer:** review and acceptance of the complete evidence
  package.
- **Gate 1 authority:** separate authorization decision after prerequisites and
  independent review.
- **Deployment authority:** separate authorization for any production action.

No role automatically grants the authority of another role.

## 9. Independent review package

The reviewer must receive the complete nonsecret package:

- SHA and Git tree.
- Image ID and RepoDigest.
- OCI revision, source, version, and creation evidence.
- External release manifest and `--require-image` result.
- Regression and deployment/security test results.
- Protected configuration validation categories and ACL evidence.
- Production TLS issuer/identity/validity evidence and ACL evidence.
- Trusted metadata schema, exact binding, path, ACL, and post-write evidence.
- Compose topology and read-only mount evidence.
- Custody authorization and role separation.
- Safety boundary and explicit statement that deployment is not authorized.

## 10. Gate 1 prerequisites

Gate 1 remains blocked until protected configuration, secret custody,
production CA TLS, compliant ACLs, current trusted metadata, independent
review, and explicit authorization are complete.

The authorization chain is deliberately separate:

```text
custody evidence -> independent review
independent review -> Gate 1 decision
Gate 1 decision -> separate deployment authorization
validate-only -> validation evidence only; never deployment authorization
```

Custody does not equal review. Review does not equal Gate 1. Gate 1 does not
automatically authorize deployment. `--validate-only` does not deploy.

## 11. Validation-only sequence

After all custody and review prerequisites are complete, an authorized operator
must:

1. Obtain a fresh clean checkout at the certified SHA and verify the tree.
2. Verify the certified image ID, RepoDigest, OCI provenance, user, command,
   and port.
3. Generate or obtain the external release manifest and verify it with
   `--require-image`.
4. Verify the protected configuration and TLS path/ACL evidence without
   exposing secret or private-key material.
5. Use the authorized metadata generator and perform post-write verification.
6. Obtain independent review and record the authorization decision.
7. Run only the following command:

```powershell
python deployment/scripts/controlled_deploy.py `
  --reviewed-sha 8eef9afd588a1dda80975bb997e4baae06a1d06d `
  --expected-digest <EXTERNAL_RELEASE_GATE_IMAGE_DIGEST> `
  --env-file <AUTHORIZED_PROTECTED_ENV_FILE> `
  --metadata-file C:\ProgramData\Sentinel-DNA\release\metadata.json `
  --release-manifest <VERIFIED_RELEASE_MANIFEST> `
  --docker-executable <AUTHORIZED_DOCKER> `
  --validate-only
```

Validation must stop immediately on any failure. No `--execute` operation is
part of this handoff.

## 12. Forbidden actions

- No deployment before separate authorization.
- No metadata refresh without authorization.
- No localhost TLS substitution for production CA TLS.
- No secret or private-key exposure.
- No ACL bypass or policy weakening.
- No validator bypass.
- No production mutation.
- No remote push.
- No modification of the certified release.

## 13. Current blocker register

- Protected production configuration.
- Secret custody.
- Production CA TLS.
- TLS ACL.
- Current trusted metadata.
- Independent review.
- Gate 1 authorization.
- Deployment authorization.

## 14. Final status

`CUSTODY HANDOFF READY`

`PRODUCTION RELEASE BLOCKED`

`RELEASE FREEZE = INTACT`
