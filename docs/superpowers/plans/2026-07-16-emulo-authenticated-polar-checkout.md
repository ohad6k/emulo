# Emulo Authenticated Polar Checkout Implementation Plan

**Goal:** Add the smallest secure account and billing-control vertical slice so a signed-in Emulo user can start a server-created Polar sandbox checkout and open their own customer portal, while public checkout remains hard-disabled.

**Architecture:** The Cloudflare Worker owns GitHub OAuth, hashed browser sessions, and trusted billing redirects. GitHub OAuth uses state plus S256 PKCE and requests no repository scope; the temporary GitHub token is used once to resolve the numeric user ID and is never persisted. Authenticated routes call Polar's official SDK in sandbox mode with an organization token held only as a Worker secret. The browser can select only `monthly` or `yearly`; product IDs, customer identity, IP forwarding, success URLs, and return URLs are server-owned. Redirects never grant entitlement.

**Current primary-source inputs (checked 2026-07-16):** GitHub's web OAuth flow strongly recommends unguessable state and S256 PKCE, codes expire after ten minutes, and identity must be revalidated through `GET /user` after every sign-in. Polar checkout accepts `external_customer_id` and `customer_ip_address`; customer sessions accept an external customer ID and return a hosted portal URL. Sandbox and production use isolated API hosts and tokens.

## Boundaries

- No GitHub or Polar token is stored, logged, returned, pasted into chat, or committed.
- OAuth state is single-use and expires after ten minutes. Session cookies are random, hashed at rest, `Secure`, `HttpOnly`, and `SameSite=Lax`.
- GitHub sign-in requests no repository or email scope and stores only the numeric provider identity.
- `PUBLIC_BASE_URL`, product IDs, and all redirect targets are server configuration, never request input.
- Checkout accepts only `monthly` or `yearly`; it forwards Cloudflare's connecting IP and binds Polar's external customer ID to the authenticated Emulo account.
- `PAID_CHECKOUT_ENABLED` defaults to `false`; no production checkout or live token is configured in this slice.
- The customer portal is available only to the authenticated account's external customer ID.
- No provider dashboard changes occur until code, tests, bundle, and review are green.

### Task 1: OAuth flow and hashed-session persistence

**Files:**
- Create: `cloud/worker/migrations/0002_auth_sessions.sql`
- Create: `cloud/worker/src/auth-store.ts`
- Create: `cloud/worker/test/auth-store.test.ts`
- Modify: `cloud/worker/test/apply-migrations.ts`

- [x] Add failing tests for single-use state consumption, expiry, identity reuse, hashed session lookup, expiry, revocation, and absence of raw session tokens.
- [x] Add `oauth_flows`, `oauth_identities`, and `browser_sessions` with strict constraints and point-query indexes.
- [x] Implement prepared-statement persistence and atomic state consumption.
- [x] Apply only to local D1; run focused tests and commit `feat: persist secure OAuth sessions`.

### Task 2: GitHub OAuth start and callback

**Files:**
- Create: `cloud/worker/src/github-auth.ts`
- Create: `cloud/worker/test/github-auth.test.ts`
- Modify: `cloud/worker/src/contracts.ts`
- Modify: `cloud/worker/src/index.ts`
- Modify: `cloud/worker/wrangler.jsonc`
- Modify: `cloud/worker/.dev.vars.example`

- [ ] Add failing tests for state/PKCE generation, exact callback URL, no requested scope, invalid/replayed/expired state, provider refusal, identity validation, safe cookie flags, and upstream failure.
- [ ] Implement `GET /v1/auth/github/start` and callback with GitHub's official endpoints; discard the access token immediately after `GET /user`.
- [ ] Return bounded safe HTML/JSON only; no auth value enters a URL except GitHub's temporary code and state.
- [ ] Run focused tests, typecheck, and commit `feat: authenticate Autopilot accounts with GitHub`.

### Task 3: Gated Polar checkout and portal adapter

**Files:**
- Create: `cloud/worker/src/polar-client.ts`
- Create: `cloud/worker/src/session.ts`
- Create: `cloud/worker/test/polar-client.test.ts`
- Modify: `cloud/worker/src/contracts.ts`
- Modify: `cloud/worker/src/index.ts`
- Modify: `cloud/worker/wrangler.jsonc`
- Modify: `cloud/worker/.dev.vars.example`

- [ ] Add failing tests for missing/expired session, disabled checkout, invalid plan, server-owned products/redirects, external account binding, connecting-IP forwarding, sandbox selection, provider refusal, and portal ownership.
- [ ] Implement `POST /v1/billing/checkout` and `POST /v1/billing/portal` through Polar's official SDK using sandbox by default.
- [ ] Return only short-lived hosted URLs with `Cache-Control: no-store`; never return Polar tokens or SDK error bodies.
- [ ] Keep entitlement changes webhook-only; run focused tests and commit `feat: create authenticated Polar billing sessions`.

### Task 4: Route/security integration and provider handoff

**Files:**
- Create: `cloud/worker/test/authenticated-worker.test.ts`
- Modify: `cloud/worker/src/index.ts`
- Modify: `cloud/worker/README.md`
- Modify: `docs/superpowers/plans/2026-07-16-emulo-authenticated-polar-checkout.md`

- [ ] Add end-to-end Worker tests for methods, origins, cookies, no-store headers, route isolation, disabled checkout, and webhook independence.
- [ ] Document exact Cloudflare Free, GitHub OAuth App, and Polar Sandbox dashboard paths and nonsecret verification evidence.
- [ ] Run local migrations, typecheck, all Worker/Python tests, audit, bundle dry-run, secret scan, and independent review.
- [ ] Commit `feat: gate Emulo founding checkout behind authenticated sandbox`.

## Completion gate

- GitHub start/callback proves state, PKCE, one-time code handling, and identity revalidation without storing provider tokens.
- Browser sessions are opaque in the cookie and hashed in D1.
- An unauthenticated caller, expired session, arbitrary product ID, arbitrary redirect, or checkout redirect cannot grant access.
- Polar sandbox checkout and portal calls are server-created and tied to the authenticated account.
- Checkout remains disabled by default and no provider resource has changed.
- The next external action is explicit and reversible: deploy a development Worker/D1, create a GitHub OAuth App for its exact callback, and create Polar sandbox products/token/webhook only after Ohad completes any login or 2FA prompt.
