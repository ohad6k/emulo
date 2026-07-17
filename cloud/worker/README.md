# Emulo Autopilot Worker

This directory contains the Cloudflare Worker and D1 boundary for Emulo's
optional Autopilot founding beta. The open-source local Emulo engine does not
require this service or an account.

## Current surface

- `GET /healthz`
- `GET /account`
- `GET /account.css`
- `GET /account.js`
- `GET /emulo.svg`
- `GET /v1/account/status`
- `GET /v1/auth/github/start`
- `GET /v1/auth/github/callback`
- `POST /v1/billing/checkout`
- `POST /v1/billing/portal`
- `GET /v1/billing/complete`
- `POST /v1/billing/webhooks/polar`

The account and payment pages read a provider-neutral entitlement summary only
after authenticating the hashed Emulo browser session. They never serialize an
Emulo account ID, GitHub identity, Polar customer/subscription/event ID, raw
webhook payload, or provider diagnostic.

The completion URL is a verification surface, not an access grant. Only an
authenticated status read of a D1 entitlement written by a verified Polar
webhook may display an active founding-beta state. The page briefly polls the
safe status endpoint to handle normal webhook delay and remains pending if no
verified state arrives.

## Security and billing invariants

- GitHub OAuth uses single-use state, S256 PKCE, browser binding, and a hashed
  `Secure`, `HttpOnly`, `SameSite=Lax` browser session.
- GitHub sign-in requests no repository or email scope and does not persist the
  temporary provider token.
- Polar checkout and customer-portal sessions are created on the server for the
  authenticated Emulo account.
- The browser may choose only `monthly` or `yearly`; product IDs, external
  customer identity, IP forwarding, and return URLs are server-owned.
- Official Polar Standard Webhooks verification runs before any billing write.
- D1 event IDs are idempotent and newer provider-effective state wins.
- Unknown products, accounts, customer conflicts, malformed payloads, invalid
  signatures, replay-window violations, and oversized bodies fail closed.
- Checkout is controlled by `PAID_CHECKOUT_ENABLED` and defaults to `false`.
- Sandbox and production use separate hosts, products, tokens, and webhook
  secrets. Never copy a token or signing secret between environments.

## Verified sandbox evidence

The deployed Sandbox integration has completed one private monthly lifecycle.
Polar delivered `subscription.created`, `subscription.active`, and
`subscription.updated`; D1 recorded all three as applied and converged to one
active `founding-monthly` entitlement. After the test, the Worker was deployed
again with `PAID_CHECKOUT_ENABLED=false`. A live disabled checkout returned
`503`, and an unsigned webhook returned `403`.

This evidence proves the Sandbox path only. It does not prove Polar production
products, production secrets, payout/KYC readiness, a real-money purchase, a
refund, or a public launch.

## Verified production preparation

- The isolated `emulo-production` Worker and D1 database are deployed.
- GitHub's public client ID, the two private Polar product IDs, and the GitHub
  client secret are configured in their correct public/secret locations.
- Checkout is disabled. Live checkout returns `503 checkout-disabled`; portal
  and webhook routes return `503 unavailable` while their Polar secrets are
  absent.
- The public account shell and assets return `200`, signed-out status returns
  `401`, and GitHub auth redirects only to `github.com`.
- Count-only D1 checks before and after live refusal tests show zero accounts,
  customers, billing events, entitlements, browser sessions, and writes.

This proves safe production preparation, not a production purchase. The Polar
access token, raw-webhook signing secret, payout readiness, signed delivery,
real charge, portal, cancellation/refund, and public checkout remain gated.

## Local verification

Requires Node.js 24 or newer.

```powershell
npm ci
npm run db:migrate:local
npm run typecheck
npm test
npx wrangler deploy --dry-run --outdir .wrangler-dry-run
```

Copy `.dev.vars.example` to `.dev.vars` only for local testing. Put secret
values directly into that ignored file or enter them interactively with
`wrangler secret put`. Never paste secrets into chat, source files, command
arguments, screenshots, issues, or documentation.

## Safe deployment order

The repository contains `wrangler.production.jsonc` for the isolated
`emulo-production` service and D1 database. Its nonsecret production provider
identifiers are configured and checkout remains `false` until the remaining
Polar actions and real lifecycle proof pass. Validate it with:

```powershell
npm run verify:production-config
npx wrangler deploy --dry-run --config wrangler.production.jsonc
```

The config guard rejects Sandbox service/database drift, committed secret
values, partial product configuration, preview hostnames, and checkout
enablement. Only `GITHUB_CLIENT_SECRET` is deploy-required at the safe shell
stage. Runtime checks keep Polar checkout, portal, and webhooks unavailable
until their corresponding secrets are installed.

1. Keep `POLAR_SERVER=production` and `PAID_CHECKOUT_ENABLED=false` in the
   production service.
2. Apply D1 migrations, deploy with existing secret bindings preserved, and
   verify the signed-out account page plus fail-closed routes.
3. Sign in through GitHub and verify count-only D1 account, identity, and
   browser-session evidence without recording identifiers.
4. Create the scoped production Polar token and raw webhook through the
   authenticated dashboard only after payout/KYC state is confirmed. Enter
   both values directly into Cloudflare secret storage.
5. Prove one signed test delivery. An unsigned request must return `403` after
   the signing secret exists; before installation, the route returns `503`.
6. Open Polar's hosted portal and confirm it is tied to the same external Emulo
   account.
7. Perform one explicitly approved private real purchase, cancellation/refund,
   portal, and webhook lifecycle before enabling a public production checkout.
8. To stop new purchases, set `PAID_CHECKOUT_ENABLED=false` and redeploy. Keep
   signed webhooks running so existing customer state continues to converge.

Production dashboard actions and secret entry require the account owner or an
approved connected provider tool. Repository changes cannot prove those
external settings.
