# Security Hardening Checklist

- [ ] TLS/WAF/rate limits configured at ingress.
- [ ] Managed secrets, key rotation, and encrypted backups enabled.
- [ ] PostgreSQL and Redis private networking enforced.
- [ ] Kubernetes non-root, read-only filesystem, resource limits, and network policy validated.
- [ ] OIDC/SAML signature verification, MFA secret storage, and SCIM authorization reviewed.
- [ ] Tenant-isolation, token-revocation, audit-export, migration, Redis, and restore tests passed in the target environment.
- [ ] External penetration test and incident-response exercise completed.
