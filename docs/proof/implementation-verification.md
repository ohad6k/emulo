# Ditto Proof v1 implementation verification

Observed on 2026-07-15 in the isolated `codex/ditto-benchmark-proof-release` worktree.

## Receipt

- Verified harness commit: `7b584430dc6f0df33cd6ce3453e70f496d1ca3e0`
- Runtime: Python 3.11.4
- Operating system: Microsoft Windows NT 10.0.26200.0
- Command: `python -m unittest discover -s tests -v`
- Result: 266 tests passed in 26.333s; one symlink test skipped because Windows did not grant symlink privilege. The real Windows junction/reparse-point rejection test passed.
- Fresh-checkout command: clone the committed branch into a new temporary directory, then run `python -m unittest discover -s tests -p "test_proof_*.py" -v`.
- Fresh-checkout result: 90 proof tests passed in 8.015s from a fresh Windows clone; the same privilege-only symlink test was skipped and the junction test passed.
- Synthetic pilot-package SHA-256: `e08c4e23921065839a234530261aae3f466c517fa0b93214669990f4dbdbe9ab`
- Integrity command: `git diff --check`
- Integrity result: clean output at the verified harness commit.

The end-to-end synthetic test sealed six clean temporary Git fixtures outside the repository, froze two harmless synthetic host identities, constructed 24 pairs, prepared 48 different homes and workspaces, appended synthetic attempts/evaluations/reviews, recalculated the exact publication digest, rejected a seeded privacy leak, and produced byte-identical clean packages. The hardened pass additionally proved tracked-only fixture sealing, cross-checkout LF stability, deep manifest validation, exact installed-context and instruction hashes, stored evidence/review provenance, complete ship-digest binding, and mandatory manual privacy inputs.

## Boundaries

- no provider execution
- no scored fixture execution
- no public result
- no Antigravity dependency
- no modification to normal Ditto behavior

The harmless argv values embedded in the synthetic manifest were never passed to `execute_cell`. The proof package remains standalone and is not imported by `ditto.py`. Live provider selection, cost approval, sealed private task content, reviewer consent, 48 scored executions, clips, claims, outreach, and publication remain separate gated work.
