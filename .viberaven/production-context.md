# VibeRaven Production Context

## Current Release / Change Window

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

- Commit `e49a3317f87ac547496a28588774acbdb02069f1`: `python -m unittest discover -s tests -v` passed 249 tests in 24.568s on Python 3.11.4; one Windows symlink privilege test skipped while the junction/reparse rejection test passed.
- Synthetic pilot package: `e08c4e23921065839a234530261aae3f466c517fa0b93214669990f4dbdbe9ab`.
- Commit `7b584430dc6f0df33cd6ce3453e70f496d1ca3e0`: full suite passed 266 tests in 26.333s; fresh Windows clone passed 90 proof tests in 8.015s.

## Open Provider Or Human Actions
