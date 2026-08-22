# Operations runbook

## Health

Check `/health` for process/database liveness and `/ready` for application readiness. Responses include component status and an `X-Correlation-ID` for diagnosis.

## Worker and queue recovery

Evaluation and notification work uses durable tenant-scoped repositories, bounded leases, heartbeats, retry backoff, and dead-letter states. Expired leases are reclaimed through SQL-bounded queries. Re-run maintenance after a worker restart and inspect retry/dead-letter counts before replaying work.

## Provider failures

Providers are optional unless explicitly configured. A provider timeout becomes a categorized retryable failure; invalid credentials, unsafe destinations, or policy errors do not loop indefinitely. Never place resolved credentials in logs or ticket content.

## Incident handling

Preserve correlation IDs, tenant, case, worker, provider, and failure category. Do not copy raw evidence or secrets into incident channels. Audit events and append-only workflow history are the source of truth for analyst actions.
