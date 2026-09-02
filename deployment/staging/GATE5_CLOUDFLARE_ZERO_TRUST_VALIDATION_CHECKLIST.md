# Gate 5 Cloudflare Zero Trust Validation Checklist

This checklist validates private remote access to the existing Sentinel DNA
staging deployment. It does not change application architecture, authorize a
production deployment, create an analyst, or generate pilot evidence.

Current status: `READY_FOR_ANALYST_PILOT`.

## Cloudflare access mode decision

- [ ] Use a Cloudflare One self-hosted private application and a private
      network route through the reviewed Tunnel connector.
- [ ] Use the Cloudflare One Client/WARP path for the analyst device. The
      certified origin uses HTTPS port `18443`; clientless Browser Isolation is
      not accepted for this port unless Cloudflare and the security owner have
      approved a separately validated compatible path.
- [ ] Do not create a public-hostname Tunnel route, public DNS record, Access
      bypass, or alternate Sentinel DNA origin.
- [ ] Do not enable `noTLSVerify`; origin TLS verification must remain enabled.
- [ ] Record Cloudflare account, tunnel, private-application, route, policy,
      device, and expiry references externally. Never copy tokens, API keys,
      private keys, or session cookies into Git or pilot evidence.

Cloudflare references: [private self-hosted applications](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/non-http/self-hosted-private-app/),
[Access policy behavior](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/),
[Tunnel origin TLS parameters](https://developers.cloudflare.com/tunnel/advanced/origin-parameters/),
and [private network routing](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/private-net/cloudflared/connect-cidr/).

## 1. Ownership and approval

- [ ] Cloudflare account owner, tunnel owner, Sentinel operator, security
      reviewer, and rollback owner are identified.
- [ ] The approved analyst identity is verified through the configured IdP and
      bound to this pilot's external run ID.
- [ ] Analyst device enrollment, MFA, and posture requirements are satisfied.
- [ ] Access start and expiry are approved in UTC and shorter than the pilot
      operating window.
- [ ] Exactly one synthetic tenant, one analyst, and one scenario set are in
      scope.
- [ ] Security/release authority approved the private access method and
      remote endpoint outside Git.

## 2. Private application and policy

- [ ] Cloudflare application type is self-hosted/private, not public hostname.
- [ ] Target is the exact private Sentinel DNA staging host and port
      `sentinel-dna-staging:18443`; no wildcard hostname or broad CIDR is used.
- [ ] Access policy is explicit default-deny with an Allow rule for the one
      approved analyst identity and the required operator identity only.
- [ ] MFA and any approved device posture requirement are enforced.
- [ ] No `Everyone`, all-valid-emails, unauthenticated, service-token-only,
      or `Bypass` rule is present.
- [ ] Session duration is short and the policy can be disabled immediately.
- [ ] Access policy logs are enabled and retained under approved custody.
- [ ] Cloudflare access logs are treated as perimeter evidence, not as a
      substitute for Sentinel DNA application authentication/audit evidence.

## 3. Tunnel, route, and DNS

- [ ] The reviewed `cloudflared` connector runs on the staging host or an
      approved private connector with access only to the staging edge.
- [ ] Tunnel is outbound-only; no inbound firewall opening or public origin
      listener was added.
- [ ] The route maps only the approved staging application path to the existing
      loopback edge. Docker remains `127.0.0.1:18443->443/tcp`.
- [ ] PostgreSQL, Redis, Docker, SSH, shell/container, repository, metrics,
      management, and production networks are not routed.
- [ ] Private DNS resolves `sentinel-dna-staging` only for enrolled/approved
      devices through the approved resolver or local-domain policy.
- [ ] No public A, AAAA, CNAME, quick-tunnel, or wildcard record points to the
      staging application.
- [ ] Split-tunnel rules include only the reviewed private destination and do
      not advertise the full LAN or production network.
- [ ] Connector, route, DNS, and policy changes have external change records
      and safe references.

## 4. TLS and exact-origin validation

- [ ] Remote browser URL is exactly
      `https://sentinel-dna-staging:18443`.
- [ ] Approved CA validates the staging certificate from the remote device.
- [ ] Certificate SAN/SNI includes `sentinel-dna-staging` as required by the
      existing staging certificate contract.
- [ ] Tunnel origin settings use the approved CA pool and
      `originServerName=sentinel-dna-staging` where required.
- [ ] `noTLSVerify` is false/absent. Any enabled verification bypass is a hard
      stop.
- [ ] No redirect, Host header, Origin header, cookie domain, CSRF scope, or
      application base URL changes across the private path.
- [ ] `/health` and `/ready` are checked without authentication and do not
      alter application state.
- [ ] Remote boundary evidence records status, UTC time, exact origin, TLS
      result, and opaque custody reference only.

## 5. Surface isolation

- [ ] Remote analyst can reach only the application browser surface.
- [ ] Internal service ports fail closed or are unroutable from the analyst
      device.
- [ ] Analyst cannot reach Docker, SSH, database, Redis, shell/container,
      runtime, secrets, repository, metrics, or management interfaces.
- [ ] No public exposure or alternate listener is observed.
- [ ] A failed boundary test blocks authentication and leaves the evidence
      status `BLOCKED_WITH_REASON` or `NOT_MEASURED`.

## 6. Evidence handoff before login

- [ ] Create one external, append-only evidence record with class
      `remote_access_preflight` and status `NOT_EXECUTED`.
- [ ] Record run ID, source commit, access method, exact origin, scope,
      preflight statuses, policy/route references, backup/restore reference,
      and custody location.
- [ ] Do not record analyst passwords, activation values, Access cookies,
      Sentinel sessions, CSRF values, tokens, private keys, database rows, or
      customer data.
- [ ] Convert preflight status to `VERIFIED` only after direct observation and
      reviewer confirmation. This does not prove analyst behavior.
- [ ] Keep rehearsal evidence and authenticated pilot evidence in separate
      records and namespaces.

## 7. Authenticated pilot controls

- [ ] Manager authenticates through the approved browser-auth workflow and
      manager role/session are directly verified.
- [ ] Missing-CSRF denial is observed before a protected write.
- [ ] Analyst authenticates through the approved channel and the server-derived
      `analyst` role, tenant, authorization, and expiry are verified.
- [ ] RBAC denials cover admin escalation, authorization management,
      provisioning, database, shell/container, runtime-management, secrets,
      metrics, and destructive actions.
- [ ] Same-tenant workspace/results are verified; a known foreign-tenant
      request is denied with no leakage.
- [ ] Audit and provenance references cover authentication, onboarding,
      investigation, reads, denials, feedback, AI advisory-only handling,
      revocation, deactivation, and session invalidation.
- [ ] Authorization is revoked, analyst deactivated, sessions invalidated, and
      post-revocation access fails closed.
- [ ] Only after the real pilot, assemble the authenticated evidence class and
      run all five focused validators plus the full validator.

## 8. Rollback

- [ ] Disable the analyst Allow policy or remove the analyst from it.
- [ ] Disable/narrow the tunnel route or revoke the analyst device/peer.
- [ ] Revoke Sentinel authorization, deactivate the analyst, and invalidate
      active sessions.
- [ ] Verify post-revocation denial from the remote device.
- [ ] Preserve safe Cloudflare/Sentinel audit and custody references.
- [ ] Create a new run ID and obtain fresh approval before any restart.
