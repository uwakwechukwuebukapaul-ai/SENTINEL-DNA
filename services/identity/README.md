# Enterprise Identity and RBAC

This package provides tenant-aware user, role, permission, session, and policy abstractions. It extends the platform gateway through identity-backed policy checks without replacing gateway authorization or the legacy `services/tenant` contracts.

The default repository is deterministic and in-memory for local and test use. Production persistence and external identity providers are future seams. JWT, OAuth2, SAML, Entra ID, Okta, LDAP, and SSO adapters must validate claims externally and then map them to these models. Missing tenant, inactive users, expired sessions, and unknown roles are denied by default.
