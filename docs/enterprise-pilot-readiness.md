# Sentinel DNA Enterprise Pilot Readiness

## Demonstration workflow

The supported pilot path is:

1. Select a scenario from `GET /api/pilot/scenarios`.
2. Submit an alert to `POST /api/pilot/investigations`.
3. Follow the returned stages through evidence collection, enrichment, MITRE mapping, reasoning, and report generation.
4. Open the tenant-scoped analyst workspace or `GET /api/investigations/<case_id>/view`.
5. Submit an analyst outcome through `POST /api/investigations/<case_id>/feedback`.
6. Review `GET /api/investigations/<case_id>/metrics`.
7. Retrieve the customer-facing summary from `GET /api/pilot/investigations/<case_id>/summary`.

The pilot workflow delegates execution to `InvestigationCoordinator`. It does not create a second investigation engine or persistence boundary.

## Supported scenarios

- Phishing compromise
- Suspicious authentication activity
- Malware execution
- Credential theft
- Cloud account compromise

Each scenario declares alert metadata, evidence requirements, expected workflow stages, and analyst review points. Scenario data is demonstration guidance; it is not a security conclusion.

## Deployment checks

Before a customer demonstration:

- Set `SENTINEL_DNA_ENV=production`.
- Set a unique 32+ character `SENTINEL_DNA_SECRET_KEY`.
- Set `SENTINEL_DNA_DB_PATH` to persistent writable storage.
- Run database initialization and backup validation.
- Use one Gunicorn worker while SQLite is the persistence boundary.
- Verify `/health` and `/ready` before the demo.
- Confirm tenant membership and analyst authorization with a non-admin test account.
- Run the required compile and regression suites.

Never place credentials, tokens, raw evidence, or provider responses in logs or demo payloads.
