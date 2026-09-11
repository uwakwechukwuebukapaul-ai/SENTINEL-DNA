# Gate 5 Pilot Activation Manifest

## Manifest metadata

Project: Sentinel DNA
Gate: Gate 5 Controlled Analyst Pilot
Manifest status: DRAFT / PENDING HUMAN AUTHORIZATION
Record timestamp: 2026-09-07T20:13:52.4214721Z
Prepared by: repository inspection; no activation was performed

Authorized candidate commit: ca1d61467f4520f52a986e5fa1a8c13d499d2229
Authorized candidate tree: 0c34089a3781c172c3711094b870f61964902d9
Repository HEAD at preparation review: b48c17daeb2ab329b9682537bf21c33e2c16967a

## Candidate artifact identity

Image reference: NOT PROVIDED
Immutable digest: NOT PROVIDED
Build provenance: PENDING EXTERNAL ARTIFACT RECORD

Activation cannot proceed until the artifact digest record is complete and
reconciled with the exact candidate identity.

## Environment target

Target: disposable, non-production Sentinel DNA staging environment.
Access path: selected Tailscale private path, subject to external configuration
and preflight.
Certified origin: `https://uwakwe-desktop.taile388cc.ts.net`
Edge boundary: loopback-only `127.0.0.1:18443->443/tcp`
Production access: prohibited.

## Ownership and scope

Deployment owner: PENDING / NOT PROVIDED
Approved analyst identity: PENDING / NOT PROVIDED
Synthetic tenant: PENDING / NOT PROVIDED
Reviewer: PENDING / NOT PROVIDED
Rollback owner: PENDING / NOT PROVIDED
Execution window and expiry: PENDING / NOT PROVIDED

No analyst identity or approval is created by this manifest.

## Allowed actions

After separate human approval and successful preflight, the analyst may perform
one bounded, non-destructive synthetic investigation through the approved
browser path. Required checks include authentication, RBAC, CSRF, tenant
isolation, evidence/provenance linkage, audit coverage, advisory-only AI
handling, denial matrix, and post-revocation fail-closed behavior.

The analyst may not access production, customer data, PostgreSQL, Redis, Docker,
SSH, shell/container, secrets, management, metrics, or destructive operations.

## Rollback

Stop on public exposure, origin/TLS drift, unexpected access, cross-tenant
leakage, missing audit/provenance, credential exposure, backup/restore failure,
or any unmeasured required gate. Revoke authorization, deactivate the analyst,
invalidate sessions, disable or narrow the private access path, preserve only
safe external custody references, and obtain fresh approval before restart.

## Evidence capture

Evidence must be written once to approved external custody using the existing
authenticated-pilot schema. Record the real run ID, source candidate identity,
UTC start/completion times, opaque references, direct observations, hashes,
revocation results, and human decision. Do not place secrets, credentials,
cookies, session IDs, or customer data in Git or evidence.

## Approval requirements

Required before activation: external artifact digest, staging runtime and TLS
preflight, fresh backup/isolated restore evidence, approved analyst and
synthetic tenant, security/release approval, monitoring and rollback ownership,
and evidence-custody availability.

This manifest authorizes no access, deployment, analyst acceptance, or
production promotion.

## Status classification

READY: Scope, allowed actions, exclusions, rollback, and evidence requirements
are defined.

BLOCKED: Activation prerequisites and human authorization are absent.

OWNER ACTION REQUIRED: Authorized governance owner must provide the approved
scope, owner, analyst, tenant, expiry, rollback contact, and decision.

NOT MEASURED: No activation, analyst access, or pilot execution occurred.
