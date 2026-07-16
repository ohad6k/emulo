# Emulo Billing Experience Architecture Plan

## Objective

Turn the already verified Emulo GitHub OAuth and Polar Sandbox billing slice into a trustworthy, production-quality customer experience without weakening the open-source product or confusing a hosted checkout redirect with paid access. The result must let a signed-in solo AI-agent power user understand their Emulo account, see a truthful subscription state, start a guarded checkout when explicitly enabled, return from Polar to a branded verification screen, and enter Polar's hosted customer portal. It must remain free to operate on the existing Cloudflare Worker and D1 footprint.

This plan covers the customer-facing account and billing experience plus the production activation boundary. It does not implement encrypted sync, device pairing, Autopilot learning, or the local control center. Those remain separate founding-beta workstreams in the approved product design.

## Product Path

1. A visitor opens the Emulo account URL.
2. Without a valid Emulo browser session, the page explains that GitHub connects an Emulo account and offers one sign-in action. It does not claim the browser is connected.
3. GitHub OAuth completes through the existing state, PKCE, browser-binding, and hashed-session flow, then returns to the account page.
4. The authenticated account page reads the normalized entitlement from D1. It displays a safe plan/state view without exposing Polar customer, subscription, event, or product identifiers.
5. When checkout is disabled, purchase actions are absent or disabled and the page clearly labels the environment. When enabled for an approved launch window, a user with no active entitlement can choose only the server-owned monthly or annual founding plan.
6. Polar hosts card collection. The return URL leads to a branded Emulo verification page, not a success claim.
7. The verification page queries an authenticated, same-origin account-status endpoint. It shows `Verifying` while no applied entitlement exists and `Active` only after a signed Polar webhook has produced an active D1 entitlement.
8. An active customer can open Polar's hosted portal through the existing authenticated server route. Cancellation or lifecycle changes return through signed webhooks and update the normalized status shown by Emulo.

## User Answers Translated

- Audience: solo agent power users who want Emulo to maximize their personal AI workflows across agents.
- Business model: preserve a strong local open-source product while charging for managed continuity, orchestration, sync, recovery, and founding-beta support.
- Founding offer: $9 monthly or $79 annually in Polar, with annual emphasized without fake urgency.
- Cost constraint: no paid infrastructure before customer revenue. Continue on Cloudflare Workers Free, D1 Free, GitHub OAuth, and Polar's transaction-funded plan.
- Safety rule: a checkout redirect is never proof of access. Signed, verified, idempotently applied Polar lifecycle events are the billing source of truth.
- Operator constraint: do not expose a public or live checkout merely to test design. Sandbox checkout remains disabled outside a bounded manual test window.
- Design standard: the page must be structurally redesigned, grounded in the real Emulo logo and real product state, clear rather than busy, and visibly distinct from generic SaaS card grids.
- Completion standard: repository tests are not production proof. Local tests, deployed-route checks, D1 receipts, and provider-dashboard receipts are tracked separately.

## Current Repo Evidence

- `cloud/worker/src/index.ts` serves `/account`, `/account.js`, and `/v1/billing/complete` as minimal inline HTML and JavaScript. The current wording intentionally avoids claiming active access, but `/account` always says the browser is connected even when it has not authenticated the request.
- `cloud/worker/src/session.ts` already authenticates the `__Host-emulo_session` cookie by hashing it and resolving a live, non-revoked D1 session.
- `cloud/worker/src/polar-client.ts` already gates checkout, validates origin, resolves the authenticated account, selects server-owned monthly/yearly product IDs, binds Polar's external customer ID to the Emulo account, and creates an authenticated portal session.
- `cloud/worker/src/repository.ts` and `cloud/worker/src/billing.ts` already apply signed lifecycle events idempotently with newer-wins ordering into normalized entitlements.
- D1 has one sandbox billing customer, one active `founding-monthly` entitlement, and three applied events: `subscription.created`, `subscription.active`, and `subscription.updated`.
- The deployed Worker has `PAID_CHECKOUT_ENABLED=false`. A live POST returns `503 checkout-disabled`; an unsigned webhook returns `403 rejected`.
- `assets/emulo-oauth.png` is the real compact Emulo identity asset and is below 1 MB.
- The Worker currently has focused auth, billing, repository, and integration tests. There is no authenticated account-status endpoint or state-aware receipt-page test.
- `site/index.html` is the deployed Vercel marketing surface. It currently explains only the free local product, has no pricing or account entry point, and cannot initiate the authenticated Worker purchase path.

## Architecture Boundaries

### Browser presentation boundary

The browser renders only a bounded view model. It never receives provider secrets, raw webhook data, provider identifiers, OAuth identities, account IDs, event IDs, or diagnostic errors. JavaScript may request checkout, portal, and status routes only on the same origin and may redirect only to a URL already validated by the Worker.

### Authentication boundary

Every account-specific data response must authenticate the hashed browser session on the server. The public `/account` page may render a signed-out state, but it must not query or imply account data. `/v1/account/status`, checkout, and portal routes return `401` for missing, malformed, expired, or revoked sessions.

### Billing truth boundary

The account status is derived from the normalized D1 entitlement. `active`, `trialing`, `past_due`, `grace`, `ended`, and `refunded` remain distinct. The completion page must not infer state from query parameters, URL arrival, checkout creation, or client storage. No client request can write entitlement state.

### Provider boundary

Polar continues to host checkout and subscription management. Emulo does not collect card details or build cancellation primitives. Sandbox and production require separate products, tokens, webhook secrets, URLs, and verification receipts. Repository configuration cannot prove Polar production state.

### Open-source boundary

The cloud billing UI changes no local mining, profile, agent-adapter, CLI, plugin, video, benchmark, or antigravity code. Ending a cloud entitlement does not disable the open-source local engine.

### Deployment boundary

The Worker may be deployed with the safe gate disabled to preview account and receipt UI. Enabling checkout is a separate reversible configuration action after provider evidence and final approval. No code path should require enabling checkout to inspect the design.

## Options Considered

### Option A: Static branded pages only

Replace the raw HTML with polished CSS but keep static copy. This is fast and visually better, but the receipt still cannot distinguish a delayed webhook from an active subscription. It would preserve the exact weakness the user noticed: a page that looks disconnected from what actually happened.

Rejected because visual polish without truthful state is insufficient for a billing experience.

### Option B: Client-only status assembled from checkout state

Store the chosen plan or checkout result in browser storage and render success after the Polar redirect. This creates a smoother page but makes the browser a billing truth source. It fails if a checkout is abandoned, if the webhook fails, or if the user changes devices.

Rejected because redirects and browser state cannot grant or prove entitlement.

### Option C: Authenticated server status plus state-aware UI

Add one safe read-only account-status boundary backed by D1, render authenticated/signed-out account states on the server, and let the completion page poll briefly for the webhook-confirmed state. Keep checkout and portal as existing server-created Polar sessions.

Recommended because it is the smallest architecture that is both polished and truthful. It reuses existing auth and normalized entitlements, introduces no paid service, and gives the UI a stable provider-neutral contract.

## Recommended Architecture

Create an account-status module responsible for authenticating the request and mapping D1 rows into a provider-neutral `AccountStatus` view model. The view model contains only environment, checkout availability, entitlement state, plan code, current period end, grace end, and recovery end. Missing rows map to `none`; database failures return a bounded `503` response.

Create a UI module responsible for the Emulo document shell, structural layouts, state copy, CSS, and small same-origin JavaScript bundle. The account layout uses a strong split composition: identity and product promise on one side, one focused account/action surface on the other. It avoids a generic dashboard grid. The real Emulo image appears as a restrained identity mark, with a text fallback. The page has visible Sandbox labeling whenever `POLAR_SERVER=sandbox`.

The account page asks the status module for a snapshot. Signed-out users see GitHub sign-in. Signed-in users see exactly one primary state: start founding beta, active founding beta, payment recovery, ended/recovery, or unavailable. Secondary details remain concise. Active or lifecycle-managed customers get a portal action; checkout choices appear only when the server gate is enabled and no active entitlement is present.

The completion page renders immediately with a `Verifying` state and bootstraps the same status view model. Its script polls `/v1/account/status` with bounded attempts and stops on any terminal entitlement. `active` produces an activation confirmation; `past_due`, `grace`, `ended`, or `refunded` produces an honest account-management state; `none` after the bounded period explains that confirmation is still pending and links back to the account. The DOM uses an `aria-live` status region and remains fully understandable without animation.

The current account script expands to handle checkout, portal, and receipt polling. Every action disables its initiating button, displays a human-readable bounded status, validates only that the returned URL is HTTPS and belongs to the expected Polar Sandbox or production host already enforced server-side, and restores controls after safe failures. Reduced motion disables nonessential transitions.

## Workstream Map

1. Account-status domain and repository query.
2. Authenticated route behavior and safe JSON contract.
3. Branded server-rendered account and receipt UI.
4. Same-origin checkout, portal, and verification interactions.
5. Local integration, accessibility, and security verification.
6. Sandbox-safe deploy, live evidence, and production provider handoff.
7. Public-site Free versus Emulo Pro decision surface and safe account handoff.

## Workstreams

### 1. Account status

Purpose: provide one provider-neutral source for every customer-facing state.

Files: create `cloud/worker/src/account-status.ts`; create `cloud/worker/test/account-status.test.ts`.

Tasks:

- [ ] Define a narrow `AccountStatus` type using existing entitlement and product-code unions.
- [ ] Authenticate through `authenticateBrowserSession` and return a signed-out result without querying account data.
- [ ] Query the entitlement by authenticated account ID with a prepared statement.
- [ ] Map no row to `none` and preserve lifecycle timestamps without provider identifiers.
- [ ] Return checkout availability only from environment configuration.

Acceptance: tests prove signed-out, no-entitlement, active, past-due/grace, and database-failure behavior.

### 2. Routes and response contracts

Purpose: make state readable by server pages and a bounded browser client.

Files: modify `cloud/worker/src/index.ts`; modify `cloud/worker/test/authenticated-worker.test.ts`.

Tasks:

- [ ] Add `GET /v1/account/status` with `Cache-Control: no-store`.
- [ ] Return `401` for missing/expired sessions and safe JSON for authenticated sessions.
- [ ] Keep exact method handling for account, status, completion, checkout, portal, and webhook routes.
- [ ] Ensure no provider or account identifiers are serialized.

Acceptance: Worker integration tests cover methods, cache headers, auth, DTO fields, and absence of sensitive identifiers.

### 3. Branded UI

Purpose: replace raw browser-default HTML with a distinct, launch-quality Emulo experience.

Files: create `cloud/worker/src/account-ui.ts`; modify `cloud/worker/src/index.ts`; make the logo available through a bounded static route or build-time asset mechanism; create focused UI tests.

Tasks:

- [ ] Build one reusable document shell with CSP-compatible external CSS/JS or hash-safe inline presentation.
- [ ] Implement signed-out, no-entitlement, active, billing-attention, ended, and unavailable account states.
- [ ] Implement a verification receipt that can transition from pending to webhook-confirmed active.
- [ ] Add explicit Sandbox labeling and avoid production language in the sandbox deployment.
- [ ] Use the real Emulo identity asset, responsive structure, visible focus, semantic headings, and reduced-motion behavior.

Acceptance: rendered HTML tests verify structure and truthful copy; browser smoke proof confirms mobile/desktop readability and no default-browser presentation.

### 4. Billing interactions

Purpose: connect UI actions to existing secure server routes without broadening provider authority.

Files: modify or replace account script in `cloud/worker/src/account-ui.ts`; extend `cloud/worker/test/authenticated-worker.test.ts` and `cloud/worker/test/polar-client.test.ts` only where new behavior requires it.

Tasks:

- [ ] Keep plan selection limited to `monthly` and `yearly`.
- [ ] Add portal action with the existing authenticated POST route.
- [ ] Add bounded receipt polling with terminal-state handling.
- [ ] Preserve no-store responses, same-origin credentials, and safe error messages.
- [ ] Ensure checkout stays hidden/disabled when the environment gate is false.

Acceptance: focused script-content and route tests prove actions, and the existing server tests continue proving origin, auth, redirect ownership, and provider failure handling.

### 5. Verification and production memory

Purpose: prevent a polished page from becoming an unsupported readiness claim.

Files: update `cloud/worker/README.md`; update `.viberaven/production-context.md`; add a verification receipt document only if it contains reproducible evidence.

Tasks:

- [ ] Run focused red/green tests for each new behavior.
- [ ] Run full Worker typecheck and test suite.
- [ ] Run a deploy dry-run or bundle check and inspect the diff for secrets or environment drift.
- [ ] Deploy with checkout disabled and verify live account, status auth, receipt, checkout-disabled, and unsigned-webhook rejection behavior.
- [ ] Record D1 and Worker receipts without IDs that are unnecessary for future decisions.

Acceptance: every status claim has a test, command, deployed response, D1 query, or provider receipt.

### 6. Polar production activation handoff

Purpose: prepare real revenue without crossing owner-only provider and live-money boundaries invisibly.

Files: add a production activation runbook under `docs/release/`; update nonsecret configuration examples only after official Polar evidence is checked.

Tasks:

- [ ] Verify current official Polar production requirements and fees from primary sources.
- [ ] List exact production products, prices, webhook events, raw format, callback URL, and nonsecret product-ID configuration.
- [ ] Separate owner actions for login, production organization/KYC/tax state, token creation, and secret entry.
- [ ] Require one low-risk real purchase/refund lifecycle before public checkout enablement.
- [ ] Define the rollback: set `PAID_CHECKOUT_ENABLED=false`, deploy, preserve signed webhooks for existing customers, and investigate without deleting entitlement history.

Acceptance: the runbook contains no secrets and makes every unproven provider state explicit.

### 7. Public-site pricing and account handoff

Purpose: let a visitor understand what stays free, what Emulo Pro adds, and where an authenticated purchase begins without turning the static Vercel site into a billing authority.

User outcome: visitors can choose the open-source local product or Emulo Pro from one clear, honest comparison. The Pro action enters the Cloudflare account flow, where GitHub authentication, server-owned product selection, Polar checkout, signed webhooks, and D1 entitlement truth remain enforced.

Files: modify `site/index.html`; add `tests/test_site_pricing.py`; update `.viberaven/production-context.md` after verification.

Dependencies: the production Worker account URL must be stable; committed production checkout remains disabled until the provider and lifecycle gates pass.

Tasks:

- [x] Add a visible `Pricing` navigation target and one asymmetric Free-versus-Pro section consistent with the existing editorial Emulo site.
- [x] State that local mining and `you.md` remain free, local, and open source.
- [x] State only the approved current Pro value: managed cloud continuity, cross-agent orchestration/sync, recovery, and founding support. Do not claim unfinished capabilities are already active.
- [x] Show exact `$9 monthly` and `$79 yearly` production prices without fake urgency, fabricated savings, or a fake trial.
- [x] Send Pro intent to the production Worker `/account` route. Do not embed Polar product IDs, tokens, customer IDs, or a direct checkout link in the site.
- [x] Keep the GitHub action as the primary free path and add truthful disabled/beta language until public checkout is enabled.
- [x] Add a focused source-level regression test for pricing, URLs, open-source guarantees, and absence of secret-shaped values or direct Polar checkout URLs.
- [ ] Verify desktop and mobile rendering from a local static server, then verify the Vercel preview after push. Local desktop and 390px checks are complete; preview proof remains open.

Acceptance: the public site clearly separates free local Emulo from paid Emulo Pro, all billing authority remains server-side, tests prevent price/link/privacy drift, and no CTA claims a purchase is live while production checkout is disabled.

## Execution Tasks

- [ ] Write account-status tests and observe expected failures.
- [ ] Implement the minimum status query and make focused tests pass.
- [ ] Write route/UI integration tests and observe expected failures.
- [ ] Implement the account and receipt structure.
- [ ] Implement checkout, portal, and receipt interactions.
- [ ] Run focused tests after each change and keep the full suite green.
- [ ] Update operator documentation and production context.
- [ ] Deploy only with checkout disabled.
- [ ] Collect live route, D1, and provider evidence.
- [ ] Prepare but do not silently perform live-money provider actions.
- [x] Add and locally verify the public-site pricing/account handoff while checkout remains disabled. Vercel preview proof remains a release action.

## Implementation Sequence

1. Preserve the current clean worktree and safe deployed gate.
2. Add status-domain tests, verify red, implement the status module, verify green.
3. Add integration tests for truthful account and completion states, verify red.
4. Add the UI module and route wiring, verify green.
5. Add portal/polling behavior with tests and verify green.
6. Run typecheck, complete Worker suite, and secret/config diff review.
7. Update production context and the production activation runbook.
8. Deploy the safe configuration and collect live proof.
9. Publish the pricing surface with an honest beta/account handoff while checkout remains disabled.
10. Only after owner/provider evidence, execute a bounded production purchase/refund test and then decide whether to open public checkout.

## Data, Auth, Provider, And Deploy Boundaries

- Data: read existing entitlements only; no migration is required for the UI slice.
- Auth: use the existing hashed session and do not expose account IDs.
- Provider: checkout and portal stay server-created; webhooks remain the only entitlement writer.
- Secrets: remain interactive Cloudflare secrets and never enter source, docs, output, screenshots, or chat.
- Deploy: the safe default is checkout disabled. UI deploys do not imply a launch.
- Cost: no new paid provider or infrastructure service is introduced.

## Test Matrix

| Case | Expected evidence |
| --- | --- |
| Signed out account | Branded sign-in state; no account claim or D1 entitlement data |
| Authenticated, no entitlement | Founding-plan explanation; checkout follows gate |
| Authenticated active monthly/yearly | Correct plan/status, portal action, no duplicate checkout CTA |
| Redirect before webhook | Verifying state; no active claim |
| Redirect after webhook | Active state from D1 only |
| Past due or grace | Billing-attention copy; local OSS remains described as available |
| Ended or refunded | Cloud access ended/recovery copy; portal/account navigation |
| Expired/revoked session | `401` status API and signed-out page behavior |
| Database failure | Safe unavailable response; no diagnostics leakage |
| Checkout disabled | No enabled purchase control and live API `503` |
| Provider checkout/portal failure | Safe retry message; no provider error body |
| Cross-origin POST | Existing `403` behavior remains |
| Unsigned/invalid webhook | Existing `403` and zero entitlement write remain |
| Duplicate/out-of-order webhook | Existing idempotent/newer-wins behavior remains |
| Responsive/reduced motion | Primary action remains visible and content readable |

## Verification Plan

- Focused Vitest commands for the status and authenticated Worker tests during red/green cycles.
- `npm run typecheck` from `cloud/worker`.
- `npm test` from `cloud/worker`, with exact test count and zero failures recorded.
- `git diff --check` and `git diff` review for scope, accidental secrets, configuration drift, and unrelated branch work.
- Cloudflare deployment output recording the Worker version and `PAID_CHECKOUT_ENABLED=false` binding.
- Live unauthenticated status request returning `401`, checkout POST returning `503`, and unsigned webhook returning `403`.
- Authenticated browser visual proof for account and payment-verification states.
- D1 query proving the sandbox entitlement remains active and lifecycle events remain applied.

## Rollout And Rollback

Rollout uses three gates. Gate one deploys UI and status reads with checkout disabled. Gate two performs a private production checkout and refund only after production provider configuration is proven. Gate three enables public checkout after the real lifecycle, portal, and rollback are verified.

Rollback never deletes billing history. Disable checkout through the Worker binding, redeploy, keep webhook processing available for existing customers, and revert only the UI/code commit if the customer experience itself is defective. If a status query fails, show unavailable rather than inventing a state. If Polar is unavailable, local open-source Emulo remains unaffected.

## Risks And Fallbacks

- Webhook latency: bounded polling falls back to pending verification and account navigation.
- Session expiry during checkout: show reconnect rather than payment failure; the webhook still binds through the server-owned external customer ID.
- Sandbox/production mix-up: environment badge, host validation, separate tokens/products/secrets, and a disabled default reduce risk.
- Duplicate purchase: active accounts do not receive a primary checkout CTA; Polar portal is the primary action.
- Generic or misleading UI: structural split layout, real Emulo identity, one primary action, and state-specific copy avoid dashboard filler.
- Cloudflare asset complexity: if static asset bundling adds risk, use a small optimized copy of the approved logo through an explicit Worker asset route, retaining a text fallback.
- Provider outage: safe `502/503` messages, no entitlement mutation, and retry through hosted portal later.

## Open Questions

No product question blocks the sandbox-safe UI slice. Production activation still requires owner/provider evidence for Polar production organization status, payout/KYC readiness, exact live products, live token creation, and live webhook registration. Those values must not be pasted into chat.

## Decision Log

- Use authenticated D1 entitlement state, not redirect/browser state, as customer-visible truth.
- Add a provider-neutral status DTO rather than exposing D1 or Polar rows.
- Reuse hosted Polar checkout and portal; do not handle cards or cancellation directly.
- Keep open source independent of cloud entitlement.
- Deploy UI with checkout disabled first.
- Treat production provider setup as a separate evidence-gated action.
- Prefer one strong account surface and one focused verification surface over a generic multi-card dashboard.
- Keep the Vercel site presentational only; route paid intent to the authenticated Worker instead of duplicating checkout logic or provider identifiers in static HTML.

## VibeRaven Route

Record the billing/auth/deploy boundary and verification receipts in `.viberaven/production-context.md`. Separate repository changes from provider actions. Use `go-live` only after local tests, config review, and safe deployment are proven.

## Next Skill

`production-context`
