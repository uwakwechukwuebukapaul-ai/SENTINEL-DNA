# Sentinel DNA Email Delivery Configuration

Sentinel DNA account registration, email sign-in, and password recovery require an explicitly configured email provider. Health/readiness checks do not prove that email delivery is configured.

## SMTP relay

Configure the application environment through the approved secret/configuration manager. Do not commit credentials or paste them into tickets, chat, logs, or evaluation records.

| Variable | Required | Description |
|---|---|---|
| `SENTINEL_DNA_EMAIL_PROVIDER` | Yes | Set to `smtp` |
| `SENTINEL_DNA_SMTP_HOST` | Yes | SMTP relay hostname |
| `SENTINEL_DNA_SMTP_PORT` | No | Defaults to `587` |
| `SENTINEL_DNA_SMTP_SECURITY` | No | `starttls` by default; use `ssl` for implicit TLS |
| `SENTINEL_DNA_EMAIL_FROM` | Yes | Verified sender address permitted by the relay |
| `SENTINEL_DNA_SMTP_USERNAME` | Conditional | SMTP username, if the relay requires authentication |
| `SENTINEL_DNA_SMTP_PASSWORD` | Conditional | SMTP password, if the relay requires authentication |

If SMTP authentication is used, both username and password must be configured. STARTTLS or implicit TLS is always used; plaintext SMTP is not supported. The adapter uses a bounded connection timeout and returns a generic delivery failure without logging the OTP, recipient, credentials, or raw provider response.

## Environment boundaries

- `development`: local development compatibility and test providers may be used intentionally.
- `testing` / `test`: use the in-memory test provider in automated tests.
- `staging` and `production`: configure a real SMTP relay explicitly. The console/test providers are not accepted as delivery providers for these environments.
- If delivery is not configured or the relay rejects the message, registration must not be treated as successful. The UI asks the user to retry; the API keeps its generic response to avoid disclosing account eligibility.

## Verification after configuration

1. Apply the variables through the approved non-production configuration process.
2. Restart/redeploy only through the normal approved runtime workflow; this document does not authorize a deployment.
3. Request a registration code for a controlled test mailbox.
4. Verify the code and create a synthetic test account.
5. Confirm a second request/session cannot reuse the verification challenge.
6. Confirm logs and audit records contain no OTPs, SMTP credentials, session cookies, or activation secrets.
7. Run the focused auth tests and the full regression suite before allowing external evaluation.
