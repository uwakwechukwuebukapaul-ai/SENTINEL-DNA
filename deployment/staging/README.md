# Sentinel DNA Staging Preparation

This directory describes preparation for one isolated, non-production remote
analyst pilot. It is not a deployment authorization and contains no real
credentials, URLs, certificates, analyst identities, tenant identifiers, or
activation tokens.

## Runtime contract

The staging runtime is defined by
`deployment/staging/docker-compose.yml` and uses the canonical
`wsgi:application` entrypoint. The application, PostgreSQL, and Redis services
are private; only the staging edge is exposed, and that edge must be private
HTTPS, VPN, or zero-trust infrastructure.

`deployment/scripts/deploy.sh` is staging-only. It requires an absolute
`STAGING_ENV_FILE` outside the repository and explicitly selects the staging
Compose file. It must not be run as part of this repository gate. The root
`docker-compose.yml` and `deployment/docker-compose.yml` remain production
contracts and must not be used for staging.

Use the [staging checklist](CHECKLIST.md) with an infrastructure operator who
can provide an approved private non-production runtime and remote boundary.
The [staging environment template](.env.example) is a non-secret template
only; inject values through the approved non-production secret/configuration
store and never commit the populated file or use the repository `.env`.

## Staging TLS certificate

The supported browser endpoint is:

```text
https://sentinel-dna-staging:8443/
```

TLS terminates at the Nginx edge on container port `443`; Docker publishes
that edge as `0.0.0.0:8443:443`. Gunicorn remains private on the Docker
network at `app:5000`. Use the checked-in
[`nginx.conf`](nginx.conf) as the reviewed source for the external edge
configuration file. It references `/etc/nginx/tls/staging.crt` and
`/etc/nginx/tls/staging.key` and must be mounted read-only by Compose.

The self-signed staging certificate must contain these SANs:

```text
DNS:sentinel-dna-staging
IP Address:192.168.1.115
IP Address:127.0.0.1
```

The LAN address is an example for the current staging VM. It is supplied by
`SENTINEL_DNA_STAGING_TLS_IP` in the external staging environment and is not
application configuration. The generator also always includes the stable
hostname and `127.0.0.1`; it does not add arbitrary SANs. It uses the reviewed
[`staging-cert-config.json`](staging-cert-config.json) configuration, RSA
3072-bit keys, SHA-256, and a 397-day validity period.

On the staging host, with `/etc/sentinel-dna/staging.env` populated outside
Git, generate or validate the material as follows:

```sh
set -a
. /etc/sentinel-dna/staging.env
set +a
python3 deployment/staging/scripts/generate_staging_cert.py
```

The TLS directory must be an absolute path outside the repository. The
generator creates the directory with restrictive permissions, writes the
private key as mode `0600`, writes the certificate as mode `0644`, validates
the SAN and key/certificate pairing, and is safe to rerun. An existing
certificate with a changed LAN IP or missing SANs fails closed; rotate it only
after review with:

```sh
python3 deployment/staging/scripts/generate_staging_cert.py --rotate
```

After generation, copy the reviewed repository Nginx template to the external
path named by `SENTINEL_DNA_STAGING_EDGE_CONFIG_FILE`, then run the documented
staging deployment workflow. Recreate or reload only the staging edge after a
certificate rotation so Nginx reads the new files. Never place
`staging.env`, a private key, or generated certificate material in Git.

Validate the certificate before opening the browser:

```sh
openssl x509 \
  -in "$SENTINEL_DNA_STAGING_TLS_DIR/staging.crt" \
  -noout -subject -issuer -dates -ext subjectAltName
```

The output must show `DNS:sentinel-dna-staging`, the configured LAN IP, and
`IP Address:127.0.0.1`. Because this is self-signed staging material, import
the exact certificate into the Windows current-user Trusted Root store; do
not disable TLS verification or trust a private key:

```powershell
Import-Certificate -FilePath .\staging.crt -CertStoreLocation Cert:\CurrentUser\Root
Test-NetConnection sentinel-dna-staging -Port 8443
curl.exe -I https://sentinel-dna-staging:8443/
```

The expected application result for the final request is HTTP `401` with the
authentication-required response. A browser hostname mismatch indicates that
the requested hostname is not in SAN; do not weaken authentication or bypass
certificate verification. This certificate model is for internal staging
only and can later be replaced by a CA-issued certificate using the same
Nginx certificate/key mount contract.

## Required staging controls

The runtime must fail the preflight if any control is absent or if production
configuration, production credentials, or a production database is detected:

```text
SENTINEL_DNA_ENV=staging
SENTINEL_DNA_PILOT_ACCESS_REQUIRED=1
SENTINEL_DNA_SECURE_COOKIES=1
FLASK_DEBUG=0
```

The runtime also requires `SENTINEL_DNA_CONFIG_SOURCE_CLASSIFICATION` to be
`external_non_production` and
`SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION` to be
`disposable_staging`. These values are defense-in-depth declarations; network,
database-role, target-ownership, and secret-store isolation remain
infrastructure responsibilities. No hostname heuristic is used.

Staging must use separate database, Redis, volumes, and non-production secret
material. The analyst-facing boundary is browser-only and private; database,
Redis, SSH, shell, repository, GitHub, and management interfaces remain
unavailable to the analyst.

The staging application volume is the named `staging_app_data` volume mounted
at `/var/lib/sentinel`. Its canonical SQLite compatibility path is
`/var/lib/sentinel/soc.db`; `/var/lib/sentinel/staging` is not part of the
contract and must not be introduced as an application-created directory. The
staging runtime's authoritative database remains the private PostgreSQL
`DATABASE_URL`, so the SQLite path is not a fallback when PostgreSQL is
configured or unavailable.

## Health and rollback gates

After an approved operator starts the staging runtime, verify `/health` and
`/ready` through the private boundary, then verify authentication, pilot
authorization, tenant isolation, audit/provenance, monitoring, and the
emergency revocation path. These checks are not evidence of a real analyst
execution.

Rollback is limited to the isolated staging runtime and a verified staging
backup restored into a separate staging target. Never restore over a
production database and never include secrets or customer data in the backup.
