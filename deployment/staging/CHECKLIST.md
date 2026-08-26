# Sentinel DNA controlled staging checklist

This checklist is a preparation gate for one bounded, non-production remote
analyst pilot. An unchecked item is `BLOCKED`; completion of this checklist
does not authorize production release. Do not record passwords, secret values,
activation tokens, private keys, customer data, or fabricated analyst results.

## 1. Custody and scope

- [ ] Confirm branch and reviewed full commit before staging preparation.
- [ ] Confirm RC1 and all release tags are unchanged.
- [ ] Confirm the staging run uses synthetic or explicitly approved
      non-customer data only.
- [ ] Confirm exactly one pilot tenant and one external analyst are in scope.
- [ ] Assign bounded pilot ownership to `Uwakwe chukwuebuka paul` only.
- [ ] Record planned pilot start and end as UTC values before access is issued.

## 2. Host and environment isolation

- [ ] Use a dedicated non-production host, project, or namespace.
- [ ] Use a non-production secret/configuration store; do not mount or source
      the existing production `.env`.
- [ ] Use a dedicated staging database or disposable staging PostgreSQL
      instance. Confirm no production network route, backup, or data volume is
      reachable.
- [ ] Set exactly these runtime controls:

      ```text
      SENTINEL_DNA_ENV=staging
      SENTINEL_DNA_PILOT_ACCESS_REQUIRED=1
      SENTINEL_DNA_SECURE_COOKIES=1
      FLASK_DEBUG=0
      ```

- [ ] Reject startup if the environment is `production`, debug is enabled,
      the pilot gate is disabled, or the database/secret source is classified
      as production.
- [ ] Confirm the populated configuration is held outside Git and its values
      are not printed in logs or evidence.
- [ ] Do not use the repository root `docker-compose.yml` or
      `deployment/docker-compose.yml` as an implicit staging contract; both
      are production-oriented. Use an approved staging runtime definition
      supplied by the infrastructure operator.

## 3. Private browser access boundary

- [ ] Provide a private HTTPS, VPN, or zero-trust front door. The value is
      `REMOTE_ANALYST_ENDPOINT = NOT_PROVIDED` until this check passes.
- [ ] Restrict access to the approved analyst identity and trusted founder or
      operator administration path.
- [ ] Expose only the application browser surface through the boundary.
- [ ] Keep database, Redis, SSH, shell, container runtime, repository,
      GitHub, admin, metrics, and management ports private or unavailable to
      the analyst.
- [ ] Verify TLS/certificate and hostname behavior from the analyst's actual
      network before handoff.
- [ ] Verify no public development server, wildcard public listener, or
      production DNS route exists.

## 4. Application startup and operability

- [ ] Start only the isolated non-production runtime using the approved
      operator procedure; do not perform this action in the repository gate.
- [ ] Verify `/health` and `/ready` through the private boundary.
- [ ] Verify secure cookies, CSRF, authentication, RBAC, tenant context, and
      fail-closed authorization.
- [ ] Confirm the application continues to use:

      ```text
      InvestigationCoordinator -> InvestigationOrchestrator -> RuntimeTaskExecutor
      ```

- [ ] Confirm audit and provenance services are writing tenant-scoped records.
- [ ] Confirm monitoring covers application health, authentication failures,
      authorization failures, investigation activity, feedback, and revocation.

## 5. Founder-controlled pilot onboarding

- [ ] Founder signs in through the private application surface with an
      authorized manager account. Do not create or distribute administrator
      credentials to the analyst.
- [ ] Provision exactly one dedicated analyst with
      `POST /api/pilot-provisioning` using a CSRF-protected manager session.
- [ ] Confirm the service creates one isolated synthetic pilot tenant and
      binds the analyst only to the `analyst` role.
- [ ] Record the returned provisioning, tenant, and authorization identifiers
      in protected operator notes only; do not place activation tokens in Git,
      logs, or evidence.
- [ ] Select only scenario identifiers present in the existing approved
      catalog. The initial requested categories are suspicious IP/domain,
      phishing URL, suspicious authentication, and endpoint compromise; do
      not invent identifiers if the catalog uses different names.
- [ ] Confirm explicit UTC authorization start/expiry and approved scenarios.
- [ ] Transfer the one-time activation mechanism through an approved secure
      channel. Never send it in source control, logs, tickets, or pilot
      evidence.
- [ ] Analyst activates their own credential through the existing activation
      endpoint and receives only the pilot workspace scope.
- [ ] Confirm the analyst cannot access another tenant, manager resources,
      production resources, repository, shell, SSH, database, secrets, SOAR,
      or destructive actions.

## 6. Evidence and monitoring

- [ ] Before execution, create a run-specific non-secret record under the
      approved `pilot-evidence/` process with status `NOT EXECUTED`.
- [ ] Record only the pilot ID, approved analyst identifier, tenant and
      authorization identifiers, scenario IDs, UTC start/end, reviewed
      application commit, environment classification, audit/provenance
      references, and evidence paths.
- [ ] Keep analyst conclusion, AI conclusion, agreement/disagreement,
      confidence, evidence used, missing evidence, contradictions, duration,
      and feedback as separate fields.
- [ ] Change status to `EXECUTED` only after the external analyst actually
      performs the workflow. Change to `VERIFIED` only after evidence review.
- [ ] Hash the finalized non-secret artifact with SHA-256 and verify the
      manifest independently. Never fabricate timestamps, outcomes, or
      analyst findings.

## 7. Backup and restore boundary

- [ ] Create only a non-production staging backup using the existing backup
      mechanism or approved operator tooling.
- [ ] Verify the backup contains no customer data, production data, secrets,
      activation tokens, private keys, or credentials.
- [ ] Restore only into a separate disposable staging target.
- [ ] Verify tenant, authorization, audit, provenance, health, and readiness
      behavior after restore.
- [ ] Do not overwrite a source database or perform a production restore.

## 8. Emergency shutdown and revocation

- [ ] Founder revokes the pilot authorization with a reason.
- [ ] Deactivate the analyst account and invalidate active sessions.
- [ ] Restrict or disable the private remote boundary if compromise is
      suspected.
- [ ] Confirm subsequent login, workspace, investigation, and feedback writes
      fail closed.
- [ ] Preserve non-secret audit, provenance, monitoring, and evidence records.
- [ ] Escalate through the approved protected support path; do not notify
      external parties from the pilot without separate authorization.

## 9. Founder validation sign-off

Record statuses as `PASS`, `NOT MEASURED`, `BLOCKED`, or `NOT PROVIDED`:

| Gate | Status | Evidence reference |
| --- | --- | --- |
| Non-production environment | NOT PROVIDED |  |
| Private remote endpoint | NOT PROVIDED |  |
| Application startup/health/readiness | NOT MEASURED |  |
| Dedicated staging database | NOT PROVIDED |  |
| Pilot tenant | NOT CREATED |  |
| Analyst account/activation | NOT CREATED |  |
| Pilot authorization | NOT CREATED |  |
| Audit/provenance/monitoring | NOT MEASURED |  |
| Backup/restore boundary | NOT MEASURED |  |
| Emergency shutdown | NOT MEASURED |  |
| Real analyst execution | NOT EXECUTED |  |
| Human-vs-AI measurement | NOT MEASURED |  |
| PostgreSQL integration | NOT MEASURED unless separately configured |  |
| Production readiness | BLOCKED |  |
