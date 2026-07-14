# Changelog

## 0.3.8 - 2026-07-15

### Added

- Google Antigravity session mining: `--source antigravity` (also included in `auto`) reads Antigravity's local transcripts (`~/.gemini/antigravity/brain/<conversation-id>/.system_generated/logs/transcript.jsonl`). Human text is exactly `USER_INPUT` records with source `USER_EXPLICIT`; the `<USER_REQUEST>` envelope and the harness-injected `<ADDITIONAL_METADATA>` block are stripped, and model/system records never enter the corpus. Discovery globs the `.system_generated` dot-directory explicitly because recursive `**` never descends into it. Session labels carry the conversation id (every transcript file shares the same name). Verified live against a real local Antigravity install (14 sessions, 31 typed messages mined) and against a simulated fresh user home via auto-detect, explicit source, and a full corpus write. Antigravity only persists transcripts when interaction logging is enabled in its privacy settings. Requested by a Reddit comment on the launch thread.
- The `v0.3.8` bootstrap runtime pins `ditto.py` to SHA-256 `105035541d4d0edb5153e61abaadbf9f7f819492f24c80b5d2a06480eb1c6ab4`; `MINING_PROMPT.md` is unchanged.

## 0.3.6 - 2026-07-14

### Added

- Official MCP Registry metadata: an `mcp-name: io.github.ohad6k/ditto` marker in the README lets the registry verify the published `ditto-cli` PyPI package, and a `server.json` describes the stdio MCP server (run with `uvx ditto-cli mcp`). No runtime behavior changed from 0.3.5.
- The `v0.3.6` bootstrap runtime pins `ditto.py` to SHA-256 `2428e5acc7dc5f87cd87182ce946705a7c4ec0dd7f2f221b3d61f9ceec5c49b2`; `MINING_PROMPT.md` is unchanged.

## 0.3.5 - 2026-07-14

### Added

- Native Claude Code plugin packaging: `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` expose the existing four skills (`mine`, `work`, `design`, `write`) through Claude Code's native plugin system, installable with `/plugin marketplace add ohad6k/ditto` then `/plugin install ditto@ditto`. Skills auto-discover from `skills/`, so the same folders serve both Codex and Claude. Manifest correctness is gated by the same static-manifest tests as the Codex plugin. Not yet verified against a live `/plugin install` (no Claude executable in the build environment) — the same boundary the 0.2.0 Codex plugin had before a real CLI confirmed discovery.
- MCP server: `python ditto.py mcp` runs a stdlib-only stdio JSON-RPC server exposing one tool, `load_ditto_profile`, which returns the active work/design/write profile so any MCP client (Claude Desktop, Cursor, and others) can load the user's profile before a task. No dependency was added; `ditto.py` stays one stdlib file. Verified by 11 tests including a real subprocess round-trip (`initialize`, `tools/list`, `tools/call` over stdio). Not yet verified against a live third-party MCP client.
- The `v0.3.5` bootstrap runtime pins `ditto.py` to SHA-256 `6e869021115dca0a8eb0f14c968ea2f854f8124bfc0915a6fd64a63276fcbbd4`; `MINING_PROMPT.md` is unchanged.

### Why it matters

The MCP server reaches the MCP client and registry ecosystem (Claude Desktop, Cursor, mcp.so, and similar) that a skill-only tool could not, and native Claude plugin packaging closes the last gap in the "install Ditto in your agent" matrix. Both are additive: the mining core, caches, and profile contract are unchanged.

## 0.3.4 - 2026-07-13

### Added

- OpenCode session mining: `--source opencode` (also included in `auto`) reads OpenCode's current SQLite store (`~/.local/share/opencode/opencode.db`, opened read-only, one mined session per stored session) and the legacy per-file JSON layout (`storage/session/…` with sibling `message/` and `part/` directories). Human text is exactly part rows of type `text` on `role: user` messages; synthetic parts, reasoning, tool output, and assistant text never enter the corpus. `XDG_DATA_HOME` overrides the data root. Verified live against a real OpenCode 1.17.19 store: the mined corpus contained the two typed prompts from real sessions and nothing else. Requested by the same Reddit thread as v0.3.3, about an hour later.
- The `v0.3.4` bootstrap runtime pins `ditto.py` to SHA-256 `80ab07118cf8cd09a13a23e48cb9a9e1d596864a822efdefdb955486ea108fb9`; `MINING_PROMPT.md` is unchanged.

## 0.3.3 - 2026-07-13

### Added

- OpenCode adapter: `python ditto.py --install you.md --target opencode` writes the marked profile block into OpenCode's global rules file (`~/.config/opencode/AGENTS.md`, same path on Windows), which loads in every session. Verified live against OpenCode 1.17.19: a real turn quoted the profile as its loaded instructions and described the user from it. OpenCode also reads project `AGENTS.md` (existing `--target agents`) and discovers `~/.claude/skills` natively, so the Claude skill install works there too. Requested by a user on Reddit within the hour.
- The `v0.3.3` bootstrap runtime pins `ditto.py` to SHA-256 `a1bdc4efb96113a8699e57b70ccf5af30223d58b190430e8b4d229726958296f`; `MINING_PROMPT.md` is unchanged.

## 0.3.2 - 2026-07-13

### Fixed

- Redaction now catches credentials in the forms people actually paste to an agent: `the wifi password is hunter2`, `psk …`, `wifi key …` — guarded so prose about passwords (`the password is wrong`) survives, and `pwd` is not a keyword so shell commands stay intact. The phone pattern no longer swallows dates, part numbers, and version strings (874 false redactions on one real corpus); it requires an international `+CC` prefix or a national trunk `0` (parenthesized area codes included), verified against Israeli, Australian, UK, German, and US international formats. Bare domestic formats with neither marker (`415-555-2671`) are no longer matched — the old pattern caught them only by the same over-matching that ate dates. From PR #9 by @terencedubois7-cmd, with review corrections (Israeli mobile coverage, parenthesized formats, `boarding pass` false positive). **If you ran Ditto before this release, grep your existing `ditto-out/` for anything sensitive before sharing it.**
- Root-level generated lens files (`you-appendix.md`, `you-thinking.md`, `you-designer.md`, `you-writer.md`) are gitignored so a `git add -A` inside a repo clone can never publish them.
- Claude Code mining now keeps only turns a human actually typed. Subagent transcripts (85% of files on one real history), tool results, harness meta records, model-written compact summaries, task notifications, command XML, and `[Request interrupted` turns are dropped; on the verified corpus that removes 78% of mined characters, all machine text that was deflating real traits' receipt counts. From PR #8 by @terencedubois7-cmd, with one fact-check correction: Claude Desktop stamps `promptSource: "sdk"` on human-typed prompts, so the filter keys on `origin.kind` and only treats sdk + headless `sdk-cli` entrypoint as machine.
- Codex mining now also reads `~/.codex/archived_sessions` (a second store the extractor never saw) and honors `CODEX_HOME`. Codex control envelopes (`subagent_notification`, `codex_internal_context`, `codex_delegation`, `turn_aborted`, `heartbeat`) are stripped out of role:user turns — 41% of role:user characters on one real 12GB corpus — and `<image>` attachment markers no longer leak local file paths into the corpus. From PR #10 by @atramenta-gargalizene, adjusted after fact-checking a real history (bare `<skill>` stays unfiltered, envelope stripping keeps surrounding human text).
- `EXTRACTION_SCHEMA_VERSION` bumps `1` -> `2`: segments cached under the old extraction rules are invalidated and re-mined instead of silently reused.
- The `v0.3.2` bootstrap runtime pins `ditto.py` to SHA-256 `c9811ce7d2413b7bb57f938c17090465244453dec40f7659138c5fffcd673cb5`; `MINING_PROMPT.md` is unchanged.

### Why it matters

All three fixes come from contributors who ran Ditto on real histories and looked at what it actually read and wrote. The corpus is the product: machine text in it deflates every real trait, and one leaked credential in it is one too many.

## 0.3.1 - 2026-07-13

### Changed

- `--card` terminal render rebuilt as a shareable ASCII card: a solid-block DITTO logotype and the engraving rendered as classic ASCII art with directional stroke shading, in a side-by-side layout on wide terminals (the fixed mark, same in every screenshot), your archetype and mined stats, each law with a filled evidence bar (`████████░░  18/20 sessions`), and the uncomfortable one. ANSI color accents on real terminals; respects `NO_COLOR`; falls back to a plain ASCII box if the console can't draw blocks. The art is pure ASCII, so every glyph survives any pipe or wrapper; box-drawing frame glyphs are chosen from the cp1252-safe set.
- On a real terminal, `--card` now plays a four-act reveal in the alternate screen (no scrolling or tearing): fragments of your own mined laws flicker past while your session count spins up, the engraving develops from faint texture to contour linework, the verdict lands and the evidence bars fill, and the uncomfortable one types itself out in red. The finished card is then printed to the real screen so it stays in your scrollback. `--still` (or `DITTO_NO_ANIM=1`) skips the animation; piped and captured output is always static.
- The card output now points somewhere: after `card.html` is written, Ditto prints the community share thread (`github.com/ohad6k/ditto/issues/1`) so a rendered card has a one-line path to being posted. Share the card or one short trait, never your full profile.
- The `v0.3.1` bootstrap runtime pins `ditto.py` to SHA-256 `176fd02fb07dd77fd1a1dd12cd4c482c7d8c48c8daa6a234628f1a8932aef12f`; `MINING_PROMPT.md` is unchanged.

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
