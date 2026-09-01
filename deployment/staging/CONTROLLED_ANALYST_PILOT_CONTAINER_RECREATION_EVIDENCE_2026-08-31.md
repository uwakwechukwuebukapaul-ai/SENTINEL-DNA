# Controlled analyst pilot container recreation evidence — 2026-08-31

This is a new append-only evidence record. No application, authentication, port,
or existing evidence artifact was changed.

## Reviewed deployment contract

- Nginx certificate: `/etc/nginx/tls/staging-server.crt`.
- Nginx private key: `/etc/nginx/tls/staging-server.key`.
- Compose bind sources use `staging-server.crt` and `staging-server.key` only.
- `staging-ca.key` is not mounted.
- Pilot publication remains `127.0.0.1:18443:443`.

## Recreation attempt

- Command checked: `docker ps`.
- Result: BLOCKED; Docker is not installed or available in this execution environment.
- Edge recreation: NOT EXECUTED, because the controlled Docker runtime is unavailable.
- Expected binding `127.0.0.1:18443->443/tcp`: NOT MEASURED.

`BLOCKED_WITH_REASON`: the pilot edge could not be recreated from this host.
