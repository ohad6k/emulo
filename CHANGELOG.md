# Changelog

## 0.3.0 - 2026-07-13

### Changed

- Added voice registers to the writing profile. Every mined `write` evidence item and rule now carries a `register`: `casual`, `professional`, or `shared`. Ditto used to average every voice you use into one blend, which made agent-drafted messages to a boss or client read too casual; registers keep those voices separate. Requested by a user who ran Ditto on ~120 sessions (see `docs/FEEDBACK.md`).
- An active `you-writer.md` is now grouped under `## Voice laws` (always apply), `## Casual register`, and `## Professional register`. A rule keeps its evidence's single register; mixed-register evidence reduces to a shared voice law. A rule can never claim a register its receipts do not show.
- The `ditto:write` skill now picks the register from task context instead of asking: an explicit audience statement wins, otherwise the pasted thread, recipient, or artifact type decides, and the pick is stated in one correctable line. Existing flat writing profiles still load unchanged.
- Register classification happens at mining time from the receipts (audience, platform, artifact type). Messages addressed to the agent count as casual signal only and never support a professional register.
- Schema bumps for the contract change: report `1` -> `2`, mining prompt `1` -> `2`, reducer `1` -> `2`, scout report `2` -> `3`, domain draft `1` -> `2`. Existing installed profiles keep loading; the next mining run re-mines under the new contract instead of reusing pre-register caches.
- The `v0.3.0` bootstrap runtime pins `ditto.py` to SHA-256 `1eb0f2698f284ee3983a055b9dcf95af131e7c6d0a448e524df271fb2d38102d` and `MINING_PROMPT.md` to SHA-256 `878454ad853b0b9730e852d66267230627ad3141de478cf16716062c11fab8b2`.
- Added `docs/FEEDBACK.md`, a running log of user feedback and what each item changed.

### Why it matters

One voice profile was the wrong shape: people write differently to a boss than to a subreddit, and the profile flattened that. Registers are mined, not asked, so the split costs the user nothing, and the loader infers the audience from context so using it costs nothing either.

## 0.2.0 - 2026-07-11

### Changed

- Added the native Codex plugin with four namespaced skills: `ditto:mine`, `ditto:work`, `ditto:design`, and `ditto:write`.
- Made full-history mining the quality default. The bounded `--preview` path is explicitly a starter profile from selected history, not the full profile.
- Added deterministic segment, report, domain-draft, and reduction caches with corrupt-cache quarantine and zero-call reuse only when the cached profile is fully valid and activatable.
- Added atomic profile activation, isolated migration/cutover/rollback, and separate work, design, and writing profile routing.
- Kept adaptive recall experimental and outside the default Plugin release path.
- Added the cross-agent `npx skills add ohad6k/ditto@ditto` bootstrap. Its `v0.2.0` runtime pins `ditto.py` to SHA-256 `82f6d15d5e535fa24b495b97bb9ac1b8dbb1b61c6c62786b49d2dc5698c7cd77` and `MINING_PROMPT.md` to SHA-256 `633a48bc0eb743cd6f13bf0f6783fcfb2653df4a353b6a303fb0d213c2b068f6`.

### Why it matters

Ditto can now keep setup/mining separate from the personal layers used during normal work. Full mining favors profile quality; quick preview remains available when a user knowingly prefers a bounded starter. Updates reuse validated evidence without trusting incomplete or semantically tampered cache state.

### Upgrade

Cross-agent bootstrap:

```bash
npx skills add ohad6k/ditto@ditto
```

Native Codex plugin:

```bash
codex plugin marketplace add ohad6k/ditto --ref v0.2.0 --json
codex plugin add ditto@ditto --json
```

Existing classic `you` profiles are staged and cut over through the migration commands; cutover removes the legacy skill from discovery before activating the new pointer, and rollback restores the prior bytes and pointers.

### Verified

- `127` unit tests pass on the release candidate. The Codex plugin validator and cross-agent bootstrap skill validator pass, both CLI help surfaces exit successfully, both JSON manifests parse, and `git diff --check` passes.
- Two independent read-only reviews, one for spec compliance and one for Python safety/quality, returned `PASS` on commit `328ecc61`; the final evidence record is commit `7acbcc89`.
- Codex CLI `0.142.5` discovered exactly the four native Ditto skills. Plugin uninstall/reinstall preserved an isolated private `DITTO_HOME` byte-for-byte, and isolated migration cutover/rollback restored the exact legacy state.
- The permanent frozen bounded calibration remains in `tests/fixtures/bounded-calibration-baseline.json`. Its widest candidate selected `159,919` source tokens, used three workers plus one reducer, and recovered `5/22` frozen requirements, so preview is not the quality default.
- A real full-history mine ran against a frozen, locally redacted snapshot of the maintainer's actual corpus: `1,968` sessions, `3,284,544` selected source tokens, `147` validated worker reports, `846` validated evidence items, and one strong reducer. The activated profile version is `e61ae342557034ff9a9b` with manifest SHA-256 `7795a1efeea0c1291b0e20afdf10d310e4984c5aeb8a4b66dba87a09a4f99e4a`; work, design, and writing are active with five rules each.
- The identical frozen-corpus update then planned `0` workers and `0` reducers with all `147` segments cached and report-set SHA-256 `d74195b1f10ea31dfc0cfa787cd5aa1fb2248a18a4797e614e73a9b6fb49eaec`.
- The unchanged private calibration recovered `12/22` requirements: work `5/10`, design `5/5`, and writing `2/7`. This is better than quick preview's `5/22` but is not a passing complete-profile score.
- Extraction and redaction happen locally before selected text reaches the user-chosen model. `ditto.py` makes no network calls. The skills.sh bootstrap downloads only the two pinned runtime files before log discovery and verifies both hashes.

### Known limits

- Full history is the quality default relative to bounded preview, but the first real run still missed `10/22` frozen traits. In particular, several explicit workflow and writing-voice constraints were absent from the fresh profile. Do not claim full mining guarantees complete recall.
- The run produced exactly `147` successful assigned reports and one reducer, but additional failed or aborted compatibility attempts occurred while correcting Windows sandbox writes, launcher exit-code handling, and an oversize CLI-input ceiling. Ditto cannot report exact provider billing for those attempts.
- Codex native routing was proven but was not uniformly clean when an older global Ditto profile competed under the host skill-description budget. The release does not claim perfect exclusive routing in that mixed legacy environment.
- Native Claude plugin packaging is not claimed because the Claude executable was unavailable. Claude Code remains supported through the skills.sh bootstrap and direct adapter.
- Benchmarks, leaderboard results, and launch videos are deferred to a separate later release.
