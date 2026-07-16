# Emulo Autopilot Worker

This directory contains the locally verified billing-integrity core for the
optional Emulo Autopilot cloud service. It does not deploy anything, create a
Polar checkout, or change access to the open-source local product.

Implemented locally:

- `GET /healthz`
- `POST /v1/billing/webhooks/polar`
- official Polar Standard Webhooks signature and schema verification
- bounded request bodies and payload-free event metadata
- idempotent, newer-wins D1 entitlement convergence
- fail-closed handling for unknown products, accounts, customers, and states

## Local verification

Requires Node.js 24 or newer.

```powershell
npm ci
npm run db:migrate:local
npm run typecheck
npm test
```

Copy `.dev.vars.example` to `.dev.vars` only for local testing. Put real secret
values directly into that ignored file or enter them interactively with
`wrangler secret put`; never paste them into chat, source files, shell history,
screenshots, or issue text.

`wrangler.jsonc` contains deliberately unusable product placeholders. The
monthly and yearly product IDs must be replaced only after the Polar sandbox
products exist.

## Provider actions intentionally deferred

No provider action is complete merely because this code exists. After the
authentication and server-created checkout/portal routes are implemented and
reviewed, the remaining operator actions are:

1. In Cloudflare, create or bind the free-tier Worker and D1 database. Record
   the Worker URL and D1 database ID as evidence; do not record a secret.
2. In Polar Sandbox, create the monthly and yearly founding products and place
   their nonsecret product IDs in the Worker configuration.
3. In Polar Sandbox under Settings > Webhooks, add the deployed endpoint ending
   in `/v1/billing/webhooks/polar`, select Raw format, and subscribe only to
   `subscription.created`, `subscription.active`, `subscription.updated`,
   `subscription.canceled`, `subscription.uncanceled`,
   `subscription.past_due`, and `subscription.revoked`.
4. Set the webhook secret interactively in Cloudflare and retain only a redacted
   screenshot or successful `202` sandbox delivery as verification.

Do not configure a live webhook or public checkout until sandbox purchase,
cancellation, past-due, revocation, duplicate, and replay behavior pass end to
end. Polar retries failed deliveries, so the endpoint should be live and tested
before a webhook is enabled.
