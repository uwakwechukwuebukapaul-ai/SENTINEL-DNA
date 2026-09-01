# Sentinel DNA staging TLS validation

This procedure validates the private, non-production staging edge without
disabling TLS verification. It uses a dedicated staging root CA and a
separate HTTPS server certificate. Never use `--insecure`, trust the server
leaf as a root, or copy either private key to an analyst workstation.

## 1. Generate the CA and server certificate

Set these values in the approved external staging environment file. The TLS
directory must be absolute and outside the repository:

```text
SENTINEL_DNA_STAGING_TLS_DIR=C:\ProgramData\Sentinel-DNA\staging\pilot-<id>\tls
SENTINEL_DNA_STAGING_TLS_IP=192.168.1.115
```

Generate the material from the reviewed checkout:

```powershell
$env:SENTINEL_DNA_STAGING_TLS_DIR = 'C:\ProgramData\Sentinel-DNA\staging\pilot-<id>\tls'
$env:SENTINEL_DNA_STAGING_TLS_IP = '192.168.1.115'
python deployment\staging\scripts\generate_staging_cert.py
```

The generator creates:

- `staging-ca.crt` and `staging-ca.key`: the self-signed staging root CA;
- `staging-server.crt` and `staging-server.key`: the HTTPS leaf signed by
  that CA;
- `staging-server-fullchain.crt`: the leaf followed by `staging-ca.crt`, which
  is mounted at Nginx's certificate path.

The leaf must contain `DNS:sentinel-dna-staging`, `DNS:localhost`,
`IP:127.0.0.1`, and the configured staging LAN IP. It must contain the Server
Authentication EKU, be `CA=false`, and match `staging-server.key`. Nginx
receives the leaf-first fullchain plus `staging-server.key`; `staging-ca.key`
is never mounted into a container.

Normal reruns are idempotent. To rotate only the leaf while retaining the
trusted root:

```powershell
python deployment\staging\scripts\generate_staging_cert.py --rotate
```

Use `--rotate-ca` only for a separately reviewed trust event. It requires
reinstalling the resulting `staging-ca.crt` before the edge is restarted.

## 2. Make hostname resolution deterministic

The validator connects to loopback but sends TLS SNI and the HTTP `Host`
header as `sentinel-dna-staging`. The name must resolve to the same loopback
address. On the staging host, maintain the approved hosts entry:

```text
127.0.0.1 sentinel-dna-staging
```

On Windows, add it to
`C:\Windows\System32\drivers\etc\hosts` using an elevated editor, then
verify the result:

```powershell
Resolve-DnsName sentinel-dna-staging
```

The validator fails closed if the name does not resolve or resolves to an
address different from `--connect-host`.

## 3. Install only the CA

Copy only `staging-ca.crt` to the approved analyst machine through the
controlled certificate-distribution process. Install it in the LocalMachine
Trusted Root store with administrator approval:

```powershell
Import-Certificate `
  -FilePath 'C:\approved\staging-ca.crt' `
  -CertStoreLocation Cert:\LocalMachine\Root
```

Confirm that the CA is present and the server leaf is not installed as a
trusted root. Do not distribute `staging-ca.key` or `staging-server.key`.

## 4. Validate chain, identity, and HTTPS health

Run the validator against the running private edge:

```powershell
python deployment\staging\scripts\validate_staging_tls.py `
  --ca-file 'C:\ProgramData\Sentinel-DNA\staging\pilot-<id>\tls\staging-ca.crt' `
  --certificate-file 'C:\ProgramData\Sentinel-DNA\staging\pilot-<id>\tls\staging-server-fullchain.crt' `
  --private-key-file 'C:\ProgramData\Sentinel-DNA\staging\pilot-<id>\tls\staging-server.key' `
  --connect-host 127.0.0.1 `
  --server-name sentinel-dna-staging `
  --port 18443 `
  --health-path /health
```

Success prints JSON with a top-level `"status": "ok"`, the negotiated TLS
1.2/1.3 protocol, and the verified health response. The validator checks all
of the following before reporting success:

1. the CA is a current self-signed `CA=true`, path-length-zero trust anchor;
2. the server certificate is current, `CA=false`, signed by that CA, contains
   the requested SAN and Server Authentication EKU, and matches its private
   key; the supplied fullchain contains exactly the leaf followed by that CA;
3. `sentinel-dna-staging` resolves to the address used for the connection;
4. TLS hostname and chain verification succeed with the CA as the explicit
   trust anchor; and
5. `GET /health` returns HTTP 200 JSON whose `status` is `ok`.

The equivalent curl acceptance check is:

```powershell
curl.exe --fail-with-body --silent --show-error `
  --ssl-revoke-best-effort `
  --cacert 'C:\approved\staging-ca.crt' `
  https://sentinel-dna-staging:18443/health
```

The response must be exactly the health contract `{"status":"ok"}`. On Windows,
`--ssl-revoke-best-effort` is required for this private CA because it has no
public CRL/OCSP service; this retains certificate-chain and hostname
verification and only treats an unavailable revocation status as indeterminate.
Do not replace it with `--ssl-no-revoke` or `--insecure`. The command must
succeed with `--cacert`; adding `--insecure` is a certification failure.

If any step fails, keep the pilot blocked. Check the hostname mapping, the
mounted `staging-server.crt`/`staging-server.key` pair, CA installation, and
the edge recreation. Do not weaken verification to make the request pass.
