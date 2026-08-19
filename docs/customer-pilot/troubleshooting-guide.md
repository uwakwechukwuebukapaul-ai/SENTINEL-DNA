# Customer Pilot Troubleshooting Guide

- If startup fails, verify environment configuration, database storage permissions, and `/health` and `/ready` responses.
- If a scenario cannot run, confirm the scenario ID with `GET /api/pilot/scenarios` and verify tenant/analyst authorization.
- If a run cannot be retrieved, confirm it belongs to the active tenant. Cross-tenant run access returns not found.
- If feedback or metrics are unavailable, complete the investigation and submit a valid analyst outcome first.

Never include credentials, tokens, raw evidence payloads, or provider responses in tickets or logs.
