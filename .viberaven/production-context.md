# VibeRaven Production Context

## Current Release / Change Window

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

- Commit `e49a3317f87ac547496a28588774acbdb02069f1`: `python -m unittest discover -s tests -v` passed 249 tests in 24.568s on Python 3.11.4; one Windows symlink privilege test skipped while the junction/reparse rejection test passed.
- Synthetic pilot package: `e08c4e23921065839a234530261aae3f466c517fa0b93214669990f4dbdbe9ab`.
- Commit `7b584430dc6f0df33cd6ce3453e70f496d1ca3e0`: full suite passed 266 tests in 26.333s; fresh Windows clone passed 90 proof tests in 8.015s.

## Open Provider Or Human Actions
