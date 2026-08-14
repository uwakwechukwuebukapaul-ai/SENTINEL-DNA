# Sentinel DNA API

## Authentication

Authenticate through the session login flow. Mutating requests require `X-CSRF-Token`; tenant-scoped APIs require an active organization context.

## Common endpoints

- `GET /api/organizations/current`
- `GET /api/connectors`
- `POST /api/streaming/events`
- `POST /api/intelligence/chat/ask`
- `GET /api/monitoring/health`

Responses use JSON and return structured `error` codes for authentication, authorization, tenant, and validation failures.
