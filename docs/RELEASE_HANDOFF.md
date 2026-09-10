# Sentinel DNA Release Handoff

## Frozen release identity

This handoff records the certified release-engineering state for operator and
independent-review use. It does not authorize deployment or Gate 1.

| Artifact | Certified value |
| --- | --- |
| Commit | `8eef9afd588a1dda80975bb997e4baae06a1d06d` |
| Git tree | `6ca1c289586f84e93d5e9bb29fa4490f3dfbae9a` |
| Image ID | **NOT MEASURED FOR THIS COMMIT** |
| RepoDigest | **NOT MEASURED FOR THIS COMMIT** |

## Engineering evidence

- Release engineering: **COMPLETE**.
- The certified engineering boundary is the committed tree identified above;
  no deployment authorization is implied by this document.
- Build-context security policy: **PASS**.
- Immutable image: **PASS**. The image runs as non-root user `sentinel` with
  effective command `gunicorn wsgi:application` and exposes `5000/tcp`.
- OCI provenance: **PASS**.
  - Full revision: `8eef9afd588a1dda80975bb997e4baae06a1d06d`
  - OCI revision: `8eef9afd5`
  - OCI source: `https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA`
  - OCI version: exact full release SHA
  - Created: **NOT MEASURED FOR THIS COMMIT**
- Image-bound release manifest: **EXTERNAL GATE**. Image ID, RepoDigest, and
  OCI creation evidence must be supplied by the authorized image release
  process for this exact SHA.
- Release/deployment validation: **33 passed** in the certified validation.
- Full regression: **2869 passed, 4 skipped, 0 failed**.

Operational procedures remain in [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md),
[CONTROLLED_DEPLOYMENT_ADAPTER.md](CONTROLLED_DEPLOYMENT_ADAPTER.md), and
[PRODUCTION_RUNBOOK.md](PRODUCTION_RUNBOOK.md).

## Outstanding external blockers

Infrastructure:

- Protected production configuration is unavailable.
- Production CA-issued TLS material is unavailable.
- The current TLS ACL fails the existing protected-path validator.

Security and custody:

- Secret custody is unavailable.
- Trusted production metadata remains bound to the previous release.
- Authorized trusted-metadata refresh is unavailable.

Governance and authorization:

- Independent release review is unavailable.
- Gate 1 authorization is unavailable.
- `controlled_deploy.py --validate-only` has not run because protected
  prerequisites are incomplete.

These are external release prerequisites, not engineering regressions.

## Authorized operator handoff

The authorized operator must perform the following sequence without modifying
the certified source or image:

1. Obtain an approved clean checkout.
2. Verify the exact commit SHA and Git tree.
3. Verify the exact certified image ID and RepoDigest.
4. Provision protected production configuration through approved secret custody.
5. Provision production CA-issued TLS material.
6. Correct TLS and protected-path ACLs through authorized infrastructure
   procedure.
7. Refresh trusted metadata with the existing atomic generator.
8. Obtain independent review of SHA, tree, image ID, RepoDigest, and metadata.
9. Run `controlled_deploy.py --validate-only`.
10. Stop immediately on any validation failure.
11. Only a separately authorized Gate 1 process may consider deployment.

## Safety boundary and final classification

Codex must not create or print secrets, fabricate metadata or digests, repair
stale metadata without authorization, change ACLs to obtain a pass, use
localhost TLS for production, run `--execute`, push Git or images, deploy, or
authorize Gate 1.

Final classification:

**RELEASE ENGINEERING COMPLETE  AWAITING AUTHORIZED INFRASTRUCTURE/GOVERNANCE**

Readiness score: **48/100**, unchanged because production infrastructure,
security custody, independent review, and authorization controls remain
outstanding.

```text
RELEASE FREEZE = INTACT
ENGINEERING = COMPLETE
IMAGE_CERTIFICATION = PASS
DEPLOYMENT = NOT PERFORMED
PRODUCTION_MUTATION = NONE
GATE_1 = BLOCKED
NEXT ACTION = AUTHORIZED INFRASTRUCTURE + INDEPENDENT REVIEW
```
