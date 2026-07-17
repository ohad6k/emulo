# Emulo Pro continuity release evidence

**Status:** repository implementation, production migration, disabled-checkout
deployment, GitHub sign-in, and the signed-out shell are verified; **not
production-launch ready**.

This record separates what is proven in the repository from provider and
operator work that has not happened. `PAID_CHECKOUT_ENABLED` must remain
`false` until every remaining gate below is evidenced and Ohad separately
approves activation.

## What is implemented and verified

- Local AES-256-GCM approved-generation encryption with authenticated metadata,
  fresh nonces, strict schemas, and bounded plaintext.
- X25519 + HKDF per-device master-key wrapping and Scrypt recovery wrapping.
- One-time pairing grants, five-device cap, hashed device credentials,
  account-scoped listing, and immediate revocation.
- Ciphertext-only generation storage with digest verification, a 500-generation
  and 64 MiB account cap, idempotent retries, and account isolation.
- Optimistic parent concurrency that preserves both branches and advances only
  one head instead of silently overwriting or merging.
- Local encrypted outbox retries, exact artifact import, conflict preservation,
  continued local learning, and append-only rollback after cloud access fails.
- Bounded post-subscription recovery reads, ciphertext export manifests, and
  confirmed account-scoped cloud-continuity deletion that does not purge local
  files.
- Provider-separated GitHub and Google OAuth code. Google is deliberately
  disabled by the committed `not-configured` client ID.
- Concrete Free versus Pro copy: open source keeps local mining, review,
  activation, history, rollback, export, and offline use; Pro adds managed
  encrypted continuity and device/recovery operations.
- Customer CLI commands for first-device initialization, second-device recovery,
  hidden-input pairing, local status, encrypted push/retry/pull, and explicit
  conflict reporting.
- Active-account controls for 10-minute pairing codes, safe device listing and
  revocation, browser-session-scoped encrypted export manifests, and exact typed
  confirmation before hosted continuity deletion.
- Secure local onboarding files that refuse overwrite and links, store the
  recovery secret nowhere, and keep device bearer credentials out of command
  output and account HTML.

## Verification evidence from 2026-07-17

- Python: 396 tests passed, 3 Windows/platform skips.
- Worker: 133 tests passed across 14 files.
- Production configuration: 8 guards passed.
- TypeScript: `tsc --noEmit` passed.
- Production npm audit: 0 vulnerabilities.
- Clean temporary Python environment with `.[pro]`: no broken requirements.
- Cloudflare production dry run passed at 1,752.99 KiB / 320.76 KiB gzip.
- Dry run confirmed `PAID_CHECKOUT_ENABLED=false` and
  `GOOGLE_CLIENT_ID=not-configured`.
- Browser QA for the new active-account controls: the local desktop render at
  1,265 CSS px had zero horizontal overflow, one safe device row, a working
  43-character pairing-code reveal, a delete button disabled until the exact
  confirmation was typed, and no console warning/error. The in-app viewport
  override did not apply, so the changed controls still need a fresh 390 px
  visual receipt before launch.
- Synthetic two-device proof preserved exact Hebrew, emoji, and CRLF artifact
  bytes and retained local rollback while transport was unavailable.
- Customer-level CLI proof initialized device A, connected it, pushed two
  approved generations, recovered a fresh device B from the portable encrypted
  kit, connected it, and activated the exact remote bytes without printing the
  recovery or device bearer tokens.
- GitHub `main` was pushed at `41cdb1e9`; production D1 applied migrations
  `0006` through `0008` and then reported no pending migrations.
- Cloudflare deployed Worker version
  `c81f8a99-4c1b-4cf7-b872-d76e3a3e561c` with checkout disabled and Google
  deliberately unconfigured. The only declared secret name was
  `GITHUB_CLIENT_SECRET`; no secret value was read.
- A configuration-aware UI correction hides Google and the provider divider on
  both signed-out account surfaces while Google is unconfigured. GitHub remains
  visible, and the direct Google start route still fails closed with `503`.
- The owner completed the production GitHub callback. The authenticated account
  page rendered successfully; a count-only D1 receipt returned one account, one
  GitHub identity, one browser session, and zero billing customers,
  entitlements, continuity devices, and continuity generations. The receipt
  wrote zero rows.
- Live HTTP proof returned expected `200` responses for health, account assets,
  and legal pages; `401` for signed-out account/device/export reads; `302` from
  GitHub start to `github.com`; safe `503` responses for checkout, portal,
  unsigned webhook, and unconfigured Google; and `404` for an unknown route.
- Live desktop and real 390x844 signed-out renders had no horizontal overflow,
  loaded the Emulo mark, and produced no console warnings or errors. This proves
  the responsive public shell, not the still-unseen active paid controls.
- Count-only D1 reads before owner sign-in preserved the empty customer state;
  the post-callback receipt above is the current production state.

## Data boundary proven by tests

The hosted service can receive account/provider identifiers, entitlement
metadata, device labels and public keys, ciphertext, ciphertext digests, byte
sizes, generation relationships, and timestamps.

It does not need raw session logs, prompt text, receipt evidence, local source
paths, plaintext profile/workflow content, device private keys, the account
master key, the recovery secret, model-provider tokens, or payment-card data.
Device bearer tokens and browser sessions are stored only as hashes.

## Remaining launch blockers

1. Capture a fresh authenticated 390 px visual/interaction receipt for the new
   active-account device and deletion controls. The live signed-out shell is
   proven at 390x844, but it cannot prove paid-state controls.
2. Install the production Polar access token and raw-webhook signing secret
   directly in Cloudflare without placing either value in source control, chat,
   command history, or captured evidence. Register the exact production webhook
   endpoint and prove a signed delivery before checkout activation.
3. Run a live synthetic account proof: every enabled sign-in provider,
   webhook-confirmed
   entitlement, first and second device, encrypted push/pull, conflict,
   revocation, recovery export, cloud deletion, and negative cross-account
   tests. Capture URLs, request IDs, timestamps, and screenshots without secret
   values.
4. Verify the production Polar products, portal, refunds/terms/privacy links,
   transaction email, cancellation, renewal, and webhook replay behavior.
5. Obtain a separate explicit Ohad approval, then change checkout activation in
   a small isolated release. Roll back on any mismatch.

## Launch decision

**No-go today.** The repository foundation, migrations, GitHub sign-in,
configuration-aware provider UI, and disabled-checkout deployment are proven.
Accepting money still requires production Polar/webhook proof, an active live
account/continuity proof, and a separately approved checkout release.
