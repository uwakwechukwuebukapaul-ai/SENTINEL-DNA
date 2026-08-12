# Deployment Guide

## Private enterprise beta

Run Sentinel DNA behind a TLS-terminating reverse proxy. Do not expose the Flask development server directly to the internet. Set a persistent, access-controlled `SENTINEL_DNA_DATA_DIR`; customer records and the SQLite databases must be backed up and retained according to the customer agreement.

```text
SENTINEL_DNA_HOST=0.0.0.0
SENTINEL_DNA_PORT=5000
SENTINEL_DNA_DATA_DIR=/var/lib/sentinel-dna
SENTINEL_DNA_DEBUG=false
```

Build and run the included non-root container, then configure the platform health probe for `/healthz` and readiness probe for `/readyz`. Collect stdout as JSON logs. Restrict `/metrics` to the monitoring network because it is intended for Prometheus scraping.

## Production checklist

- Put the service behind TLS, a WAF/rate-limiting proxy, and organization SSO where required.
- Use a managed secret store for integration credentials; never commit secrets or mount them into logs.
- Use encrypted volumes, tested backups, and a documented restore exercise.
- Forward JSON logs and protect audit-log retention from ordinary application users.
- Set alerts for health/readiness failures, authentication-denial spikes, and elevated 5xx responses.
- Keep SQLite for the private beta only. Migrate the SaaS boundary to PostgreSQL before horizontal scaling; introduce Redis for distributed rate limits/cache and a worker queue for asynchronous workloads.
