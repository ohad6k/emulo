# VibeRaven Production Context

## Current Release / Change Window

### 2026-07-17 - Public Emulo Pro pricing boundary

- Change: Add an honest Free-versus-Emulo Pro pricing section to the Vercel site and route paid intent to the authenticated production Worker account boundary.
- Evidence: The page shows open-source Emulo at `$0`, Emulo Pro at `$9/month` and `$79/year`, and a visible `Private beta` state. Both Pro actions target `/account` on the production Worker; no direct Polar checkout URL or production product ID is embedded.
- Boundary: The static site explains and routes. GitHub OAuth authenticates in the Worker, Polar hosts payment, signed webhooks write normalized D1 entitlement state, and only that database state may display Pro as active.
- Danger: Publishing a direct Polar link, embedding provider identifiers/secrets, promising unfinished cloud capabilities, or showing checkout as live before production proof would bypass the verified billing boundary.
- Repo fix: Add a responsive asymmetric pricing ledger, explicit open-source guarantees, server-side payment-truth copy, and focused regression tests for prices, URLs, beta state, and secret/provider-ID absence.
- Verification: Pricing tests pass 5/5 after failing against the previous site; desktop and 390px browser checks show two-column and single-column layouts with no horizontal overflow; full Python tests pass 353 with 2 expected skips; Worker tests pass 91/91 plus 6/6 production guards; typecheck, production config validation, dry-run bundle, diff check, and production dependency audit all pass.
- Provider/MCP proof: No production checkout, customer, subscription, charge, webhook, or entitlement was created by this change. Committed production checkout remains disabled.
- Open action: Deploy the Worker with checkout disabled, prove production OAuth and empty D1 state, install the scoped Polar token and raw webhook secret interactively, then request explicit approval before a real-money lifecycle.

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
- Production Worker deployment is intentionally waiting for the scoped Polar token and webhook secret; the GitHub client ID and both nonsecret Polar product IDs are now configured.
