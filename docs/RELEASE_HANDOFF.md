# Sentinel DNA Release Handoff

## Frozen release identity

This handoff records the certified release-engineering state for operator and
independent-review use. It does not authorize deployment or Gate 1.

| Artifact | Certified value |
| --- | --- |
| Commit | `8a7df7e07da0b50054fabcb393dffee1b58a8cff` |
| Git tree | `497c82a893d67ebf86751253b039abd30cb7d7e5` |
| Image ID | `sha256:5f92c7d28dbe0eeee5e5cc9e0051292a312364a39c3a83e78d09501a496f5d25` |
| RepoDigest | `deployment-app@sha256:5f92c7d28dbe0eeee5e5cc9e0051292a312364a39c3a83e78d09501a496f5d25` |

## Engineering evidence

- Release engineering: **COMPLETE**.
- The frozen hardening boundary contains exactly six files; no subsequent
  application or deployment mutation is part of the certified commit.
- Build-context security policy: **PASS**.
- Immutable image: **PASS**. The image runs as non-root user `sentinel` with
  effective command `gunicorn wsgi:application` and exposes `5000/tcp`.
- OCI provenance: **PASS**.
  - Full revision: `8a7df7e07da0b50054fabcb393dffee1b58a8cff`
  - OCI revision: `8a7df7e07`
  - OCI source: `https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA`
  - OCI version: exact full release SHA
  - Created: `2026-08-24T03:22:34Z`
- Image-bound release manifest: **PASS**. It binds the exact SHA, Git tree,
  image ID, RepoDigest, release-boundary hashes, and self-hash exclusion;
  `--require-image` verification passed.
- Deployment/security suite: **91 passed**.
- Full regression: **2778 passed, 4 skipped, 0 failed**.

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
