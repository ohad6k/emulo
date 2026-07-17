# Emulo Account, Google Sign-In, Pricing, And Legal Architecture Plan

## Objective

Turn the current Emulo account and pricing shell into a credible, consumer-ready path that can convert both developers and non-developers without weakening the open-source product or the existing server-side billing boundary. The change must replace the current beta/technical presentation with a professional account experience, add Google as a first-class authentication provider alongside GitHub, publish the legal pages required before accepting payment, use the real Emulo identity asset, and keep all live-money behavior disabled until provider setup and lifecycle verification are complete.

The work is deliberately split into repo-controlled changes and provider-controlled changes. The repository can implement and fully test the Google OAuth flow, migration, UI, pricing, policies, and fail-closed configuration. It cannot prove a Google Cloud OAuth client, consent-screen publishing state, Cloudflare secret, Polar production lifecycle, or public deployment merely by changing code. Those actions require a provider receipt or a connected provider tool.

## Product Path

1. A visitor discovers Emulo on the public site.
2. The visitor understands the permanent free/open-source product and the optional managed Emulo Pro layer.
3. The visitor chooses free, monthly, or annual without seeing internal implementation language.
4. A Pro visitor reaches a centered Emulo account page and chooses either Google or GitHub.
5. Emulo completes a server-side OAuth Authorization Code flow, validates the provider identity, stores only the provider's stable subject identifier, and creates a hashed browser session.
6. The authenticated account page shows the user's actual entitlement state from D1.
7. Checkout remains unavailable until Polar production secrets, signed webhook processing, and a real lifecycle are separately proven.
8. Privacy, Terms, and Refund Policy pages are available before sign-in and before payment intent.
9. A paying user's access continues to be determined only by normalized Polar webhook state, regardless of whether the user authenticated with Google or GitHub.

## User Answers Translated

- Audience: Emulo Pro must not target only programmers. Google sign-in is required so creators, operators, founders, and other AI power users can create an account without GitHub.
- Identity providers: Google and GitHub should be equal choices on the account page. GitHub remains valuable for the open-source audience; Google is the broader commercial path.
- Product boundary: open-source Emulo stays capable and free. Emulo Pro must offer managed continuity that is meaningfully more convenient, not a crippled-open-source upsell.
- Financial constraint: the implementation must not create a recurring infrastructure cost before revenue. Existing Cloudflare Worker/D1, Vercel static hosting, Google OAuth, and Polar are used; no paid identity platform is introduced.
- Safety: no secrets are committed or pasted into chat. Provider setup is handled through dashboard fields or connected tools, with receipts that contain only nonsecret identifiers and status.
- Account merge policy: Google and GitHub identities will not be silently merged by email. The current GitHub flow does not request email, and email-based automatic merging can attach the wrong identity to an existing paid account. Each provider subject initially creates or returns its own Emulo account. Explicit account linking is a later authenticated feature.
- Brand and copy: remove “Private beta,” “Private account,” “Signed out,” “Production,” “View open source,” hashed-session explanations, and payment implementation language from customer-facing surfaces.
- Legal operator: Emulo is operated by Ohad Krispin in Israel and uses `ohadkrispin@gmail.com` as the public support/privacy contact. No registered-company claim will be made.
- Refund baseline: the proposed policy is a 14-day refund window for the first subscription payment and a 7-day window for renewal payments, while preserving mandatory consumer rights. This remains a written commercial policy, not a claim that a refund has been operationally tested.

## Current Repo Evidence

- Work is isolated on `codex/emulo-autopilot-design` in `D:/ditto/.worktrees/emulo-autopilot-design`; the main checkout and `feat/antigravity-source` are out of scope.
- `cloud/worker/src/index.ts` currently exposes GitHub start/callback routes, account assets, account state, Polar checkout/portal, and the signed webhook route.
- `cloud/worker/src/github-auth.ts` already implements a server-side OAuth flow with a 10-minute single-use state record, browser binding cookie, PKCE S256 challenge, exact callback URL derived from an allowlisted HTTPS base URL, safe diagnostics, hashed session token, `HttpOnly`/`Secure`/`SameSite=Lax` cookies, and non-storage of the upstream access token.
- `cloud/worker/src/auth-store.ts` uses `oauth_identities(provider, provider_user_id, account_id)` as the identity-to-account mapping. This is structurally provider-neutral, but migration `0002_auth_sessions.sql` currently constrains `provider` to `github` and provider user IDs to 32 characters.
- `accounts`, `browser_sessions`, `billing_customers`, and `entitlements` are already independent of GitHub. Polar receives the internal `account_id` as its external customer ID, so Google identities do not require billing schema changes.
- Production config binds one GitHub client ID and requires only `GITHUB_CLIENT_SECRET`. It keeps `PAID_CHECKOUT_ENABLED=false`, uses Polar production endpoints, and binds the isolated production D1 database.
- The production-context record says the production Worker is live with checkout disabled, the GitHub route is proven, both Polar product IDs are configured, and Polar access/webhook secrets plus real-money lifecycle proof remain open.
- The public site contains the requested prices but still uses “Install from GitHub,” “Open account,” “Private beta,” and a technical “payment truth” paragraph.
- The Worker account UI uses a split navy/teal layout and the old SVG robot. The real Emulo dual-profile icon is available as the optimized `assets/emulo-oauth.png` file under 1 MB.
- Existing tests cover GitHub OAuth failure modes, exact route methods, safe account rendering, production configuration guards, Polar checkout ownership, webhook integrity, and D1 entitlement state. The new provider must extend, not bypass, these guarantees.

## Architecture Boundaries

### Public site

The Vercel-hosted static site explains the product, prices, annual saving, and policies. It does not contain provider secrets, Polar product IDs, direct checkout links, or entitlement claims. Pro actions route to the Worker account page. Legal pages are static and publicly accessible.

### Account Worker

The Cloudflare Worker owns OAuth state, identity mapping, browser sessions, account rendering, and billing actions. The browser never receives a Google client secret, Polar access token, webhook signing secret, or durable upstream access token.

### D1

D1 remains the source of truth for Emulo account IDs, provider identities, hashed sessions, normalized billing customers, and webhook-confirmed entitlements. Adding Google changes the accepted identity-provider values but not billing ownership or entitlement logic.

### Google

Google authenticates the person and returns an authorization code. The Worker exchanges the code server-side and validates the returned ID token. Emulo relies on Google's stable `sub` claim, not email, as the provider user ID. Requested scopes are limited to `openid email profile`; no Drive, Gmail, Calendar, YouTube, or other sensitive product data is requested. Tokens are not persisted.

### GitHub

GitHub remains unchanged as an alternative provider. Its numeric user ID remains the identity key. The current no-email/no-repository-scope behavior remains intact.

### Polar

Polar remains Merchant of Record and billing provider. The internal Emulo account ID continues to be the external customer ID. Authentication choice has no effect on entitlement rules. Hosted checkout and signed webhooks remain the payment boundary.

### Deployment and secrets

Nonsecret client IDs may be committed as environment configuration after provider creation. `GOOGLE_CLIENT_SECRET`, `GITHUB_CLIENT_SECRET`, `POLAR_ACCESS_TOKEN`, and `POLAR_WEBHOOK_SECRET` must exist only as Cloudflare Worker secrets. Checkout remains committed as disabled.

## Options Considered

### Authentication platform versus direct providers

- Paid authentication service: fastest social-login expansion, but creates another vendor, recurring pricing risk, user migration work, and a new session boundary.
- Direct Google OAuth in the existing Worker: reuses the hardened flow and D1 model, has no per-user auth bill, and keeps provider tokens server-side. This is selected.
- Google Identity Services client-side credential flow: polished and supported, but adds browser-side SDK/CSP complexity and a separate POST/CSRF handling model. The existing Worker already uses server-side authorization code flow, so a consistent server-owned flow is selected.

### Account identity strategy

- Merge by verified email: convenient, but GitHub currently supplies no email and email is not an immutable identity key. Rejected for launch.
- One internal account per provider subject: safe, simple, and consistent with current schema. Selected for launch.
- Explicit linking: best long-term UX, but requires reauthentication of both providers, confirmation UI, collision handling, and entitlement transfer rules. Deferred to a separate design.

### Google ID token validation

- Call Google's `tokeninfo` endpoint for every sign-in: simple but Google documents it as a debugging mechanism and it creates another network dependency. Rejected for production.
- Verify the JWT signature using Google's published JWKS and check `iss`, `aud`, `exp`, and `nonce`: correct production approach. Selected. A small standards-focused JWT/JWK library compatible with Workers is preferred over handwritten cryptography; package impact and runtime compatibility must be proven before adoption.
- Use only the UserInfo endpoint: insufficient because access-token possession alone does not validate the ID token claims intended for this client. Rejected.

### Visual structure

- Recolor the current split screen: rejected because the problem is structural and the current presentation feels like an internal beta dashboard.
- Centered, warm-neutral account shell: selected. It supports two provider buttons, legal links, authenticated states, and mobile layouts without decorative clutter.

## Recommended Architecture

Implement a provider-neutral OAuth layer around the existing GitHub design. Introduce a shared flow utility for state, browser binding, PKCE, callback URL construction, session issuance, and safe diagnostics. Keep provider-specific authorization, token exchange, and identity validation in separate GitHub and Google modules. Refactor `auth-store.ts` to resolve or create an identity for an allowlisted provider and validate provider-specific subject formats. Apply a forward-only D1 migration that rebuilds the provider-constrained tables to accept `github` and `google`, copying existing rows without changing account IDs, sessions, billing customers, or entitlements.

Google begins at `GET /v1/auth/google/start` and returns to the exact production callback `https://emulo-production.ohad1306.workers.dev/v1/auth/google/callback`. The authorization request uses `response_type=code`, `scope=openid email profile`, `state`, PKCE S256, and `nonce`. The flow record must bind the provider and nonce to prevent a Google callback from consuming a GitHub flow or vice versa. The callback performs a single-use flow consume, exchanges the code server-side, verifies the ID token signature and claims against Google's discovery/JWKS data, requires `email_verified=true`, uses `sub` as the Google provider ID, discards tokens, creates the same hashed Emulo session, and redirects to `/account?signin=complete`.

The account page becomes a centered authentication surface with the real Emulo icon, “Sign in to Emulo,” a high-contrast “Continue with Google” button, a high-contrast “Continue with GitHub” button with the official GitHub mark, one concise explanation, and legal links. It contains no internal status badges or security implementation prose. Authenticated and billing states reuse the same shell.

The pricing section presents “Emulo” as free/open source and “Emulo Pro” as the managed continuity product. Actions read “Get Emulo,” “Choose monthly,” and “Choose annual.” Annual pricing shows `$108` struck through, `$79/year`, and “Save 27%,” calculated from 12 monthly payments. No live checkout claim is made while checkout is disabled.

Static Privacy Policy, Terms of Service, and Refund Policy pages use the same warm editorial design. They identify the operator accurately, explain actual data flows, distinguish open source from Pro, disclose Polar as Merchant of Record, and preserve statutory rights without pretending that production billing is already active.

## Workstream Map

1. Provider-neutral auth and migration.
2. Google OAuth and ID-token verification.
3. Professional account UI and real branding.
4. Pricing copy and annual value presentation.
5. Legal pages and policy links.
6. Provider setup, release safety, verification, and rollback.

## Workstreams

### 1. Provider-neutral auth and migration

Purpose: extend the proven auth boundary without duplicating security logic or rewriting billing data.

User outcome: either provider produces the same Emulo account/session experience.

Areas: `cloud/worker/src/auth-store.ts`, `github-auth.ts`, a new shared auth module, D1 migrations, contracts, and auth tests.

Tasks:

- [ ] Add failing tests proving an OAuth flow is bound to one provider and cannot be consumed by another.
- [ ] Add failing tests for Google subject length, GitHub numeric IDs, collision-safe identity creation, and existing-account lookup.
- [ ] Add a forward-only migration that accepts `github` and `google` while preserving all current identity/account rows.
- [ ] Generalize identity resolution behind an allowlisted provider type.
- [ ] Share state, browser binding, PKCE, session, and cookie behavior without weakening current GitHub tests.
- [ ] Add rollback documentation; do not attempt a destructive down migration after Google identities exist.

Acceptance: existing GitHub account IDs remain unchanged; Google identities can be stored; provider crossover is rejected; billing tables are untouched.

### 2. Google OAuth and token validation

Purpose: add broad consumer authentication with minimal data access.

User outcome: a Google user can securely create or return to an Emulo account.

Areas: new `google-auth.ts`, routing, contracts, package dependencies, Wrangler configs, config validation, and focused tests.

Tasks:

- [ ] Write start-route tests for exact callback, state, PKCE S256, nonce, and minimal scopes.
- [ ] Write callback tests for canceled consent, invalid state, wrong browser binding, replay, provider mismatch, bad token response, invalid signature, wrong issuer, wrong audience, expired token, wrong nonce, missing subject, and unverified email.
- [ ] Select and pin a Worker-compatible JWT/JWK verification library only after a minimal runtime test.
- [ ] Implement server-side token exchange and ID-token verification.
- [ ] Store only the Google `sub` identity and safe diagnostic metadata; never store access, refresh, or ID tokens.
- [ ] Add `GOOGLE_CLIENT_ID` as nonsecret configuration and `GOOGLE_CLIENT_SECRET` as a required deploy secret once the provider is ready.
- [ ] Ensure auth remains available through GitHub if Google is temporarily unavailable.

Acceptance: Google happy path creates a hashed browser session; all invalid-claim paths fail closed; no token appears in D1, logs, rendered HTML, or committed configuration.

### 3. Account UI and branding

Purpose: turn the internal-looking beta surface into a trustworthy consumer account entry point.

User outcome: the page immediately explains the action and offers two familiar sign-in methods.

Areas: `cloud/worker/src/account-ui.ts`, real icon asset route, account tests, and browser verification.

Tasks:

- [ ] Replace the split-screen structure with a centered warm-neutral shell.
- [ ] Serve the optimized real Emulo icon with an exact image content type and use it for favicon and top-left brand.
- [ ] Add professional Google and GitHub buttons with accessible names, focus states, and official provider marks.
- [ ] Remove all rejected labels, open-source secondary button, implementation prose, and blue/teal dashboard treatment.
- [ ] Keep authenticated entitlement states clear and human-readable.
- [ ] Add policy links that remain visible before authentication.
- [ ] Verify desktop and 390px mobile layouts, keyboard focus, contrast, and no horizontal overflow.

Acceptance: visual structure is materially different, both provider buttons are obvious, the real icon renders, and forbidden copy is absent.

### 4. Pricing

Purpose: make the commercial choice understandable without hype or internal billing language.

User outcome: visitors can compare free, monthly, and annual options and understand the annual saving.

Areas: `site/index.html` and site regression tests.

Tasks:

- [ ] Add failing copy tests for new action labels and removed beta/technical language.
- [ ] Rename the free entry and Pro framing in plain product language.
- [ ] Display `$108` crossed out, `$79/year`, and “Save 27%.”
- [ ] Route both Pro choices to account sign-in while checkout remains disabled.
- [ ] Preserve open-source capability statements that are already proven.

Acceptance: pricing is professional, arithmetic is correct, no direct Polar identifiers leak, and no visitor is told payment is live before proof.

### 5. Legal pages

Purpose: provide the baseline policies needed for Google branding review, Polar checkout, and customer trust.

User outcome: visitors can inspect privacy, commercial terms, and refund rules before creating an account or paying.

Areas: `site/privacy.html`, `site/terms.html`, `site/refunds.html`, shared styles or duplicated minimal legal styles, home footer, account footer, tests.

Tasks:

- [ ] Draft plain-language policies with operator name, Israel location, contact email, and last-updated date.
- [ ] Privacy: disclose Google/GitHub identity data, hashed sessions, D1 billing metadata, IP forwarding where applicable, providers, retention, rights, security, and no raw coding-log upload by the account service.
- [ ] Terms: separate MIT open source from Pro, define eligibility, subscriptions, renewals, cancellation, acceptable use, availability, IP, warranty/limitation, termination, and Israeli governing law.
- [ ] Refunds: state 14-day first-payment and 7-day renewal windows, cancellation behavior, request method, Polar processing, and mandatory-law preservation.
- [ ] Add footer links on all relevant surfaces.
- [ ] Mark the pages as product policies, not legal advice, and avoid invented company/registration claims.

Acceptance: all pages return 200 publicly, links are reachable before auth, copy matches actual architecture, and the support contact is consistent.

### 6. Provider setup, release, and proof

Purpose: prevent repo completion from being mistaken for provider or live completion.

User outcome: Google login launches only when the consent screen and callback are correctly configured.

Areas: Google Cloud Console, Cloudflare Worker secrets, D1 migration deployment, Vercel/Worker deployment, production context, release checklist.

Tasks:

- [ ] Create separate Google Cloud production OAuth project/client where practical.
- [ ] Configure External audience, Emulo branding, homepage, Privacy Policy, Terms, support email, and exact callback URI.
- [ ] Use only `openid`, `email`, and `profile`; do not enable unrelated Google APIs.
- [ ] Add Ohad as a test user for pre-production proof, then publish for public users.
- [ ] Complete brand verification if Google requires it for the Emulo name/logo.
- [ ] Enter `GOOGLE_CLIENT_SECRET` directly into Cloudflare; never paste it into chat or commit it.
- [ ] Apply migration before deploying code that writes Google identities.
- [ ] Deploy with checkout disabled, prove Google and GitHub sign-in, then separately continue Polar activation work.

Acceptance: provider dashboard receipt shows the exact callback and publishing state without exposing secrets; Cloudflare secret list shows the key name only; live sign-in works; checkout still fails closed.

## Execution Tasks

- [ ] Freeze the approved design and account-linking decision in a committed design spec.
- [ ] Write a Superpowers implementation plan with exact red/green checkpoints.
- [ ] Checkpoint the branch before auth/migration work.
- [ ] Implement migration and provider-neutral store tests first.
- [ ] Implement Google OAuth tests and code second.
- [ ] Redesign account UI and legal links third.
- [ ] Update pricing and create legal pages fourth.
- [ ] Run focused tests after each workstream and full tests before any deploy.
- [ ] Apply local D1 migration and prove existing GitHub data preservation with fixtures.
- [ ] Prepare exact Google provider steps and receipt requirements.
- [ ] Apply production migration before Worker deploy.
- [ ] Install the Google secret directly in Cloudflare.
- [ ] Deploy the Worker with checkout disabled.
- [ ] Deploy static site/legal pages.
- [ ] Verify both sign-in paths, policies, pricing, security headers, asset types, and fail-closed billing.
- [ ] Update production context with exact receipts and remaining Polar actions.

## Implementation Sequence

1. Approve and commit the design/specification.
2. Produce the detailed TDD implementation plan.
3. Add failing migration/store tests, then generalize provider storage.
4. Add failing Google OAuth tests, then implement authorization, exchange, and verification.
5. Add config guards and secret-name requirements without secret values.
6. Add failing account UI tests, then perform the structural redesign and brand asset route.
7. Add failing pricing/legal tests, then update the site and policies.
8. Run full local verification, dependency audit, config guard, and Wrangler dry run.
9. Complete Google dashboard setup and capture redacted receipt.
10. Apply production migration, install secret, deploy Worker with checkout disabled, and prove both providers.
11. Deploy the site and verify all public pages.
12. Keep Polar activation as a separately approved money-moving release gate.

## Data, Auth, Provider, And Deploy Boundaries

- Migration: forward-only widening of provider constraints; no account or entitlement rewrite.
- Identity: provider `sub`/ID, never email, is the durable key.
- Session: unchanged hashed token with one-day expiry and revocation support.
- OAuth state: one-time, ten-minute, browser-bound, provider-bound, and PKCE-protected.
- Tokens: ephemeral in Worker memory only.
- Diagnostics: provider, stage, safe status, and allowlisted error code only.
- Billing: entitlement derives only from verified Polar webhook state.
- Provider setup: Google Client ID can be nonsecret; Google Client Secret stays in Cloudflare.
- Deployment: migration before code; checkout disabled throughout this release.

## Test Matrix

| Area | Happy path | Unauthorized / invalid | Provider failure | Regression |
| --- | --- | --- | --- | --- |
| Google start | Correct redirect/scopes/state/PKCE/nonce | Bad config returns 503 | N/A | GitHub start unchanged |
| Google callback | Valid signed token creates session | State, binding, issuer, audience, expiry, nonce, subject, email verification rejected | Token/JWKS failures return safe 502 | No tokens/log details leak |
| Identity store | New/returning Google subject resolves | Invalid provider/subject rejected | D1 error safely handled | Existing GitHub account IDs preserved |
| Sessions | Authenticated status returns entitlement | Missing/expired/revoked cookie returns 401 | D1 failure returns 503 | Cookie attributes unchanged |
| Account UI | Both buttons and real brand render | Protected actions remain unavailable signed out | One provider outage does not hide the other | Forbidden beta/technical copy absent |
| Pricing/legal | Correct prices, 27% saving, all policy links | N/A | N/A | No product UUIDs/secrets/direct checkout URLs |
| Billing | Existing authenticated account owns checkout intent | Cross-account and unsigned webhook rejected | Missing secrets fail closed | Google identity does not alter entitlement rules |
| Deployment | Config, migrations, secrets, routes proven | Preview/sandbox drift rejected | Roll back Worker while schema remains compatible | GitHub remains fallback |

Deleted/archived data behavior: there is no user-delete feature in current scope. Tests must prove that deleting an account cascades identities, sessions, and entitlements according to existing foreign keys, and that no orphan Google identity survives. A separate account-deletion product flow should be created before broad consumer launch if Google policy or user demand requires self-service deletion.

## Verification Plan

- Focused Vitest suites for auth store, GitHub auth, Google auth, account rendering, routing, and billing.
- Local D1 migration from the current schema with seeded GitHub identity, session, and entitlement; verify exact row preservation and successful Google insert.
- `npm run typecheck`.
- `npm test` including production config guards.
- `npm run verify:production-config`.
- Wrangler production dry run with checkout disabled.
- Dependency audit and bundle-size review after adding JWT/JWK support.
- Static site tests for copy, prices, saving calculation, policies, contact, links, and absence of secret/provider identifiers.
- Browser checks at desktop and 390px for account, pricing, Privacy, Terms, and Refund pages.
- Live HTTP checks for status codes, content types, CSP, cookies, method restrictions, and disabled checkout.
- Redacted provider proof: Google client type, exact authorized redirect URI, audience/publishing status, scopes, and brand-review status; Cloudflare secret-name list only.
- Live identity proof with a test Google account and existing GitHub account; no secret, authorization code, cookie, ID token, email, or provider subject is recorded in the receipt.

## Rollout And Rollback

Rollout is migration-first because the old schema rejects `google`. The migration is backward compatible with the current GitHub code. After migration, deploy the new Worker with Google config. If Google configuration is incomplete, the Google start route returns a safe unavailable response while GitHub continues working. Deploy the static site only after the Worker account page can render both choices.

Rollback the Worker to the previous GitHub-only version if Google validation or UI fails. Do not reverse the D1 migration after any Google identity exists; the widened schema remains compatible with old GitHub-only code. Remove or hide the Google button during rollback so users are not routed to an unavailable provider. Revoke/rotate the Google secret in Cloudflare and Google Cloud if exposure is suspected. Do not touch Polar products or entitlements during auth rollback.

## Risks And Fallbacks

- Google brand verification may delay a fully branded public consent screen. Fallback: test with allowlisted users while the repo/UI/legal work ships; do not advertise public Google login until publishing is proven.
- Current `workers.dev` and `vercel.app` hostnames may complicate domain ownership proof for Google branding. Fallback: keep GitHub live and plan a custom Emulo domain before verification if Google rejects shared-provider domains.
- A JWT/JWK dependency may not run cleanly in Workers or may add excessive bundle size. Fallback: choose another standards-compliant Worker-compatible library; do not use `tokeninfo` as the production verifier.
- Separate Google and GitHub accounts may confuse a person who uses both. Mitigation: concise UI copy and a later explicit linking flow. Do not auto-merge by email.
- Legal text can become inaccurate as features change. Mitigation: keep claims narrow, date policies, link production-context updates, and review policies before enabling money.
- Provider outage: retain both buttons and provider-specific errors; do not turn one failure into a global account failure.
- Checkout risk: keep `PAID_CHECKOUT_ENABLED=false` and require a separate explicit approval for a real-money lifecycle.

## Open Questions

- Google Cloud may require a custom owned domain for Emulo brand verification. This is provider-dependent and must be observed, not guessed.
- Self-service account deletion is not in the current scope but should be designed before broad consumer scale.
- Explicit Google/GitHub account linking and entitlement transfer are deferred; the launch behavior is deliberately provider-specific.
- Refund windows are commercially approved only when Ohad accepts the written policy; production refund operations still require Polar lifecycle proof.

## Decision Log

- Selected direct Google OAuth in the existing Worker to avoid a paid auth platform and preserve the current security model.
- Selected server-side Authorization Code flow with PKCE, state, nonce, browser binding, and local ID-token verification.
- Selected Google `sub` as the durable provider identity; rejected email as a primary/merge key.
- Selected separate provider accounts at launch; deferred explicit linking.
- Selected a forward-only constraint-widening migration; rejected billing/account rewrites.
- Selected a centered warm-neutral account layout; rejected a recolor of the split beta dashboard.
- Selected minimal Google identity scopes; rejected access to any Google product data.
- Selected public Privacy, Terms, and Refund pages before payment activation.
- Selected continued fail-closed checkout and a separate real-money approval gate.

## VibeRaven Route

After design approval, use `superpowers:writing-plans` to produce the exact TDD implementation plan. During implementation, use `superpowers:test-driven-development`. Before provider/deploy work, update `production-context`, then use provider-action receipts and `go-live`/verification guidance. Before declaring complete, use release review and verification-before-completion.

## Next Skill

Next skill: `production-context`
