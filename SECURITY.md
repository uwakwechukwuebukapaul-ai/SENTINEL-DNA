# Security Guide

## Implemented controls

- Passwords are uniquely salted and hashed with PBKDF2-HMAC-SHA256 at 600,000 iterations. Plaintext passwords are never persisted.
- Session tokens are high-entropy random values. Only SHA-256 digests are stored; sessions expire and can be revoked with `POST /auth/logout`.
- Every tenant-scoped API request authenticates a principal and verifies organization membership. Role checks protect investigator actions and membership changes; only an owner can grant owner access.
- SQLite connections enable foreign-key enforcement, use bound parameters, and commit or roll back atomically.
- HTTP responses include anti-sniffing, frame-denial, referrer, and content-security headers. Operational failures return generic public errors.
- JSON logs allow-list operational metadata and exclude credentials, bearer tokens, alert payloads, evidence, and tenant content.

## Operating requirements

Use TLS, managed secrets, encrypted storage, restricted metrics access, central log collection, dependency scanning, and a reverse-proxy rate limit. SQLite is appropriate only for a single-instance beta deployment. Key management, data retention/deletion controls, SSO/SCIM, distributed rate limiting, and external penetration testing remain required before a broad public SaaS launch.
