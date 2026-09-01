# Controlled analyst pilot final TLS gate status — 2026-08-31

`BLOCKED_WITH_REASON`

| Gate | Status | Evidence |
|---|---|---|
| CA is self-signed `CA=TRUE` root | PASS | `certutil -dump` |
| Only CA trusted; leaf not imported | PASS | `Cert:\LocalMachine\Root` thumbprint check |
| Nginx uses server leaf pair only | PASS | Compose and Nginx contract review |
| Pilot edge recreated | BLOCKED | Docker unavailable |
| Expected loopback binding | NOT MEASURED | `docker ps` unavailable |
| TLS handshake succeeds | BLOCKED | curl exit 35, `SEC_E_NO_CREDENTIALS` |
| Chrome warning disappears / lock is valid | BLOCKED | Chrome control unavailable |
| `/health` returns 200 | BLOCKED | No live HTTPS response |
| `/ready` returns 200 | BLOCKED | No live HTTPS response |

Do not start the analyst pilot. Release remains blocked until the edge is
recreated and all four live gates pass: Chrome trust, TLS handshake, `/health`
200, and `/ready` 200.
