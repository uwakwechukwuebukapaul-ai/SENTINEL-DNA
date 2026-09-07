# Gate 5 Origin Connectivity Validation

## Record metadata

Project: Sentinel DNA
Gate: Gate 5 Controlled Analyst Pilot
Status: BLOCKED_PENDING_EXTERNAL_ORIGIN_PREFLIGHT
Record timestamp: 2026-09-07T20:06:55.1294813Z
Performed by: static repository review; no live endpoint request succeeded

Candidate commit: ca1d61467f4520f52a986e5fa1a8c13d499d2229
Candidate tree: 0c34089a3781c172c3711094b870f61964902d9

## Required origin

Certified analyst origin: `https://uwakwe-desktop.taile388cc.ts.net`
Selected private path: Tailscale raw TCP forwarding to the staging edge.
Expected edge publication: `127.0.0.1:18443->443/tcp` only.

Cloudflare is paused for the first analyst login and is not an alternate path.

## Validation procedure

The approved operator must, from the staging host and enrolled analyst device:

1. Verify private DNS and the approved private-path destination.
2. Verify the Tailscale policy is deny-by-default and limited to the staging
   tag and TCP 443; no Funnel, public route, broad CIDR, or exit node.
3. Verify the raw TCP Serve forwarder reaches only `127.0.0.1:18443`.
4. Run the repository Tailscale private-access validator with external policy,
   CA, and Compose environment paths.
5. Request `/health` and `/ready` with the approved CA and exact hostname/SNI.
6. Verify certificate chain, security headers, reverse-proxy routing, and no
   redirect/origin drift.
7. Verify PostgreSQL, Redis, Docker, SSH, shell/container, metrics,
   management, repository, LAN, and production surfaces are denied or
   unroutable from the analyst device.

## Current observations

| Check | Result |
|---|---|
| Repository origin policy | PREPARED / STATIC ONLY |
| Loopback edge configuration | PASS / RECORDED IN COMPOSE |
| Live DNS reachability | BLOCKED / NOT OBSERVED |
| Live TLS CA/SNI validation | BLOCKED / NOT OBSERVED |
| Live `/health` and `/ready` | BLOCKED / NOT OBSERVED |
| Security headers | PENDING LIVE OBSERVATION |
| Private-path isolation | PENDING EXTERNAL PREFLIGHT |

No live origin, certificate, DNS, runtime, or deployment event is claimed by
this record.
