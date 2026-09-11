# Gate4 custody intake package

Status: source-side intake only. This package does not create, approve, deploy,
sign, restart, or repair any runtime artifact.

The intake boundary is fail-closed. A local repository observation, historical
evidence, image tag, runtime behavior, or test fixture cannot substitute for an
independently supplied custody record.

## Evidence classes

| Class | Meaning | Examples |
|---|---|---|
| A. Operator-supplied | Protected configuration references and bounded runtime choices supplied by the staging operator | secret-file paths, certified origin, bind/port, image references |
| B. Externally-custodied | Artifacts and attestations held outside the repository and independently approved | browser runtime, BrowserAuth bridge, image digests, signatures |
| C. Docker-generated | Evidence produced by a Docker/Linux build or inspection, not by a Windows source test | OCI image digest, labels, platform, container image inspection |
| D. Root-level read-only | Host evidence requiring an authorized read-only root inspection | nftables, iptables, DOCKER-USER, forwarding state |
| E. Live runtime | Evidence observed from the authorized Linux staging runtime | Compose render, container health, network membership, `/health`, `/ready` |
| F. Human/browser acceptance | Evidence requiring an approved browser and human reviewer | certified-origin navigation, BrowserAuth, login, RBAC, tenant isolation |

## Custody domain matrix

| Domain | Required artifact and identity fields | Digest/hash | Authority/supplier | Local/Docker/root/human | Validation and fail-closed rule |
|---|---|---|---|---|---|
| `REPOSITORY_PROVENANCE` | Exact reviewed commit, tree, repository identity, and Gate4 source manifest | Commit/tree identifiers and manifest SHA-256 | Release/repository owner | Local; Docker not required; root not required; human review required | Compare commit/tree to the authorized release record; mismatch or dirty release source blocks |
| `RUNTIME_IMAGE_PROVENANCE` | Sentinel image, immutable OCI reference, platform, source revision, build timestamp, builder, manifest, labels, attestation | OCI manifest digest and provenance-record SHA-256 | Independent image/build custody | Docker required; root not required for inspection; external attestation required | `repo@sha256:...`, platform, source revision, and attestation must agree; tag-only, unknown labels, or missing attestation blocks |
| `BROWSER_PROVENANCE` | Linux/amd64 browser executable, Playwright version/revision, executable path, runtime bundle, base image, dependency closure | Runtime, executable, lockfile, base-image, and OCI digests | Approved browser/runtime custody | Docker required; external custody required; human acceptance required later | `verify-image-inputs.mjs` and independent custody record must agree; missing bytes, digest, platform, or registry verification blocks |
| `BROWSERAUTH_BRIDGE_PROVENANCE` | Bridge identity, reviewed export `requestBrowserAuth`, exact bytes, allowed environment, tenant/security context | Bridge SHA-256 | Separate operator/security custody | Local structural verification; external custody and human acceptance required | `validate_trusted_browser_auth_bridge.mjs` and external digest must agree; missing or malformed bridge blocks |
| `EGRESS_POLICY_PROVENANCE` | Versioned HTTPS-only policy, approved DNS names/ports, policy reference, owner, review/expiry record | Policy file SHA-256 and reference binding | Network/security owner | Policy can be prepared locally; Docker runtime verification required; root evidence later | `egress-policy.mjs` validates schema/digest; private/metadata/IP literals, changed digest, missing policy, or unreviewed destination blocks |
| `ACTIVATION_MANIFEST_PROVENANCE` | Schema version, provider/runtime identities, runtime digest, image runtime digest, certified origin, timestamp, approval reference, integrity, optional lockfile and bridge identities | Manifest integrity SHA-256; detached signature reference where supplied | External custody/approval system | Manifest can be assembled locally only from supplied facts; external custody and human approval required | `scripts/trusted_browser_activation_manifest.mjs` and `scripts/verify_gate4_external_artifacts.mjs`; missing integrity, origin, digest, approval, or bridge binding blocks |
| `LIVE_DEPLOYMENT_PROVENANCE` | Authorized host, source/image identity, Compose config digest, container IDs, image IDs, network membership, health/readiness, edge/TLS evidence, firewall baseline | Captured evidence bundle hash and image/container digests | Authorized Linux operator and independent reviewer | Docker and live runtime required; root read-only firewall evidence required; human acceptance required | Read-only preflight and runtime evidence must bind to the approved manifest; stale, legacy, exited, or unbound services block |

Historical evidence is retained as historical evidence. It is not current
runtime provenance and cannot satisfy a missing custody domain.

## Configuration intake checklist

Do not record secret contents. Record only a protected reference, owner,
classification, expiry/rotation status, and a redacted presence result.

### Secrets

- [ ] `SENTINEL_DNA_STAGING_APP_SECRET_FILE` — protected readable file reference; contents never copied.
- [ ] `SENTINEL_DNA_STAGING_POSTGRES_PASSWORD_FILE` — protected readable file reference; contents never copied.
- [ ] `SENTINEL_DNA_STAGING_SMTP_USERNAME_FILE` — protected readable secret-file path; contents never copied.
- [ ] `SENTINEL_DNA_STAGING_SMTP_PASSWORD_FILE` — protected readable secret-file path; contents never copied.
- [ ] `SENTINEL_DNA_STAGING_TRUSTED_BROWSER_SERVICE_KEY_FILE` — protected readable secret-file path; contents never copied.

### Environment configuration

- [ ] `SENTINEL_DNA_CERTIFIED_ORIGIN` — exact approved HTTPS origin.
- [ ] `SENTINEL_DNA_CERTIFIED_HOSTNAME` — externally supplied DNS name for staging TLS SANs.
- [ ] `SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_HOST` and `SENTINEL_DNA_TRUSTED_BROWSER_SERVICE_PORT` — private RPC endpoint.
- [ ] `SENTINEL_DNA_TRUSTED_BROWSER_EGRESS_READY` — independently evidenced readiness assertion.
- [ ] `SENTINEL_DNA_TRUSTED_BROWSER_EGRESS_PROXY` — approved gateway endpoint.
- [ ] `SENTINEL_DNA_EGRESS_GATEWAY_BIND` and `SENTINEL_DNA_EGRESS_GATEWAY_PORT` — injected gateway bind/port.
- [ ] `SENTINEL_DNA_TRUSTED_BROWSER_GATEWAY_UPLINK_NETWORK` — existing approved external uplink network identity.
- [ ] `SENTINEL_DNA_STAGING_EDGE_CONFIG_FILE` — protected edge configuration path.
- [ ] `SENTINEL_DNA_STAGING_TLS_DIR` — protected TLS directory containing the approved server chain/key.
- [ ] `SENTINEL_DNA_EGRESS_POLICY_FILE` — protected policy file path.

### Artifact references

- [ ] `SENTINEL_DNA_STAGING_APP_IMAGE` — immutable `repository@sha256:...` reference required.
- [ ] `SENTINEL_DNA_STAGING_EDGE_IMAGE`
- [ ] `SENTINEL_DNA_IMAGE_TAG`
- [ ] `SENTINEL_DNA_TRUSTED_BROWSER_IMAGE` — immutable reference required.
- [ ] `SENTINEL_DNA_EGRESS_GATEWAY_IMAGE` — immutable reference required.
- [ ] `SENTINEL_DNA_POSTGRES_IMAGE` — immutable reference required.
- [ ] `SENTINEL_DNA_REDIS_IMAGE` — immutable reference required.
- [ ] `SENTINEL_DNA_EGRESS_POLICY_REFERENCE`

All staging runtime image references, including application, edge, trusted
browser, gateway, PostgreSQL, and Redis, are required to be immutable digest
references. Mutable tags are rejected by the redacted validator and are not
release identities.

### Provenance values

- [ ] `SENTINEL_DNA_IMAGE_REVISION_FULL`
- [ ] `SENTINEL_DNA_IMAGE_CREATED`
- [ ] `SENTINEL_DNA_IMAGE_DIGEST`
- [ ] `SENTINEL_DNA_APPROVED_RUNTIME_DIGEST`
- [ ] `SENTINEL_DNA_EGRESS_POLICY_DIGEST`
- [ ] `SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST`

### Runtime/provider inputs

- [ ] `SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME`
- [ ] `SENTINEL_DNA_BROWSER_EXECUTABLE`
- [ ] `SENTINEL_DNA_BROWSER_EXECUTABLE_SHA256`
- [ ] `SENTINEL_DNA_BROWSER_AUTH_BRIDGE`
- [ ] `SENTINEL_DNA_TRUSTED_BROWSER_CLIENT`
- [ ] `SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT`
- [ ] `PLAYWRIGHT_BASE_IMAGE`

The redacted validator is `scripts/validate_gate4_custody_intake.py`. It reads
only environment names and non-secret metadata, never prints values, never
creates files, and rejects placeholders, mutable trusted-browser/gateway image
references, missing SHA-256 values, repository-relative protected paths, and
developer-machine paths.

The external custody package interface is defined by
`GATE4_EXTERNAL_CUSTODY.schema.json` and validated by
`scripts/validate_gate4_external_custody.py`. The authoritative artifact
classes are `SENTINEL_BUILT`, `EXTERNAL_SECURITY_BOUNDARY`, and
`THIRD_PARTY`. The application and trusted-browser wrapper are
`SENTINEL_BUILT`; the egress gateway and edge are
`EXTERNAL_SECURITY_BOUNDARY`. External does not mean trusted by default:
every image requires an immutable digest, independently verified signature,
digest-bound SBOM, meaningful supplier/build provenance, independent
approval, and activation-manifest binding. The supplier identity must match
the independently approved trust policy; a vendor label alone is insufficient.
Mutable tags, opaque images,
self-asserted verification, and historical/conflicting evidence are blocked.

The repository-side workflow design is `.github/workflows/gate4-custody.yml`.
It is manual-only, requires explicit external-custody confirmation, requires
registry and signer configuration from the workflow environment, and fails
closed when any build context, digest, signing, SBOM, provenance, or identity
input is unavailable. It builds only Sentinel-owned images and verifies the
externally supplied egress and edge image references without building or
signing them. Adding the workflow does not execute it or establish custody.

## Artifact tooling already present

Safe source-side tooling already exists for:

- image input and build-context validation:
  `trusted_browser_runtime/verify-image-inputs.mjs` and
  `trusted_browser_runtime/verify-build-context.mjs`;
- runtime custody and dependency closure:
  `scripts/trusted_browser_runtime_custody.mjs`;
- BrowserAuth bridge structure:
  `scripts/validate_trusted_browser_auth_bridge.mjs`;
- activation manifest validation:
  `scripts/trusted_browser_activation_manifest.mjs`;
- external artifact reconciliation:
  `scripts/verify_gate4_external_artifacts.mjs`;
- trusted-browser/provider readiness:
  `scripts/verify_trusted_browser_provider.mjs` and
  `scripts/generate_trusted_browser_readiness_report.mjs`;
- egress policy and DNS/TOCTOU enforcement:
  `scripts/trusted_browser_service/policy/egress-policy.mjs`,
  `network-policy.mjs`, and `egress_gateway/gateway-server.mjs`;
- Gate4 evidence generation:
  `scripts/generate_gate4_evidence.mjs`.

The repository does not contain the externally approved runtime bytes, browser
bytes, bridge bytes, immutable production image attestations, or live custody
records needed to make those validators pass.

## Known staging-edge blocker

Do not restart or repair this container during intake.

- Container: `staging-edge-1`
- Image: `nginx:stable`
- Exit code: `1`
- Known error: missing `/etc/nginx/tls/localhost.crt`
- Classification: `PRE-EXISTING LEGACY CONDITION`
- Classification: `GATE4 DEPENDENCY`

The observed container also used legacy edge configuration and did not prove
the Gate4 TLS/configuration custody contract. Resolution requires a separately
authorized operator action and fresh read-only evidence afterward.

## IPv6 acceptance condition

- IPv6 forwarding remains disabled.
- Gate4 currently uses IPv4-only browser egress.
- Do not enable IPv6 for this intake.
- Acceptance must prove there is no usable IPv6 browser egress path.
- Any future IPv6 enablement requires a separately approved design with
  equivalent IPv6 policy, subnet controls, and enforcement evidence.

## Root-level read-only evidence commands

An authorized operator may later run these commands for evidence only:

```sh
sudo nft list ruleset
sudo iptables-save
sudo ip6tables-save
sudo iptables -S DOCKER-USER
sudo ip6tables -S DOCKER-USER
sudo sysctl net.ipv4.ip_forward net.ipv6.conf.all.forwarding
sudo nft list chain inet filter forward
sudo nft list chain inet filter DOCKER-USER
```

If a chain does not exist, record that fact as `NOT_PRESENT`; do not create it.
The evidence must show forwarding policy, Docker-user policy, browser-subnet
enforcement, and the IPv4-only/IPv6-disabled condition. No command in this
package applies firewall, route, DNS, sysctl, interface, or Docker changes.

## Hard-stop rule

Runtime validation remains blocked until the redacted intake validator passes,
all seven custody domains have authoritative evidence, Compose renders from
protected external configuration, root-level firewall evidence is captured,
the legacy edge issue is separately resolved, and the approved browser/human
acceptance evidence is available.
## Phase A verification boundary

The external custody validator requires typed evidence records. Boolean fields
such as `verified: true` are not accepted. A custody package is blocked unless
the evidence record is independently approved and includes an evidence
reference, evidence digest, verifier identity, verification method, timestamp,
and approval reference. The validator also loads the actual activation-manifest
bytes and cross-checks every release and artifact digest before accepting it.

The permitted status vocabulary is `MISSING`, `PRESENT`, `CLAIMED`,
`LOCALLY_VERIFIED`, `EXTERNALLY_VERIFIED`, `INDEPENDENTLY_APPROVED`,
`HISTORICAL`, `CONFLICTING`, and `BLOCKED`. `CLAIMED`, `HISTORICAL`,
`CONFLICTING`, and `MISSING` can never be promoted by local JSON claims.

The repository does not contain authoritative build contexts for
`deployment/staging/egress_gateway/Dockerfile` or
`deployment/staging/edge/Dockerfile`. The custody workflow therefore fails
closed unless externally supplied immutable custody for both security-boundary
images is present; this package does not invent either Dockerfile.

The only security-relevant gateway configuration injected by staging Compose
is the approved egress policy, whose reference and digest remain mandatory.
The edge Nginx configuration is a repository-controlled security-boundary
configuration and is bound by digest to the release. TLS private keys are
never read, recorded, hashed, or printed. TLS intake retains only a non-secret
private-key custody reference, the public certificate digest, and an
independently approved certificate/private-key match evidence record. Missing,
self-asserted, mismatched, historical, or conflicting key-match evidence
blocks custody; metadata alone never substitutes for custody of the key.
The key-match record must bind the certificate digest and the non-secret key
custody reference, and must include its own evidence digest, verifier identity,
verification method, timestamp, and approval reference.

The workflow's third-party trust policy is separate from the custom-image
signer policy. The protected `gate4-custody` environment and external approval
are prerequisites for any future publish/signing run. Action references still
require immutable SHA pinning from an approved dependency source; no SHA is
fabricated in this repository.
