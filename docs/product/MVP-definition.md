# Sentinel DNA MVP Definition

## Goal

Provide an analyst with a usable, evidence-first investigation workflow over
synthetic data: review a tenant-scoped case, run the canonical investigation,
inspect evidence and an advisory report, record an attributed analyst decision,
and sign out securely.

## In scope

- Verified public analyst registration and authenticated sign-in.
- The canonical WSGI workspace at `/workspace` and `/workspace/`.
- A repeatable synthetic PowerShell investigation, disabled by default in
  production and isolated by tenant.
- Durable execution status and evidence references, with provenance,
  uncertainty, and confidence visible to the analyst.
- Tenant-scoped, append-only analyst feedback with CSRF and audit controls.
- Safe, truthful behavior when investigation, report, or feedback operations
  are unavailable.

## Out of scope

Customer data, autonomous remediation, unreviewed AI decisions, real analyst
activation, external evaluation, and production or staging release approval.
These require separate authorization and operational evidence.

## Acceptance

The measurable workflow and its local synthetic demonstration are defined in
[`SYNTHETIC_ANALYST_MVP_ACCEPTANCE.md`](SYNTHETIC_ANALYST_MVP_ACCEPTANCE.md).
Release readiness remains tracked separately in
[`SOC_ANALYST_PILOT_READINESS.md`](../release/SOC_ANALYST_PILOT_READINESS.md).
