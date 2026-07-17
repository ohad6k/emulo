# VibeRaven Production Context

## Current Release / Change Window

### 2026-07-17 - Emulo Pro continuity customer onboarding

- Change: Expose the verified encrypted-continuity foundation as a first-device, recovery, pairing, status, push, retry, pull, device-management, encrypted-export, and cloud-deletion customer workflow.
- Evidence: The Python companion now creates a private device/master-key file plus a portable encrypted recovery kit, displays the recovery secret once, prompts without echo for recovery and pairing, stores the device bearer token only in a private exact-schema file, and preserves explicit conflict output. The active Pro account page creates a 10-minute one-time pairing code, lists/revokes safe device metadata, downloads the signed-in account's encrypted manifest, and requires typing `delete-cloud-continuity` before cloud deletion becomes actionable. A CLI-level synthetic proof moved exact Hebrew, emoji, and CRLF bytes from a first device to a recovered second device without printing recovery or device tokens.
- Boundary: The local companion alone holds plaintext, device private keys, the master key, recovery secret, and device bearer credential. The Worker/browser receives bounded account/device metadata and ciphertext. Local open-source use remains independent of entitlement. Checkout remains disabled.
- Danger: Printing a recovery/device secret, overwriting existing key material, accepting a redirect or non-HTTPS origin, silently merging divergent generations, exposing wrapped keys/tokens in account HTML, treating browser export as cross-account, or coupling local rollback to billing would break the product boundary.
- Repo fix: Add strict onboarding/credential schemas, atomic private writes, public-key derivation, exact HTTPS pairing, lazy CLI commands, active-only account controls, browser-session-scoped export, and typed-confirmation deletion UI. No migration, provider SDK, product ID, or checkout flag changed.
- Verification: Fresh Python suite passed 396 tests with 3 platform skips. Worker passed 132 tests across 14 files plus 8 production-config guards. TypeScript, production-config validation, npm production audit, clean `.[pro]` install/pip check, and Cloudflare production dry run passed. Dry run bundled 1,752.99 KiB / 320.76 KiB gzip with `PAID_CHECKOUT_ENABLED=false` and `GOOGLE_CLIENT_ID=not-configured`. Local browser proof at 1,265 CSS px showed no horizontal overflow, one safe device row, a valid 43-character pairing result, a disabled-until-typed deletion control, and no console warnings/errors. The in-app viewport override did not apply, so a fresh 390 px visual receipt for the new controls remains open.
- Provider/MCP proof: Unknown for this change. No Google, Cloudflare, D1, Polar, deployment, webhook, billing, or live customer state was mutated.
- Open action: Capture the fresh 390 px account receipt, configure/prove production Google, apply migrations through `0008`, deploy with checkout disabled, run the complete live synthetic two-device/account/billing/deletion proof, and require separate Ohad approval before checkout activation.

### 2026-07-17 - Google identity implementation (provider activation pending)

- Change: Implement Google OpenID Connect beside GitHub using an Authorization Code flow, PKCE S256, state plus browser binding, a one-time nonce, signed ID-token verification, provider-separated internal accounts, and the existing opaque Emulo browser session.
- Evidence: A forward-only migration preserves GitHub rows while allowing only `github` and `google`; tests use real RS256-signed JWTs to reject invalid signature, issuer, audience, expiry, nonce, unverified email, and invalid subject. Google callback tests prove provider crossover and wrong-browser flows fail without consuming valid state, tokens never enter D1, and only the stable Google `sub` becomes identity data.
- Boundary: Google client creation, consent-screen publishing, authorized production callback, Cloudflare `GOOGLE_CLIENT_SECRET`, live migration, deploy, and real callback proof remain provider actions. Production config intentionally holds `GOOGLE_CLIENT_ID=not-configured`, requires no Google secret yet, and keeps GitHub independently available.
- Danger: Enabling the visible route with a partial client, storing or logging Google tokens, broadening scopes beyond `openid email profile`, merging by email, deploying before migration, or claiming live Google sign-in without provider receipts.
- Repo fix: Add provider-bound OAuth flow storage, hashed Google nonce storage, pinned Worker-compatible `jose` verification against Google JWKS, safe diagnostics, exact GET-only routes, and config/privacy guards. No access, refresh, or ID token column exists.
- Verification: Focused auth/store/token/integration tests and Worker type-check pass. Full-suite, production dry-run, dependency audit, and browser proof remain required before this change is release-ready.
- Provider/MCP proof: Unknown. No Google Cloud or Cloudflare provider mutation occurred in this implementation step.
- Open action: Create a Google Web client with callback `https://emulo-production.ohad1306.workers.dev/v1/auth/google/callback`, publish/verify the consent configuration as required, install the secret directly in Cloudflare, then commit only the nonsecret client ID and require a real callback receipt before deployment claims.

### 2026-07-17 - Consumer account and Google identity design

- Change: Plan a structural account redesign, public legal pages, professional pricing copy, Google sign-in alongside GitHub, and a hard paid-value/security gate without changing the Polar entitlement boundary.
- Evidence: The current Worker already stores provider identities separately from accounts and billing, but D1 constrains identities/diagnostics to GitHub. The approved architecture uses a forward-only provider-widening migration, server-side Google Authorization Code flow, minimal identity scopes, local ID-token verification, and separate provider accounts rather than unsafe email merging.
- Boundary: The repo can implement and test routes, migration, UI, policies, and fail-closed config. Google OAuth client/consent publishing, Cloudflare secret installation, live migration, and live provider proof remain dashboard/provider actions.
- Danger: Silent email account merging, persisted Google tokens, broad Google scopes, deploying code before migration, claiming Google is public before consent-screen proof, or enabling Polar checkout during an auth/UI release.
- Repo fix: Pending approved design review and TDD implementation plan. The free product keeps local mining, review, adapters, history, rollback, export, and offline use. Pro is not sellable until client-side encrypted continuity works across two paired devices with conflict protection, propagation, recovery, and server-plaintext exclusion. Checkout remains disabled.
- Verification: Architecture plan and design spec record exact flows, rejected alternatives, test matrix, rollout, and rollback. No product code or provider state changed in this planning step.
- Provider/MCP proof: Google Cloud project/client, redirect URI, consent-screen audience, publishing/brand-verification status, and Cloudflare Google secret are currently unknown from repo.
- Open action: Review the written design, the Free-versus-Pro contract, and the proposed 14-day initial/7-day renewal refund window; then implement with tests before provider setup or any paid activation.

### 2026-07-17 - Public Emulo Pro pricing boundary

- Change: Add an honest Free-versus-Emulo Pro pricing section to the Vercel site and route paid intent to the authenticated production Worker account boundary.
- Evidence: The page shows open-source Emulo at `$0`, Emulo Pro at `$9/month` and `$79/year`, and a visible `Private beta` state. Both Pro actions target `/account` on the production Worker; no direct Polar checkout URL or production product ID is embedded.
- Boundary: The static site explains and routes. GitHub OAuth authenticates in the Worker, Polar hosts payment, signed webhooks write normalized D1 entitlement state, and only that database state may display Pro as active.
- Danger: Publishing a direct Polar link, embedding provider identifiers/secrets, promising unfinished cloud capabilities, or showing checkout as live before production proof would bypass the verified billing boundary.
- Repo fix: Add a responsive asymmetric pricing ledger, explicit open-source guarantees, server-side payment-truth copy, and focused regression tests for prices, URLs, beta state, and secret/provider-ID absence. Separate deploy-stage GitHub auth from later Polar activation so the disabled production shell can ship without weakening runtime billing checks.
- Verification: Pricing tests pass 5/5 after failing against the previous site; desktop and 390px browser checks show two-column and single-column layouts with no horizontal overflow; full Python tests pass 353 with 2 expected skips; Worker tests pass 92/92 plus 6/6 production guards; typecheck, production config validation, dry-run bundle, diff check, and production dependency audit all pass. Missing-webhook-secret coverage returns `503` and writes no billing event.
- Provider/MCP proof: Vercel production deployment `dpl_A7Vc19mb63ggGKyt7PqXseskcpHb` reached `READY` and owns `https://emulo.vercel.app`; a public HTTP read returned `200` with the Free, `$9`, `$79`, private-beta, and Worker-account markers, and no Polar product UUID. Two obsolete queued previews were removed after the production lane cleared; the remaining superseded preview was already canceled. Production Worker version `2a49f764-d11f-4fed-93a3-984f42cc862d` is live at `https://emulo-production.ohad1306.workers.dev` with checkout disabled and preview hostnames explicitly disabled. Live health/account/assets returned `200`, signed-out status returned `401`, GitHub auth redirected to `github.com`, and checkout/portal/webhook returned safe `503` states. Count-only D1 queries before and after returned zero accounts, customers, events, entitlements, sessions, and writes.
- Open action: Create the scoped Polar production access token and raw-webhook signing secret through the authenticated dashboard, enter them directly into Cloudflare without exposing their values, prove authenticated OAuth plus signed webhook state, and request explicit approval before any real-money lifecycle or checkout enablement.

### 2026-07-17 - Emulo Pro production products

- Change: Create and bind the two private recurring Emulo Pro products in Polar production.
- Evidence: Polar production MCP listed organization `Emulo` (`e060a9bd-275b-4235-878e-bfa49deac711`) with zero products before creation, then read back `Emulo Pro Monthly` (`ce99808b-4e11-4cec-bc31-d9654d558e08`) at `$9 USD` every month and `Emulo Pro Annual` (`b6535378-b1bd-40ee-bd37-96a03abec2f2`) at `$79 USD` every year; both are private with interval count `1` and no trial.
- Boundary: The repository stores only nonsecret product UUIDs. Polar remains the product source of truth, and committed production checkout remains disabled.
- Danger: Duplicate products, public checkout links, partial product configuration, or enabling checkout before secrets/webhooks/deployment are proven could create billing confusion or live-money risk.
- Repo fix: Bind both verified UUIDs together, rename active paid-plan UI copy to Emulo Pro, and keep `PAID_CHECKOUT_ENABLED=false`.
- Verification: Focused Emulo account tests pass 16/16; full Worker tests pass 91/91 plus 6/6 production-config guards; typecheck exits `0`; production config reports `nonsecret-config-ready`; the production Wrangler dry-run bundles with `PAID_CHECKOUT_ENABLED=false`; the production dependency audit reports 0 vulnerabilities.
- Provider/MCP proof: Both products were absent, created once, and independently listed after creation with exact names, cents, currency, cadence, privacy, and null trial state. No checkout link, customer, subscription, webhook, discount, benefit, or charge was created.
- Open action: Install the scoped production Polar access token and webhook secret, deploy the application with checkout disabled, prove auth/webhook behavior, and require separate approval before any real-money lifecycle test.

### 2026-07-17 - Production Polar routing correction

- Change: Route the server-side Polar SDK through the validated `POLAR_SERVER` value for both Sandbox and production.
- Evidence: A production-checkout regression test failed with `503` before the fix because readiness accepted only Sandbox; after the fix it returned `200` only for a `https://polar.sh` checkout URL.
- Boundary: Sandbox credentials and URLs must remain in Sandbox; production credentials and URLs must remain in production. Checkout remains disabled in committed production configuration.
- Danger: The previous Sandbox-only client would make production configuration unusable and could send a production flow to the wrong provider environment.
- Repo fix: Use one allowlisted server selector for readiness and SDK construction; preserve strict hosted-URL origin validation.
- Verification: Focused Polar billing tests pass 10/10; full Worker suite passes 91/91 plus 6/6 production-guard tests; typecheck, pinned high-severity scanner, production config validation, and Wrangler dry-run all exit 0.
- Provider/MCP proof: No Polar production mutation occurred while the unsafe routing was present.
- Open action: After the fix is green, create production products with a production-scoped token and keep public checkout disabled.

### 2026-07-17 - Production GitHub OAuth registration

- Change: Bind the owner-created Emulo Production OAuth application's public Client ID into the isolated production Worker configuration.
- Evidence: Owner supplied Client ID `Ov23liZFqQWwSfHUWsY1` after registering the app with the documented production homepage and callback; the provider dashboard was not independently inspected.
- Boundary: The Client ID is nonsecret repo configuration. `GITHUB_CLIENT_SECRET` remains a Cloudflare secret and must never enter source control or chat.
- Danger: Reusing Sandbox OAuth credentials, committing the Client Secret, or deploying before the production secret exists would leave authentication unavailable or cross environments.
- Repo fix: Replace only the production Client ID placeholder; keep checkout disabled and Polar production identifiers unconfigured.
- Verification: Run the production configuration guard, Worker typecheck/tests, and Wrangler production dry-run before committing.
- Provider/MCP proof: Cloudflare `secret list` returned exactly `GITHUB_CLIENT_SECRET` for `emulo-production`; deployments `b0af7ddb-89e4-48b1-9bdc-c07b0149931c` and `6eb69d76-5871-484b-ada8-5b5b60cb7439` record Worker creation and the secret change. The secret value was never read or recorded. Live `/`, `/account`, and `/v1/account/status` return Cloudflare `404`/`1042` because application code is intentionally not deployed yet.
- Open action: Create the two Polar production products and install the remaining production secrets before deploying application code and proving the GitHub callback.

### 2026-07-16 - Emulo founding-beta billing experience

- Change: Replace placeholder account/payment pages with an authenticated, state-aware Emulo experience while keeping checkout disabled by default.
- Evidence: Polar Sandbox delivered `subscription.created`, `subscription.active`, and `subscription.updated`; all three were recorded as `applied`, producing one active `founding-monthly` entitlement. Worker version `3ec1a0d8-184d-491e-8a90-66c3018cf577` exposes `PAID_CHECKOUT_ENABLED=false`; live checkout returned `503` and an unsigned webhook returned `403`.
- Boundary: D1 entitlement state after a verified signed webhook is the only customer-visible billing truth. A Polar checkout redirect never activates access.
- Danger: Static success copy, unauthenticated account claims, sandbox/production credential crossover, duplicate checkout, or enabling checkout during UI work could mislead users or create live-money risk.
- Repo fix: Add a provider-neutral authenticated account-status read, state-aware account/receipt UI, and safe checkout/portal interactions without changing local open-source behavior.
- Verification: Require focused red/green tests, full Worker tests/typecheck, config and secret review, safe deployment, live route checks, authenticated visual proof, and D1 state proof.
- Provider/MCP proof: Polar Sandbox lifecycle is proven. Polar production organization, products, token, webhook, payout/KYC state, and real purchase/refund remain unknown.
- Open action: Deploy the polished UI with checkout disabled; prepare exact owner-only Polar production activation steps without requesting secrets in chat.

### 2026-07-15 - Ditto Proof v1 harness

- Change: Build a disabled-by-default benchmark harness on `codex/ditto-benchmark-proof-release`.
- Evidence: The approved design and implementation plan freeze `v0.3.7`, 24 pairs, 48 isolated cells, private fixtures outside Git, and separate execution and publication approvals.
- Boundary: This work creates local repository code and synthetic verification only. Provider/model selection, scored executions, reviewer consent, cost approval, proof clips, and publication remain later human/provider actions.
- Danger: Mixed Ditto versions, reused homes, leaked profiles or receipts, invented provider state, and public claims before complete evidence would invalidate the proof.
- Repo fix: Add the standalone `proof` package, schemas, tests, pilot fixtures, privacy gates, publication generator, and runbook without importing it from `ditto.py`.
- Verification: Baseline `python -m unittest discover -s tests -v` passed 176 tests on Python 3.11.4 before implementation.
- Provider/MCP proof: Unknown until the later live preflight captures exact provider labels, versions, argv, quotas, expected cost, and screenshots.
- Open action: Stop after the verified synthetic harness and request exact cost/run/reviewer approval before any provider execution.

## Recent Changes

- Added the standalone proof harness, exact schemas, private fixture sealing, frozen 24-pair matrix, append-only evidence, clean-home runner, objective/blind review, privacy scan, deterministic publication, non-scored pilot, and operator runbook.
- Closed independent-review blockers by binding every public cell to its frozen manifest identity and stored attempt/evaluation/review hashes, binding exclusions to ship approval, requiring real CLI privacy inputs, rejecting ignored fixture secrets, and proving the pilot from a fresh clone.

## Architecture Boundaries

## Provider Boundaries

## Migration And Data History

## Incidents And Rollback Notes

## Fragile Customer Paths

## Verification Receipts

- Emulo billing experience commits `10509adc`, `79f504c1`, `92120af2`, and `05cb3947`: `npm run typecheck` exited 0; `npm test` passed 90 tests across 9 files; Wrangler dry-run bundled 1,500.32 KiB (153.39 KiB gzip) with `PAID_CHECKOUT_ENABLED=false` and `POLAR_SERVER=sandbox`.
- Worker version `600e1d92-4c3f-45c4-b5be-ea2466ed00d7`: live account, CSS, JavaScript, and SVG routes returned `200` with exact content types; unauthenticated status returned `401`; disabled checkout returned `503`; unsigned webhook returned `403`. Remote D1 still showed one active `founding-monthly` entitlement and three applied lifecycle events (`created`, `active`, `updated`).
- Production isolation receipt: D1 `emulo-autopilot-production` was created in EEUR, all five migrations applied, and count-only queries returned 0 accounts, 0 entitlements, and 0 billing events. `wrangler.production.jsonc` validates with checkout disabled and bundles against the production D1 binding; six Node config-guard tests reject Sandbox drift, secrets in vars, partial products, and committed enablement.

- Commit `e49a3317f87ac547496a28588774acbdb02069f1`: `python -m unittest discover -s tests -v` passed 249 tests in 24.568s on Python 3.11.4; one Windows symlink privilege test skipped while the junction/reparse rejection test passed.
- Synthetic pilot package: `e08c4e23921065839a234530261aae3f466c517fa0b93214669990f4dbdbe9ab`.
- Commit `7b584430dc6f0df33cd6ce3453e70f496d1ca3e0`: full suite passed 266 tests in 26.333s; fresh Windows clone passed 90 proof tests in 8.015s.

## Open Provider Or Human Actions

- Open the deployed `/account` and `/v1/billing/complete` in the already authenticated browser and provide a redacted visual receipt that the active plan and branded surfaces render. Do not share cookies, query codes, account IDs, or provider IDs.
- Polar production organization and both private products are proven through MCP. Payout status, scoped OAT, raw webhook, and real purchase/cancellation/refund lifecycle remain unproven, and checkout remains disabled.
- Production Worker is deployed with checkout disabled; its GitHub client ID and both nonsecret Polar product IDs are configured. The scoped Polar token and raw-webhook signing secret are still absent, so checkout, portal, and webhooks correctly fail closed.
