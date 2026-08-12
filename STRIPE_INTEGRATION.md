# Stripe Integration

Stripe is implemented as a billing provider adapter. Sentinel DNA billing remains the source of business rules, tenant authorization, entitlement checks, lifecycle validation, idempotency, and audit.

## Architecture

```text
Authenticated billing API
-> tenant authorization
-> Sentinel DNA billing domain
-> StripeProvider adapter
-> Stripe API
```

Checkout creates a Stripe checkout session and returns the Stripe URL. It never activates a Sentinel DNA subscription. Subscription state changes enter Sentinel DNA only through signed Stripe webhooks or audited reconciliation workflows.

## Configuration

Set all Stripe variables together:

- `STRIPE_SECRET_KEY`: Stripe API secret key.
- `STRIPE_WEBHOOK_SECRET`: Stripe endpoint signing secret.
- `STRIPE_PRICE_IDS`: JSON object mapping Sentinel DNA plan IDs to Stripe price IDs, for example `{"plan-free":"price_...","plan-team":"price_..."}`.

Secrets must come from the deployment secret manager. Do not hardcode them in source, images, Helm values, or tests.

If any Stripe setting is missing while Stripe is enabled, configuration fails closed. Without complete Stripe configuration, provider-backed checkout and webhook operations are unavailable.

## Webhook Security Model

`POST /billing/webhook` requires the `Stripe-Signature` header. Sentinel DNA verifies:

- timestamp freshness
- HMAC SHA-256 signature
- valid JSON event envelope
- duplicate event protection using `billing_provider_events`

Unsigned, stale, malformed, or replayed payloads are rejected or ignored idempotently. Supported events:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_failed`

Webhook payload metadata must include `tenant_id` and `plan_id` where subscription state is updated. Client-submitted billing state is ignored.

## Failure Handling

- Checkout creation failure does not activate a subscription.
- Missing provider configuration returns a closed failure instead of falling back to local success.
- Duplicate webhook events return a duplicate status and do not reapply state.
- Reconciliation drift is audited as `billing_reconciliation_required`.
- Failed payments and canceled provider subscriptions require commercial review before access decisions are relaxed.

## Deployment Requirements

- Configure Stripe webhook endpoint to `POST /billing/webhook`.
- Restrict secrets to the runtime environment.
- Run PostgreSQL migrations, including `003_stripe_provider_events.postgresql.sql`.
- Monitor billing audit events and reconciliation findings.
- Keep Sentinel DNA tenant IDs in Stripe metadata for subscriptions and checkout sessions.
