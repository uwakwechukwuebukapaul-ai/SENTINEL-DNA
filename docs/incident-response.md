# Sentinel DNA incident response

1. Confirm scope using the request/correlation ID and tenant-safe operational views.
2. Preserve audit, lifecycle, queue, lease, retry, and notification records.
3. Contain the affected provider, route, worker, or tenant boundary without disabling authentication or tenant checks.
4. Rotate compromised secret references through the deployment secret manager; do not edit stored payloads to hide exposure.
5. Validate `/health`, `/ready`, tenant isolation, redaction, and browser login before recovery.
6. Record root cause, affected versions, evidence references, recovery actions, and follow-up tests.

Security incidents must not be “resolved” by weakening authorization, bypassing CSRF, or exposing raw provider/model content.
