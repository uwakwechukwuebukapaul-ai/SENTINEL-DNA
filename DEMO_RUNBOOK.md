# Sentinel DNA Enterprise Beta Demo Runbook

## Demo Goal

Show how Sentinel DNA turns a suspicious phishing alert into an evidence-backed analyst decision with traceable evidence, IOCs, MITRE mapping, risk assessment, recommendations, and audit output.

## Audience

- Security operations leaders.
- Detection engineering teams.
- Incident response teams.
- Security platform owners.
- Enterprise beta evaluators.

## Demo Setup

Before the demo:

1. Confirm the service is running.
2. Confirm `/healthz` and `/readyz` return healthy responses.
3. Register or prepare an owner account.
4. Confirm the active tenant ID.
5. Confirm the analyst workspace is reachable.
6. Prepare a phishing alert payload.

Suggested alert:

```json
{
  "sender": "security-alert@example-login.com",
  "subject": "Urgent MFA password verification required",
  "body": "Verify your password at https://example-login.com/security before access is suspended.",
  "severity": "high"
}
```

## Talk Track

Opening:

```text
Sentinel DNA is not just summarizing an alert. It creates an evidence-backed investigation record that an analyst can inspect, challenge, replay, and act on.
```

Core message:

```text
The platform moves from detection to decision by collecting evidence, enriching indicators, mapping attacker behavior, assessing risk, and producing an analyst-ready recommendation with auditability.
```

## Phishing Investigation Walkthrough

### 1. Submit The Alert

Run or trigger the phishing investigation through the existing investigation entry point.

Expected result:

- A case is created.
- The alert is normalized.
- The investigation plan is executed.
- Evidence and reasoning records are produced.

### 2. Evidence Collection

Show:

- Alert subject.
- Sender.
- Message body.
- URL indicators.
- Severity.
- Case metadata.

Explain:

```text
Sentinel DNA preserves the evidence trail so the final decision can be traced back to concrete observations.
```

### 3. IOC Enrichment

Show extracted indicators such as:

- Suspicious URL.
- Login-themed domain.
- Credential or MFA language.
- Sender/domain mismatch if present.

Explain:

```text
Indicators are enriched deterministically so the analyst can see why they mattered, not just that they were found.
```

### 4. MITRE Mapping

Expected phishing-aligned techniques may include:

- Initial Access.
- Phishing.
- Credential Access themes.

Explain:

```text
MITRE mapping gives the analyst a familiar threat-model vocabulary and helps connect alert evidence to attacker behavior.
```

### 5. Risk Assessment

Show:

- Risk level.
- Numeric score.
- Risk factors.
- Confidence signal.

Explain:

```text
Risk is calculated after evidence fusion so the score reflects the combined investigation context, not an isolated alert field.
```

### 6. Analyst Decision Output

Show:

- Executive summary.
- Decision intelligence.
- Recommended actions.
- Audit history.
- Analyst action controls.

Recommended demo decision:

```text
Escalate the investigation, block the suspicious URL, search for related mailbox activity, and require analyst approval before any containment action.
```

### 7. Record Analyst Action

Record one of:

- Confirm finding.
- Dismiss finding.
- Escalate.
- Add note.

Explain:

```text
The analyst remains in control. Sentinel DNA recommends and explains; it does not silently execute high-impact response actions.
```

## Demo Success Criteria

The demo is successful when the audience sees:

- Alert-to-case conversion.
- Evidence collection.
- IOC enrichment.
- MITRE mapping.
- Risk and confidence explanation.
- Analyst-ready decision output.
- Audit history.
- Human approval posture for response.

## Common Questions

Does Sentinel DNA replace analysts?

```text
No. It reduces investigation assembly work and gives analysts evidence-backed recommendations.
```

Does Sentinel DNA execute containment actions automatically?

```text
No. The beta posture is human-approved response.
```

Can outputs be audited?

```text
Yes. Cases include evidence, reasoning, audit, lineage, and replay-oriented records.
```

Can it run in a private enterprise environment?

```text
Yes. The beta deployment supports private infrastructure with PostgreSQL, Redis, Kubernetes or Docker Compose, and customer-controlled secrets.
```
