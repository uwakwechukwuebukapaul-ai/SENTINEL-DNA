# API Examples

```http
GET /api/organizations/current
Cookie: session=<authenticated-session>
```

```http
POST /api/intelligence/chat/ask
X-CSRF-Token: <session-csrf-token>
Content-Type: application/json

{"question":"Which evidence supports this alert?"}
```
