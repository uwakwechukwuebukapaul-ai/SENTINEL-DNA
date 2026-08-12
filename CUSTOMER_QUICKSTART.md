# Sentinel DNA Enterprise Beta Customer Quickstart

This quickstart is for private enterprise beta customers evaluating Sentinel DNA as an evidence-backed investigation workspace.

## Installation Requirements

Required for a production-like beta:

- Windows, macOS, or Linux workstation for local validation.
- Python 3.10 or newer.
- PostgreSQL for SaaS identity, tenancy, usage, billing, and audit-adjacent state in shared environments.
- Redis for distributed sessions and rate limiting in multi-instance deployments.
- Kubernetes or Docker Compose for production-like deployment.
- TLS termination through the enterprise ingress, load balancer, or reverse proxy.
- Access to a managed secret store or Kubernetes Secret for production secrets.

Optional:

- Stripe test-mode credentials for billing checkout validation.
- Centralized log collection for JSON service logs.
- Prometheus-compatible monitoring for `/metrics`.

## Environment Setup

Create a virtual environment for local beta validation:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

For enterprise beta deployment, configure these environment variables:

```text
SENTINEL_DNA_ENV=production
SENTINEL_DNA_DATA_DIR=/var/lib/sentinel-dna
SENTINEL_DNA_SAAS_DATABASE_URL=postgresql://sentinel:<password>@postgres:5432/sentinel
SENTINEL_DNA_REDIS_URL=redis://redis:6379/0
SENTINEL_DNA_SECRET_BACKEND=environment
SENTINEL_DNA_ENCRYPTION_KEY=<base64-encoded-32-byte-key>
SENTINEL_DNA_RATE_LIMIT_PER_MINUTE=120
SENTINEL_DNA_METRICS_PRIVATE=true
SENTINEL_DNA_METRICS_TOKEN=<monitoring-token>
```

Stripe billing validation is optional for beta:

```text
STRIPE_SECRET_KEY=<stripe-test-secret>
STRIPE_WEBHOOK_SECRET=<stripe-webhook-secret>
STRIPE_PRICE_IDS={"plan-free":"price_...","plan-team":"price_..."}
```

Start the local web workspace:

```powershell
python -m sentinel_dna.workspace.web_app
```

Open:

```text
http://127.0.0.1:5000
```

Validate service health:

```text
/healthz
/readyz
/version
```

## First Login

Use the API to register the first owner account and organization:

```http
POST /auth/register
Content-Type: application/json

{
  "email": "owner@example.com",
  "password": "correct horse battery staple",
  "display_name": "Owner",
  "organization_name": "Acme SOC"
}
```

Then log in:

```http
POST /auth/login
Content-Type: application/json

{
  "email": "owner@example.com",
  "password": "correct horse battery staple"
}
```

Use the returned bearer token and organization ID for tenant-scoped requests:

```http
Authorization: Bearer <token>
X-Sentinel-Org: <organization_id>
```

## First Investigation Workflow

1. Confirm the tenant has an active beta subscription or entitlement state.
2. Submit a phishing-style alert through the investigation entry point.
3. Review the generated case in the analyst workspace.
4. Inspect evidence, IOCs, risk, MITRE mapping, confidence, reasoning, and recommendations.
5. Record an analyst decision: confirm finding, dismiss finding, escalate, or add note.
6. Export or review the case audit history for beta feedback.

Example investigation payload:

```python
from sentinel_dna.investigation import InvestigationCoordinator

coordinator = InvestigationCoordinator(data_dir="data")
result = coordinator.investigate(
    "case-beta-001",
    {
        "sender": "security-alert@example-login.com",
        "subject": "Urgent MFA password verification required",
        "body": "Verify at https://example-login.com/security",
        "severity": "high",
    },
)

print(result.to_dict())
```

Expected analyst output:

- Evidence-backed investigation summary.
- Extracted indicators.
- IOC intelligence.
- MITRE ATT&CK mapping.
- Risk score and explanation.
- Confidence signal.
- Recommended analyst actions.
- Audit and replay records.

## Beta Success Criteria

The first customer handoff is successful when:

- The customer can deploy the API in a private environment.
- The first owner can register, log in, and access the tenant workspace.
- A phishing investigation produces deterministic evidence-backed output.
- Analyst decisions are recorded in the case audit history.
- Health, readiness, logs, and metrics are visible to operations.
