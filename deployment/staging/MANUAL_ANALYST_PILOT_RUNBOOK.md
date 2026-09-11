# Manual Controlled Analyst Pilot Validation Runbook

This is a manual validation procedure for the isolated Sentinel DNA staging
pilot. It does not create users, generate credentials, issue URLs, modify
application security logic, or change production configuration.

The pilot remains blocked unless every required gate has direct evidence. A
healthy endpoint, static test, or HTTP response without the required context is
not evidence of an authenticated pass.

## Scope and safety rules

- Use only the existing private staging edge at the operator-certified
  loopback binding. Never use a public, wildcard, LAN, or production origin.
- Use exactly one approved synthetic tenant and one approved synthetic analyst
  account if those identities have separately been provisioned. This runbook
  does not authorize provisioning.
- Use the approved browser workflow for authentication. Never paste passwords,
  cookies, CSRF values, activation values, or private keys into a terminal,
  ticket, screenshot, log, or evidence file.
- Do not use direct database clients, shell/container sessions, Docker exec,
  standalone HTTP credential clients, or simulated browser results.
- Do not perform a destructive action to test a denial. Use only a reviewed
  deny-only route or a documented no-op authorization check; otherwise record
  `NOT_MEASURED`.
- Store evidence as a new file. Never overwrite an earlier evidence artifact.

## Evidence preparation

Copy the evidence template to a new run-specific filename using the approved
operator process. Do not edit the template in place. Fill only non-secret
values:

```powershell
$EvidenceDir = 'C:\ProgramData\Sentinel-DNA\release\evidence'
$Template = Get-ChildItem -LiteralPath $EvidenceDir -Filter 'MANUAL-ANALYST-PILOT-EVIDENCE-TEMPLATE-*.json' |
  Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
if (-not $Template) { throw 'Evidence template not found' }
$EvidencePath = Join-Path $EvidenceDir 'manual-analyst-pilot-<unique-run-id>.json'
if (Test-Path -LiteralPath $EvidencePath) { throw 'Refusing to overwrite evidence' }
Copy-Item -LiteralPath $Template.FullName -Destination $EvidencePath -ErrorAction Stop
$EvidencePath
```

Record UTC timestamps, opaque runtime identifiers, HTTP status codes, gate
results, audit/provenance references, and hashes. Do not record credential
values, token values, database contents, customer data, or screenshots that
contain secrets.

## 1. Read-only staging boundary checks

Run before opening the application:

```powershell
docker version
docker ps --format "{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}"
docker port sentinel-dna-pilot-974e327-edge-1
docker network inspect sentinel-dna-pilot-974e327_staging_internal --format "{{.Internal}}"
Get-NetTCPConnection -State Listen | Where-Object {$_.LocalPort -in 80,443,18443} |
  Select-Object LocalAddress,LocalPort,OwningProcess
Test-NetConnection 127.0.0.1 -Port 18443
```

Record `PASS` only when the pilot edge is exactly
`127.0.0.1:18443 -> 443/tcp`, the pilot internal network is `true`, app,
PostgreSQL, and Redis have no published host ports, and no public listener or
route can reach the pilot. A separate wildcard listener requires operator
route-isolation confirmation before certification.

Verify the certificate without weakening TLS verification:

```powershell
openssl x509 -in 'C:\ProgramData\Sentinel-DNA\staging\pilot-9e5638b\tls\staging-server.crt' `
  -noout -subject -issuer -dates -fingerprint -sha256 -ext subjectAltName
openssl x509 -in 'C:\ProgramData\Sentinel-DNA\staging\pilot-9e5638b\tls\staging-ca.crt' `
  -noout -subject -issuer -dates -fingerprint -sha256 -ext basicConstraints
curl.exe --cacert 'C:\ProgramData\Sentinel-DNA\staging\pilot-9e5638b\tls\staging-ca.crt' --silent --show-error --fail-with-body https://127.0.0.1:18443/health
curl.exe --cacert 'C:\ProgramData\Sentinel-DNA\staging\pilot-9e5638b\tls\staging-ca.crt' --silent --show-error --fail-with-body https://127.0.0.1:18443/ready
```

If the certificate is not trusted by the approved browser, stop and resolve
trust through the approved certificate process. Do not use `-k`, disable
certificate verification, or add a private key to a trust store.

## 2. Manager authentication and CSRF

1. Open the private staging origin in the approved browser.
2. Inspect the visible login form before authentication.
3. Use the browser's secure authentication handoff. Do not enter credentials
   through a terminal or record them.
4. Verify the session response derives an authorized manager role (`admin` or
   `soc_manager`) through `/api/auth/me`.
5. Verify session cookies are Secure, HttpOnly where applicable, SameSite
   protected, and scoped to the staging origin.
6. In the browser's same-origin context, submit a manager-only write without a
   CSRF header. The expected result is HTTP `403` and no state change.

Safe missing-CSRF check from the authenticated same-origin browser console:

```javascript
fetch('/api/pilot-provisioning', {
  method: 'POST',
  credentials: 'same-origin',
  headers: {'Content-Type': 'application/json'},
  body: '{}'
}).then(async r => ({status: r.status, body: await r.text()}))
```

Record only the status and a redacted response classification. Do not run a
valid provisioning request in this manual preparation because no account or
credential creation is authorized.

## 3. Analyst authentication and RBAC

These checks require a separately approved synthetic analyst account. If it
does not exist, record `NOT_MEASURED` and stop the authenticated sequence; do
not create one here.

With the one approved analyst session:

1. Verify `/api/auth/me` derives role `analyst` and the expected synthetic
   tenant ID.
2. Verify the current pilot authorization is active, bounded, unexpired, and
   tenant-scoped.
3. Verify the analyst can access only the approved investigation/read paths.
4. Verify manager, administration, production, secrets, metrics, and runtime
   management surfaces are unavailable.

## 4. Tenant isolation and investigation workflow

Use synthetic data only and the reviewed canonical investigation workflow.

1. Submit one non-destructive synthetic investigation action with a valid CSRF
   token obtained inside the browser context.
2. Verify the action is accepted only through the canonical application path.
3. Request a known resource belonging to a different synthetic tenant. Expect
   explicit `403` or the endpoint contract's indistinguishable `404`.
4. Verify no foreign tenant identifier, record, evidence, or audit content is
   returned.
5. Record the case/job identifier and result reference, not sensitive payloads.

## 5. Audit, provenance, and AI controls

For each analyst action:

- Verify an audit event is created and contains a non-secret correlation
  reference, actor role, tenant scope, action, and UTC timestamp.
- Verify evidence provenance links the result to the synthetic input,
  execution path, and immutable or independently hashable reference.
- Verify audit and provenance references are tenant-scoped and do not expose
  another tenant's records.
- Verify AI output is clearly advisory, separate from the analyst conclusion,
  and requires an explicit human decision. AI output must not directly approve,
  execute, or close a case.
- Record disagreement, missing evidence, and human decision fields separately.

HTTP `200` by itself is insufficient for audit or provenance `PASS`.

## 6. Denial tests

Use only reviewed, safe authorization checks. Capture route class, request
method, HTTP status, and non-secret correlation ID. Do not attempt system
access outside the application boundary.

| Gate | Expected result |
| --- | --- |
| Cross-tenant resource | `403` or contract-defined indistinguishable `404` |
| Admin privilege escalation | Explicit `403`; no state change |
| Database access | Explicit `403`; no database endpoint or dump returned |
| Shell/container access | Explicit `403`; no command/session created |
| Destructive action | Explicit `403`; no mutation or external action |

If a known safe denial route is not available from the current deployment
contract, record `NOT_MEASURED`. Never substitute a guessed route or a real
destructive request.

## 7. Revocation and closeout

After the workflow, or immediately on any security concern:

1. Revoke the pilot authorization with a reason through the approved manager
   path.
2. Deactivate the synthetic analyst and invalidate active sessions.
3. Verify subsequent login, workspace, investigation, and feedback writes fail
   closed.
4. Preserve the audit and provenance references.
5. Restrict the private edge if compromise is suspected.

Record `PASS` only after post-revocation behavior is directly observed.

## 8. Final certification command

After manually filling the evidence file and changing its status to `VERIFIED`
after human evidence review, run this fail-closed, read-only validator. It
requires every gate, boundary field, audit/provenance reference, revocation
subcheck, and human approval to pass. It never contacts the application, issues
a URL, creates credentials, or changes evidence.

```powershell
node deployment/staging/scripts/validate_manual_analyst_pilot_evidence.mjs $EvidencePath
```

The final status is advisory to the human release authority. Human approval
remains the final decision, and any `NOT_MEASURED`, `FAIL`, `UNKNOWN`, or
missing field keeps the pilot blocked. The validator must be run against a
copied run file, never the template itself; the template must remain unchanged.
