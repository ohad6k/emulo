# Emulo Autopilot Polar Billing Integrity Implementation Plan

**Goal:** Build the fail-closed, provider-neutral billing integrity core and a locally tested Cloudflare Worker webhook vertical slice before touching Polar or Cloudflare dashboards.

**Architecture:** Add an isolated TypeScript Worker under `cloud/worker`. Pure normalization maps Polar events into Emulo entitlement states. The adapter verifies Polar Standard Webhooks using Polar's official SDK, writes only bounded metadata to D1, and converges duplicate/out-of-order events through conditional upserts. Redirects never grant access. Account authentication, checkout creation, portal creation, encrypted sync, and deployment remain later gated slices.

**Current primary-source inputs (checked 2026-07-16):** Cloudflare recommends `wrangler.jsonc`, D1 migrations are versioned SQL, D1 `batch()` is transactional, and the Workers Vitest integration runs locally. Polar recommends sandbox development, official Standard Webhooks validation, and subscription lifecycle events; scheduled cancellation keeps the subscription active until revocation.

## Boundaries

- No secret value enters Git, terminal output, chat, tests, fixtures, or browser JavaScript.
- No Cloudflare resource, D1 database, DNS record, Worker route, Polar product, webhook endpoint, or token is created in this slice.
- Only verified webhooks or later server reconciliation may change entitlement.
- Unknown product, customer, account, event shape, state, or signature fails closed.
- Payload bodies are never stored or logged; billing events store only ID, type, timestamps, result, and SHA-256.
- The open-source local product remains fully operational without billing or cloud.
- Internal founding-beta caps and public checkout stay disabled.

### Task 1: Worker scaffold and deterministic entitlement normalization

**Files:**
- Create: `cloud/worker/package.json`
- Create: `cloud/worker/package-lock.json`
- Create: `cloud/worker/tsconfig.json`
- Create: `cloud/worker/wrangler.jsonc`
- Create: `cloud/worker/vitest.config.ts`
- Create: `cloud/worker/src/contracts.ts`
- Create: `cloud/worker/src/billing.ts`
- Create: `cloud/worker/test/billing.test.ts`
- Modify: `.gitignore`

- [x] Write failing table tests for active, trialing, past-due, scheduled cancellation, uncancel, revoked/ended, unknown state, unknown product, and effective timestamp selection.
- [x] Implement strict event parsing and provider-neutral `NormalizedEntitlement`; allow only the configured monthly/yearly product IDs.
- [x] Pin current compatible versions of Wrangler, Vitest, Cloudflare's Vitest pool, TypeScript, Workers types, and `@polar-sh/sdk`.
- [x] Declare secret names only, sandbox-safe nonsecret defaults, D1 binding, local migrations, disabled observability, and `.dev.vars`/`.wrangler` ignores.
- [x] Run typecheck and focused tests; commit `feat: normalize Polar entitlement events`.

### Task 2: D1 idempotency and convergence repository

**Files:**
- Create: `cloud/worker/migrations/0001_billing_integrity.sql`
- Create: `cloud/worker/src/repository.ts`
- Create: `cloud/worker/test/repository.test.ts`
- Create: `cloud/worker/test/apply-migrations.ts`
- Modify: `cloud/worker/vitest.config.ts`
- Modify: `cloud/worker/tsconfig.json`
- Modify: `cloud/worker/package.json`
- Modify: `cloud/worker/package-lock.json`

- [x] Add failing tests for duplicate event IDs, newer-wins convergence, older-event refusal, equal-time deterministic tie-break, unknown account, and payload-body absence.
- [x] Create minimal `accounts`, `billing_customers`, `billing_events`, and `entitlements` tables with point-query indexes and strict checks.
- [x] Implement transactional event metadata insert plus conditional customer/entitlement upserts using prepared statements only.
- [x] Apply the migration only to Wrangler's local D1 and run integration tests; commit `feat: persist convergent billing entitlements`.

### Task 3: Verified Polar webhook route

**Files:**
- Create: `cloud/worker/src/polar.ts`
- Modify: `cloud/worker/src/index.ts`
- Create: `cloud/worker/test/worker.test.ts`
- Create: `cloud/worker/.dev.vars.example`
- Create: `cloud/worker/README.md`
- Modify: `cloud/worker/package.json`
- Modify: `cloud/worker/package-lock.json`

- [x] Add failing signed-request tests for valid lifecycle processing, invalid signature/no writes, malformed/oversize body, unsupported route/method, duplicate delivery, and unknown product/account.
- [x] Verify raw bytes and headers with `validateEvent` from `@polar-sh/sdk/webhooks`; normalize errors to safe responses with no payload logging.
- [x] Expose only `GET /healthz` and `POST /v1/billing/webhooks/polar`; return 202 for verified handled/ignored events and 403 for signature refusal.
- [x] Document exact repo-code completion versus future dashboard actions. Example vars contain names/placeholders only.
- [x] Run typecheck, Worker tests, local migration, full Python suite, and secret-pattern scan; commit `feat: verify Polar webhooks on Cloudflare Worker`.

## Completion gate

- Billing core passes duplicate, replay, ordering, signature, product, customer, and privacy tests locally.
- D1 contains no webhook body, email, raw logs, access token, webhook secret, checkout URL, or customer portal token.
- No redirect or client-provided state can unlock Autopilot.
- No provider dashboard or paid resource has changed.
- The next provider action is explicit: create sandbox products and a Cloudflare free project only after authentication/checkout endpoints are implemented and reviewed.
