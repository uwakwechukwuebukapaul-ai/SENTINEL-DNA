# Gate 5 Remote Analyst Access Runbook

## Status

Current status remains `READY_FOR_ANALYST_PILOT`. This runbook is an operator
procedure for preparing and executing one bounded remote staging pilot. It is
not production deployment documentation and does not create analysts,
credentials, approvals, or evidence automatically.

## Hard stops

Stop if any of the following is true:

- a public hostname, wildcard listener, alternate origin, or unapproved
  redirect is introduced;
- TLS cannot be verified with the approved CA and exact staging SNI;
- the remote path can reach database, Redis, SSH, Docker, shell, metrics,
  management, repository, or production surfaces;
- Gate 4 readiness is not `READY_FOR_ANALYST_PILOT` with all checks PASS;
- backup/restore, human approval, identity approval, or custody is missing;
- any authenticated control is `NOT_MEASURED`, fabricated, or inferred;
- credentials, tokens, cookies, session values, or sensitive payloads appear in
  logs or evidence.

## A. Preflight

1. Confirm the reviewed branch/commit and inspect `pilot-evidence/gate4/`.
2. Reconcile provider, runtime, bridge, image, manifest, TLS, and lockfile
   identities with external custody.
3. Verify all populated secret/configuration files and remote-access keys are
   outside the repository.
4. Complete the fresh staging backup and isolated restore checklist. Do not
   proceed while the retained evidence says `not_executed`.
5. Obtain external human approval for this specific non-production run.
6. Confirm exactly one approved synthetic tenant, analyst, scenario set, and
   expiry.

## B. Configure private remote access

### Preferred: Cloudflare One private application

1. Create or select a private self-hosted application for the staging target;
   do not create a public published hostname route.
2. Bind the application to the exact private staging hostname/port and route
   through the reviewed Tunnel connector on the staging host.
3. Configure an explicit Allow policy for the approved analyst identity and
   required operator identity only. Keep default deny for everyone else.
4. Require approved identity authentication and MFA/device policy where
   available. Use a short session duration and an explicit expiry.
5. Ensure the connector validates the staging origin certificate and SNI. Never
   set a TLS verification bypass.
6. Confirm access to only the browser surface; do not route the database,
   Redis, Docker, SSH, or management networks.
7. Obtain the connector/policy reference and hash in external custody. Do not
   copy connector tokens or policy secrets into the repository.

### Fallback: WireGuard private overlay

1. Provision one externally held peer for the approved analyst device.
2. Route only the reviewed staging application path; do not advertise a broad
   LAN or production subnet.
3. Use host firewall/ACL rules to deny database, Redis, SSH, Docker, shell,
   metrics, and management ports.
4. If loopback forwarding is required, have the network owner review the
   host-level forwarding path. Keep Docker's edge publication unchanged at
   `127.0.0.1:18443->443/tcp`.
5. Record only peer identity, policy reference, route scope, expiry, and safe
   verification result.

## C. Validate the remote boundary

Run on the approved operator host and, after private access is granted, from
the approved analyst device. Do not substitute `-k` for CA verification.

```powershell
node deployment/staging/scripts/check_controlled_pilot_readiness.mjs
docker compose -f deployment/staging/docker-compose.yml ps
docker compose -f deployment/staging/docker-compose.yml port edge 443
Resolve-DnsName sentinel-dna-staging
Test-NetConnection sentinel-dna-staging -Port 18443
curl.exe --cacert <approved-staging-ca.crt> https://sentinel-dna-staging:18443/health
curl.exe --cacert <approved-staging-ca.crt> https://sentinel-dna-staging:18443/ready
```

Require the exact origin, valid certificate/SNI, no redirect, no public
publication, loopback-only edge binding, and no access to internal services.
Record only safe status and custody references.

## D. Authenticate and onboard

1. Launch the already reviewed trusted browser/provider at the certified
   origin.
2. Manager authenticates using the protected browser-auth flow.
3. Verify manager role and session; verify missing-CSRF requests fail closed
   before any protected write.
4. Provision only the approved synthetic tenant/analyst using the protected
   manager workflow, if the run approval includes provisioning.
5. Analyst activates through the approved channel. Never pass credentials or
   activation values as CLI arguments.
6. Verify analyst role, authorization expiry, and server-derived tenant scope.
7. Record opaque evidence references only.

## E. Execute controls

1. Run one approved, non-destructive synthetic investigation.
2. Verify analyst RBAC and denial of privileged, database, shell/container,
   runtime-management, and destructive surfaces.
3. Verify same-tenant workspace/result scope and known foreign-tenant denial
   with no leakage.
4. Verify audit events and provenance references for authentication, CSRF,
   onboarding, investigation, workspace/result access, denials, feedback, and
   AI advisory-only handling.
5. Revoke authorization, deactivate the analyst, invalidate sessions, and
   verify subsequent login renewal, reads, and writes fail closed.
6. Disable or narrow the remote access policy and retain safe revocation
   references.

## F. Assemble and validate evidence

Create a new externally held record; never overwrite an earlier record. Use
`GATE5_ANALYST_ACCESS_EVIDENCE.schema.json` for access/preflight evidence and
the full controlled-pilot schema for authenticated pilot evidence.

```powershell
node deployment/staging/scripts/validate_authenticated_analyst_access.mjs <evidence-file>
node deployment/staging/scripts/validate_analyst_rbac.mjs <evidence-file>
node deployment/staging/scripts/validate_tenant_isolation.mjs <evidence-file>
node deployment/staging/scripts/validate_audit_trail.mjs <evidence-file>
node deployment/staging/scripts/validate_session_revocation.mjs <evidence-file>
node deployment/staging/scripts/validate_manual_analyst_pilot_evidence.mjs <evidence-file>
```

Every validator must exit zero for a completed authenticated pilot. Any
missing, malformed, rehearsal-class, secret-bearing, stale, or unmeasured
record must return `BLOCKED_WITH_REASON` and stop the run.

## G. Closeout

- [ ] External custody sealed the evidence and recorded its SHA-256.
- [ ] Analyst authorization, account, sessions, and remote peer/policy are
      revoked or disabled.
- [ ] Audit/provenance references are retained without sensitive payloads.
- [ ] Pilot metrics and analyst feedback are collected without customer data.
- [ ] Security/release owner reviewed the report and chose repeat, extend, or
      close. No production release follows automatically.
