# Local Microsoft Entra OIDC staging

This runbook activates only Microsoft Entra ID. Google Workspace and Okta are
not registered, so they cannot appear in the backend-driven provider list.

## Configuration

Copy `deployment/staging/.env.example` into the protected staging
configuration store and populate only the non-secret Azure values. Keep:

```text
SENTINEL_DNA_ENTRA_OIDC_ENABLED=1
SENTINEL_DNA_ENTRA_REDIRECT_URI=https://localhost/auth/enterprise/entra/callback
SENTINEL_DNA_CERTIFIED_ORIGIN=https://localhost
```

The client secret is external only. Set
`SENTINEL_DNA_STAGING_ENTRA_CLIENT_SECRET_FILE` to a protected host file and
let Compose mount it as `/run/secrets/staging_entra_client_secret`. The
application receives only the reference name
`SENTINEL_DNA_ENTRA_CLIENT_SECRET`; it never receives a secret from source
control or a committed `.env` file.

## Azure App Registration

1. In Microsoft Entra admin center, create an App registration for the staging
   tenant. Use the tenant (single-tenant) account type.
2. Under Authentication, add a Web redirect URI exactly equal to
   `https://localhost/auth/enterprise/entra/callback`.
3. Create a client secret, record its value once, and place it in the approved
   external secret store. Do not put it in this repository.
4. Expose the OIDC ID-token claims required by Sentinel DNA: `tid`, `oid`,
   `sub`, `ver`, `nonce`, and `roles`.
5. Define and assign the application roles `sdna.requester` and/or
   `sdna.reviewer` to the approved users or groups.
6. Populate the tenant/client IDs and the tenant-specific issuer, authorize,
   token, JWKS, and discovery URLs in the protected staging configuration.
7. Ensure the local HTTPS certificate trusts the staging CA and contains the
   `localhost` DNS name.

## Validation checklist

Run from the repository root with the protected staging environment loaded:

```powershell
python deployment/staging/scripts/validate_entra_oidc_config.py
python deployment/staging/scripts/validate_entra_oidc_config.py --check-discovery
docker compose --env-file <PROTECTED_STAGING_ENV_FILE> -f deployment/staging/docker-compose.yml config
curl.exe --fail --silent --show-error https://localhost/auth/enterprise/providers
```

The provider endpoint must contain Entra only after configuration, secret
availability, and discovery validation succeed. Before that it must return an
empty provider list. Complete a browser sign-in and confirm that an assigned
Entra identity has a pre-created active Sentinel DNA binding and provider
tenant-trust record. If MFA is enabled for the account, the first callback must
leave the session pending MFA verification.

