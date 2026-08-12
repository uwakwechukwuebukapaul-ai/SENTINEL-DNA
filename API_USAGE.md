# Sentinel DNA API Usage

Sentinel DNA investigations start through `InvestigationCoordinator.investigate(case_id, alert)`.

```python
from sentinel_dna.investigation import InvestigationCoordinator

coordinator = InvestigationCoordinator(data_dir="data")

result = coordinator.investigate(
    "case-001",
    {
        "sender": "security-alert@example-login.com",
        "subject": "Urgent MFA password verification required",
        "body": "Verify at https://example-login.com/security",
        "severity": "high",
    },
)

payload = result.to_dict()
```

The returned `InvestigationResult` contains:

- `plan_name`
- `results`
- `errors`

The `results` payload includes case details, alert, executed tasks, evidence, graph, IOC intelligence, MITRE mappings, fusion verdict, risk, confidence, reasoning, decision intelligence, recommendations, report, provenance, replay, uncertainties, and audit trail.

Invalid inputs are rejected before execution:

- `case_id` must be a non-empty string.
- `case_id` cannot include path separators.
- `alert` must be a non-empty dictionary or expose `to_investigation_alert()`.

## SaaS API

The Flask API exposes a production-oriented foundation for identity, tenancy, authorization, and usage metering.

Authentication:

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

Service operations:

- `GET /healthz`
- `GET /readyz`
- `GET /version`
- `GET /metrics` (restrict to the monitoring network)

Organizations:

- `POST /organizations`
- `GET /organizations`
- `GET /organizations/<id>`

Memberships:

- `GET /organizations/<id>/members`
- `POST /organizations/<id>/members`

Usage:

- `GET /usage`
- `GET /usage/<metric>`

Authenticated requests use:

```text
Authorization: Bearer <token>
X-Sentinel-Org: <organization_id>
```

The SaaS layer records usage events, but billing is not implemented yet.
