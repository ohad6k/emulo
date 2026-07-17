# Emulo Pro Encrypted Continuity Implementation Plan

> Execute test-first. This work must not enable checkout until every release gate passes.

**Goal:** Deliver the smallest paid Emulo Pro outcome worth charging for: an approved local generation follows a user to a second paired device, remains end-to-end encrypted, preserves conflicts and rollback history, and leaves the open-source local engine fully usable without payment.

**Architecture:** The Python companion owns all plaintext and keys. It uses the mature `cryptography` package for AES-256-GCM, X25519, HKDF-SHA256, and Scrypt. The Cloudflare Worker authenticates accounts/devices, enforces entitlement and ownership, stores only ciphertext plus bounded routing metadata, and applies optimistic parent concurrency. Device credentials are random bearer tokens stored only as hashes. D1 never receives raw sessions, evidence, profiles, workflows, private keys, account master keys, recovery secrets, or provider tokens.

## Task 1: Local cryptographic envelope and recovery material

**Files:**
- Modify: `pyproject.toml`
- Add: `emulo_autopilot/continuity_crypto.py`
- Add: `tests/test_continuity_crypto.py`

1. Add failing dependency/error tests proving the open-source engine still imports without the optional Pro crypto extra.
2. Add real cryptographic tests for fresh-nonce AES-GCM bundles, deterministic authenticated metadata, tamper rejection, wrong-key rejection, Unicode/CRLF round trips, and strict size/schema bounds.
3. Add X25519 + HKDF per-device master-key wrapping and tests for wrong-device rejection.
4. Add a random one-time recovery secret, Scrypt-derived wrapping key, explicit confirmation, and lost-secret failure tests.
5. Add private-material serialization helpers with strict permissions and no secret logging.
6. Run focused tests and commit.

## Task 2: Device enrollment and revocation boundary

**Files:**
- Add: `cloud/worker/migrations/0007_continuity_devices.sql`
- Add: `cloud/worker/src/device-auth.ts`
- Add: `cloud/worker/test/device-auth.test.ts`
- Modify: `cloud/worker/src/index.ts`

1. Add failing migration/store tests for one-time hashed pairing grants, five-device cap, hashed device tokens, public-key bounds, account ownership, expiry, replay, and revocation.
2. Implement browser-authenticated `POST /v1/devices/pair/start` and one-time `POST /v1/devices/pair/complete`; never place pairing or device bearer credentials in URLs.
3. Implement browser-authenticated `GET /v1/devices` and `DELETE /v1/devices/{id}` with no wrapped key or token leakage.
4. Require a webhook-confirmed write-capable entitlement for new pairing; existing local functionality remains unaffected.
5. Run focused Worker tests/type-check and commit.

## Task 3: Ciphertext generation storage and optimistic concurrency

**Files:**
- Add: `cloud/worker/migrations/0008_continuity_generations.sql`
- Add: `cloud/worker/src/continuity-store.ts`
- Add: `cloud/worker/src/continuity-routes.ts`
- Add: `cloud/worker/test/continuity-routes.test.ts`
- Modify: `cloud/worker/src/index.ts`

1. Add failing tests for authenticated upload, point-read head, owned generation download, ciphertext digest mismatch, cross-account denial, revoked-device denial, replay/idempotence, quotas, and exact method/content limits.
2. Store one bounded encrypted envelope per founding-beta generation (maximum 256 KiB encoded payload) plus generation ID, parent ID, author device, digest, byte size, and timestamps.
3. Advance the account head only when the submitted parent equals the current head. Preserve a divergent generation and return a typed conflict instead of merging or overwriting it.
4. Gate new writes by entitlement; allow the documented bounded recovery/export reads after entitlement loss.
5. Prove D1 rows and logs contain no synthetic plaintext marker.
6. Run focused Worker tests/type-check and commit.

## Task 4: Local generation packaging, transport, and atomic import

**Files:**
- Add: `emulo_autopilot/continuity.py`
- Modify: `emulo_autopilot/store.py`
- Add: `tests/test_continuity.py`

1. Add failing tests that package only the active approved generation manifest and its verified domain artifacts; never receipts, candidates, source paths, or session evidence.
2. Encrypt locally, upload through an injected HTTPS transport, persist a local pending-sync record on outage, and retry idempotently.
3. Download on a second device, verify metadata/digest/authentication, decrypt locally, validate the generation, and import through the existing atomic store rules.
4. Detect a divergent local head before activation and preserve both branches for explicit user resolution.
5. Prove local rollback remains available before and after cloud entitlement loss.
6. Run focused Python tests and commit.

## Task 5: Two-device proof, revocation, export, and deletion

**Files:**
- Add: `tests/test_continuity_two_device.py`
- Add: `cloud/worker/test/continuity-lifecycle.test.ts`
- Modify: privacy/security scans and production context

1. Run a synthetic two-device scenario: create/confirm recovery, pair A and B, activate on A, encrypt/upload, download/decrypt/import on B, then verify exact Unicode artifact bytes.
2. Prove tamper, wrong device, replay, stale parent, divergent branch, revoked device, cloud outage, and lost recovery secret all fail safely.
3. Add encrypted export manifest and account/device deletion paths with bounded server deletion and no implicit local purge.
4. Scan D1 fixtures, Worker output, repo files, and logs for the synthetic plaintext marker.
5. Run all Python/Worker tests, type-check, dependency audits, production config validation, dry-run bundle, and browser QA.
6. Record provider actions and remaining unknowns. Checkout stays disabled until Ohad separately approves activation after this proof.

