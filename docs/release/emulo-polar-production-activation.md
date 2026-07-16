# Emulo Polar Production Activation

**Status:** Prepared, not activated  
**Last checked:** 2026-07-17
**Owner:** Ohad  
**Safety default:** Production checkout disabled

This runbook moves Emulo from a proven Polar Sandbox lifecycle to a private
real-money founding-beta test. It does not authorize a public launch or a real
charge by itself.

## What is already proven

- GitHub OAuth creates a bounded Emulo account and hashed browser session.
- Server-created Polar Sandbox checkout binds the external customer ID to the
  authenticated Emulo account.
- Polar Sandbox delivered `subscription.created`, `subscription.active`, and
  `subscription.updated`; all three were applied and converged to one active
  monthly entitlement.
- The completion page reads the webhook-backed D1 entitlement rather than
  treating the checkout redirect as success.
- Portal creation, invalid signatures, duplicate events, replay, unknown
  products/accounts, provider failure, and disabled checkout have automated
  coverage.
- The deployed Sandbox checkout gate is disabled.

This proves Sandbox only. Polar documents Sandbox as a separate environment
with isolated organizations, products, tokens, customers, and money movements:
<https://polar.sh/docs/integrate/sandbox>.

## Current official provider facts

- Production API base URL: `https://api.polar.sh/v1`; Sandbox API base URL:
  `https://sandbox-api.polar.sh/v1`. Tokens are environment-specific:
  <https://polar.sh/docs/api-reference/introduction>.
- An Organization Access Token is created under **Settings > General >
  Developers > New Token**. It must remain server-side:
  <https://polar.sh/docs/integrate/oat>.
- Emulo needs only `checkouts:write` for checkout creation and
  `customer_sessions:write` for hosted portal sessions:
  <https://polar.sh/docs/api-reference/checkouts/create-session> and
  <https://polar.sh/docs/api-reference/customer-portal/sessions/create>.
- Raw webhook endpoints follow Standard Webhooks signing. Polar recommends Raw
  for custom integrations and separate Sandbox testing:
  <https://polar.sh/docs/integrate/webhooks/endpoints>.
- Subscription event sequences can include both `subscription.updated` and a
  more specific lifecycle event. Creation may occur before the subscription is
  active, which is why Emulo does not grant access from `created` or redirect
  arrival alone: <https://polar.sh/docs/integrate/webhooks/events> and
  <https://polar.sh/docs/api-reference/webhooks/subscription.created>.
- Polar's hosted portal lets customers cancel, obtain invoices/receipts, and
  update a failed payment method without Emulo touching card data:
  <https://polar.sh/docs/features/customer-portal/introduction>.
- Israel is currently listed as a supported payout country through Stripe
  Connect Express: <https://polar.sh/docs/merchant-of-record/supported-countries>.
- A payout account is connected under **Finance > Setup**:
  <https://polar.sh/docs/features/finance/accounts>.
- Current public Starter pricing is free monthly with `5% + $0.50` per
  transaction for organizations created on or after 2026-05-27. Earlier
  organizations may retain Early Member pricing. The Emulo production
  dashboard is the final receipt for the actual plan:
  <https://polar.sh/resources/pricing>.
- Polar is the Merchant of Record for international sales tax, but Ohad remains
  responsible for local income/revenue tax:
  <https://polar.sh/docs/merchant-of-record/introduction>.

## Required environment separation

Production must not reuse the Sandbox D1 database, OAuth callback, token,
webhook secret, products, or provider customer records. Use a separate
Cloudflare Worker service and D1 database for production. This prevents the
existing Sandbox entitlement from ever being interpreted as paid production
access and allows Sandbox to remain available for future testing.

Required production resources:

| Resource | Required value/evidence | Owner |
| --- | --- | --- |
| Cloudflare Worker | Separate production service; checkout disabled | Codex can create/deploy after confirmation |
| Cloudflare D1 | Empty production database with all migrations | Codex can create/migrate after confirmation |
| GitHub OAuth App | Production homepage and exact production callback | Ohad must register/confirm in GitHub |
| Polar organization | Production Emulo organization | Ohad confirms in Polar |
| Polar payout account | Finance page shows connected/review state | Ohad completes Stripe identity/bank flow |
| Polar products | Recurring `$9/month` and `$79/year`, no trial | Ohad or approved provider automation |
| Polar OAT | Production-only, `checkouts:write` + `customer_sessions:write` | Ohad creates; enter directly into Cloudflare |
| Polar webhook | Raw endpoint with exact seven events | Ohad or approved provider automation |
| Webhook secret | Production-only secret | Enter directly into Cloudflare |

No password, OAT, client secret, webhook secret, cookie, bank detail, tax ID, or
identity document may be pasted into chat, committed, placed in command
arguments, or shown in screenshots.

### Current production preparation receipt

- Cloudflare D1 `emulo-autopilot-production` exists in the EEUR region.
- All five repository migrations are applied.
- Count-only verification shows 0 accounts, 0 entitlements, and 0 billing
  events, so no Sandbox identity or purchase crossed the boundary.
- `wrangler.production.jsonc` points only to the production D1 resource, uses
  `POLAR_SERVER=production`, and keeps `PAID_CHECKOUT_ENABLED=false`.
- The config validates and bundles in a Wrangler dry-run.
- GitHub client ID, GitHub client secret, and both Polar product IDs are
  configured. Production Worker version
  `2a49f764-d11f-4fed-93a3-984f42cc862d` is deployed with checkout and preview
  hostnames disabled.
- Live health, account, and asset routes return `200`; signed-out account status
  returns `401`; GitHub auth redirects to `github.com`; checkout, portal, and
  the not-yet-configured webhook return safe `503` states. Count-only D1
  queries before and after returned zero rows and zero writes.
- The production Polar access token and raw-webhook signing secret remain
  deliberately absent pending the owner/provider steps below.

## Phase 1: owner/provider readiness

Ohad performs these authenticated dashboard actions because they may require
identity verification, bank details, legal acceptance, or 2FA.

1. Open the production Polar dashboard, select the Emulo organization, and
   confirm the organization name, slug, country, website, support identity, and
   visible checkout branding.
2. Open **Finance**. If no payout account is connected, choose **Setup** and
   complete the Stripe Connect Express flow. A redacted screenshot may show
   only `connected`, `pending review`, or the exact blocking status.
3. Open the current Polar plan/billing page and record only the plan label and
   fee schedule. Do not assume Early Member status from an older personal
   account; the organization creation date controls it.
4. Confirm Polar permits the product category and that the checkout description
   accurately promises founding-beta cloud continuity, not guaranteed AI
   performance or bundled model usage.

Stop if the production organization is suspended, payout/identity review has a
blocking error, or its visible seller identity is incorrect.

## Phase 2: production infrastructure with checkout disabled

Codex may perform these steps after Phase 1 has a redacted receipt:

1. Confirm the existing separate production D1 database and its five applied
   migrations.
2. Complete the production Wrangler configuration with only nonsecret values:
   production service name, production D1 binding/ID, exact production base URL,
   production GitHub client ID, production Polar product IDs, and
   `PAID_CHECKOUT_ENABLED=false`.
3. Run `npm run verify:production-config` and confirm the result changes from
   `provider-actions-required` to `nonsecret-config-ready` only after the
   GitHub client ID and both Polar product IDs are present.
4. Deploy the production Worker while preserving Cloudflare secrets. Only the
   GitHub client secret is deploy-required at this gate; both Polar secrets are
   installed later and runtime billing routes fail closed while they are absent.
5. Verify `/healthz`, signed-out `/account`, `/account.css`, `/account.js`, and
   `/emulo.svg` without enabling checkout.
6. Verify unauthenticated `/v1/account/status` returns `401`, checkout returns
   `503`, and the not-yet-configured webhook returns `503` without a D1 write.
   After the Polar signing secret is installed, an unsigned webhook must return
   `403`.

Record the Worker URL, Worker version, and D1 database ID. These are nonsecret.
Do not record any session/account/provider identifiers.

## Phase 3: production GitHub OAuth

In GitHub **Settings > Developer settings > OAuth Apps**, register a dedicated
production Emulo app.

- Application name: `Emulo`
- Homepage URL: exact HTTPS production Worker account origin
- Authorization callback URL: exact production origin followed by
  `/v1/auth/github/callback`
- Device Flow: disabled

Put the nonsecret client ID in production Worker configuration. Enter the
client secret interactively with Cloudflare secret storage. Then sign in once
and verify one production account, one GitHub identity, and one live browser
session using count-only D1 queries.

## Phase 4: production Polar products and server token

Create two recurring products. Polar locks the billing cycle/price type at
creation, so inspect before saving.

### Monthly

- Name: `Emulo Pro Monthly`
- Recurring interval: monthly
- Price: `$9 USD`
- Trial: none
- Promise: managed continuity, cross-agent/device orchestration as delivered,
  founding-beta support, and inspectable/reversible behavior
- Exclusions: no model tokens, no guaranteed productivity result, no loss of
  open-source local ownership

### Annual

- Name: `Emulo Pro Annual`
- Recurring interval: yearly
- Price: `$79 USD`
- Trial: none
- Same promise and exclusions as monthly

Copy only the nonsecret production product IDs into production Worker
configuration. Keep checkout disabled.

Create one production OAT under **Settings > General > Developers**:

- descriptive name tied to the production Worker;
- an explicit expiry/rotation date;
- `checkouts:write` scope;
- `customer_sessions:write` scope;
- no broader scopes.

Enter it directly as the production Worker's `POLAR_ACCESS_TOKEN` secret.
Never display it again.

## Phase 5: production webhook

Under Polar production **Settings > Webhooks**, create one endpoint:

- URL: exact production Worker origin followed by
  `/v1/billing/webhooks/polar`
- Format: `Raw`
- Events:
  - `subscription.created`
  - `subscription.active`
  - `subscription.updated`
  - `subscription.canceled`
  - `subscription.uncanceled`
  - `subscription.past_due`
  - `subscription.revoked`

Enter the production webhook signing secret directly into Cloudflare as
`POLAR_WEBHOOK_SECRET`. Keep checkout disabled. Use the Polar dashboard's test
delivery if available and verify a valid delivery is accepted without granting
an entitlement for an unknown account.

## Phase 6: explicitly approved private real-money lifecycle

This phase creates a real charge and requires Ohad's explicit approval at that
moment.

1. Confirm full tests/typecheck and the production deploy version.
2. Enable checkout only for the bounded private test window.
3. Sign in with the production GitHub account.
4. Purchase the monthly plan with a real card.
5. Confirm the completion page stays pending until a signed webhook applies.
6. Confirm D1 shows one active production entitlement and applied lifecycle
   events using count/state-only queries.
7. Open the hosted portal from Emulo and confirm the correct plan.
8. Cancel/refund using the exact agreed test path. A refund is not assumed to
   generate the same subscription event sequence as cancellation; observe and
   record the real events without payloads.
9. Confirm the customer-visible Emulo state converges correctly.
10. Disable checkout immediately after the lifecycle test.

Do not use a real customer's card or email for this test. Do not publish the
checkout while the test is running.

## Public enablement gate

Public founding checkout may be enabled only when all boxes are true:

- [ ] Production payout/organization state is accepted.
- [ ] Production monthly and annual products show exact prices/intervals.
- [ ] Production OAT has only the two required scopes.
- [ ] Production webhook is Raw and subscribed to exactly the seven events.
- [ ] GitHub production callback and sign-in work.
- [ ] Real purchase creates an active entitlement only after signed webhook.
- [ ] Hosted portal opens for the authenticated external customer.
- [ ] Cancellation/refund lifecycle converges without manual D1 edits.
- [ ] Checkout can be disabled without disabling webhook processing.
- [ ] Customer-facing promise, privacy, refund, support, and beta limitations
  are visible before purchase.
- [ ] Ohad explicitly approves public enablement.

## Rollback

If any billing, provider, or UI failure appears:

1. Set `PAID_CHECKOUT_ENABLED=false` in the production Worker configuration.
2. Deploy the safe configuration.
3. Verify checkout returns `503`.
4. Keep the production webhook endpoint and secret active so existing customer
   lifecycle state continues to converge.
5. Do not delete D1 events, customers, entitlements, or provider subscriptions.
6. Record the Worker version, observed symptom, affected route/state, and Polar
   delivery status without sensitive payloads.
7. Fix and verify in Sandbox first, then repeat the bounded production proof.

This rollback stops new purchases. It does not cancel existing customers;
cancellation/refund remains an explicit Polar action.
