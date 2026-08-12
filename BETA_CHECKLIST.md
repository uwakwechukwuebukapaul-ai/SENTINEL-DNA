# Sentinel DNA Enterprise Beta Checklist

Use this checklist before handing Sentinel DNA to a private enterprise beta customer.

## Deployment Readiness

- [ ] Target environment approved for private beta.
- [ ] Python/runtime image validated.
- [ ] PostgreSQL provisioned.
- [ ] Redis provisioned for multi-instance deployment.
- [ ] Persistent storage plan confirmed.
- [ ] TLS termination configured.
- [ ] Kubernetes manifests or Docker Compose deployment reviewed.
- [ ] Secrets loaded through approved secret-management path.
- [ ] `SENTINEL_DNA_ENV=production` set for production-like deployment.
- [ ] `SENTINEL_DNA_SAAS_DATABASE_URL` configured.
- [ ] `SENTINEL_DNA_REDIS_URL` configured for multi-instance deployment.
- [ ] `SENTINEL_DNA_ENCRYPTION_KEY` configured.
- [ ] `SENTINEL_DNA_RATE_LIMIT_PER_MINUTE` configured.
- [ ] `/healthz` returns healthy status.
- [ ] `/readyz` returns ready status.
- [ ] `/version` returns service metadata.
- [ ] `/metrics` is private through network controls or token mode.

## Security Checks

- [ ] First owner account created through approved onboarding path.
- [ ] Tenant organization created.
- [ ] At least one backup owner assigned.
- [ ] Admin users assigned only where required.
- [ ] Analyst users assigned least-privilege roles.
- [ ] Viewer users assigned only read access.
- [ ] Test outsider account cannot access tenant resources.
- [ ] Billing routes require owner/admin role.
- [ ] Stripe webhook secret configured if Stripe test billing is enabled.
- [ ] Metrics endpoint exposure reviewed.
- [ ] Logs checked for absence of passwords, tokens, and request bodies.
- [ ] PostgreSQL backups encrypted or protected by customer controls.
- [ ] Redis access restricted to service network.
- [ ] NetworkPolicy or equivalent segmentation enabled.

## Onboarding Steps

- [ ] Send customer quickstart.
- [ ] Send admin guide.
- [ ] Send security whitepaper.
- [ ] Send architecture overview.
- [ ] Schedule deployment walkthrough.
- [ ] Confirm beta stakeholders and escalation contacts.
- [ ] Confirm customer success criteria.
- [ ] Create initial owner account.
- [ ] Create tenant organization.
- [ ] Invite beta users.
- [ ] Run first login validation.
- [ ] Run first phishing investigation.
- [ ] Record first analyst decision.
- [ ] Review audit history with customer.

## Demo Validation

- [ ] Phishing payload prepared.
- [ ] Alert submission path tested.
- [ ] Evidence collection visible.
- [ ] IOC enrichment visible.
- [ ] MITRE mapping visible.
- [ ] Risk score visible.
- [ ] Confidence signal visible.
- [ ] Recommended actions visible.
- [ ] Analyst action recorded.
- [ ] Case audit history updated.

## Operations Checks

- [ ] Health checks monitored.
- [ ] Readiness checks monitored.
- [ ] JSON logs collected.
- [ ] Metrics scraped.
- [ ] Authentication denials monitored.
- [ ] Authorization denials monitored.
- [ ] Rate limiter fallback logs monitored.
- [ ] 5xx responses monitored.
- [ ] Worker failures monitored if workers are enabled.
- [ ] Backup job scheduled.
- [ ] Restore procedure tested.
- [ ] Rollback plan approved.

## Support Checklist

- [ ] Customer support channel created.
- [ ] Named technical owner assigned.
- [ ] Named security contact assigned.
- [ ] Named product contact assigned.
- [ ] Incident response path agreed.
- [ ] Beta feedback process agreed.
- [ ] Known limitations shared.
- [ ] Weekly check-in scheduled.
- [ ] Exit criteria agreed.

## Launch Hold Conditions

Do not proceed with beta handoff if any of these are true:

- [ ] Production-like environment cannot pass readiness checks.
- [ ] Tenant isolation validation fails.
- [ ] Metrics endpoint is publicly exposed without protection.
- [ ] Secrets are committed to source control.
- [ ] PostgreSQL backup/restore path is not understood.
- [ ] Customer cannot identify an owner/admin for the tenant.
- [ ] Demo investigation cannot produce evidence-backed output.

## Beta Handoff Completion

The beta handoff is complete when:

- [ ] Customer has documentation.
- [ ] Customer can log in.
- [ ] Customer can run a phishing investigation.
- [ ] Customer can review evidence, IOCs, MITRE mapping, risk, and recommendations.
- [ ] Customer can record an analyst decision.
- [ ] Operations can monitor health, readiness, logs, and metrics.
- [ ] Remaining launch risks are documented and accepted.
