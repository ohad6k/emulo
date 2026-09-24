# Changelog

## 0.6.4 - 2026-09-25

### Fixed

- **`--coach` stated causes it cannot see.** Every check is a text match on the messages you typed, yet 0.6.3 printed the reason as fact: three identical sends meant "the model had already given everything that prompt could get", a message saying "as I said" meant you "re-explain things the agent was already told" and "paid for twice", a reword run "usually means the first one was missing a constraint", and a correction rate was "high enough to point at the opening prompt rather than the model". None of that is in the text. Found in a review that checked each claim the report prints against what the code measures. Titles and meanings now say what was counted ("Messages that say you already said it") and offer the fix as a possibility ("If the agent had lost it, stating it once in a profile or rules file saves retyping it"). The report says once, under its header, that these are text matches that cannot tell why you repeated something or whether the agent forgot anything, and that each finding shows its receipts so you can judge. Each finding's `key` and the `--json` shape are unchanged.
- **A phrase inside quoted or pasted text counted as you restating context.** An email you were answering ("> like I said last week") or a paragraph you asked to have proofread ("As I said in the last update...") read as you repeating yourself. Fenced code blocks, lines starting with `>`, and double-quoted spans, straight or curly, are now masked before the restated-context phrases and the correction openers are matched, and a receipt is windowed on the phrase that was counted rather than on an earlier quoted copy. A genuine "as I said, use pnpm not npm" still counts. One deliberate side effect: a correction written after a quoted line now counts, because the first words you wrote yourself are a correction. A paste with no quote marks at all still counts, since nothing in the text tells it apart from your own words.
- **The browser scan at `/scan` carried the same claims.** It runs its own port of `--coach`, so it gets the same titles and meanings, the same text-match line under the result, and the same quoting rule. Its intro no longer says you "re-explained context", and its search description no longer promises to find "lost context".
- The README said `--coach` finishes in seconds. It now says it takes about a minute on a big history, and describes the checks as text matches.

### Verified

- 17 new tests in `tests/test_usage_report.py`: eight for the quoting rule (pasted paragraph, curly quotes, fenced block, quoted email line, a genuine "as I said", a genuine phrase next to a quote, a receipt that must window on the counted copy when the same phrase also sits inside the quote, a correction after a quoted line), one guard that a correction opener inside a quote still does not count (openers only match at the start of a message, so it passed before this change and is not evidence for the masking), four for the wording (no cause stated as fact, no dashes, keys unchanged, every check fires on the fixture), two for the printed report (the text-match line appears exactly once, `--json` keeps every key), and two for history edge cases. With `HOME`, `USERPROFILE`, `CODEX_HOME` and `XDG_DATA_HOME` all pointed at an empty directory, `--coach` and `--coach --json` exit 1 with the existing "no session logs found" message, name every path they looked in, and write nothing. A single Claude Code session with three messages produces a readable report and valid JSON.
- Against one real history (1,394 sessions, 5,701 messages), restated-context matches went from 71 to 66. All five dropped matches were pasted or generated text rather than something typed: two of Emulo's own mining chunks sent through Claude Code, an agent-written design brief, a message between agent sessions, and a notes digest. Repeat sends (11) and corrections (79, 1%) did not change. A run takes about a minute over roughly 1,400 sessions on one Windows machine (three runs: 54 to 71 s), and each run left the directory it ran from empty.
- Not fixed, found by the same run: 10 of the remaining 66 matches sit inside those mining chunks, which reach `--coach` as if they were typed. That is an unmarked paste the quoting rule cannot see.
- Full suite on Python 3.11 with the `[pro]` extra: 542 tests, 5 skipped, 0 failures. On Python 3.13 without `cryptography`: 520 tests, 13 skipped, 0 failures. On Windows the symlink tests skip, and the two release pin tests skip until the `v0.6.4` tag exists.
- Site tests after a clean `npm ci`: 38 tests, 0 failures, including a new parity case where the browser scan and `emulo.py` must produce the identical report for quoted, fenced, curly-quoted and `>` text. On the same nine-message fixture, the page drove through its real folder-picker path now shows "Messages that say you already said it. 3 messages" where it showed "You re-explain things the agent was already told. 6 messages": the three markers it no longer counts were all inside quoted or pasted text.
- The `v0.6.4` bootstrap runtime pins `emulo.py` to SHA-256 `9006632a609e8f48` (prefix); `MINING_PROMPT.md` is unchanged at `ee22077c2cda3c1c` (prefix). Full digests in `.agents/skills/emulo/runtime.json`.
- Not verified: Python 3.8, because no 3.8 interpreter is installed on the release machine, and `pip install emulo==0.6.4` from PyPI, because the version is not published at the time of writing.

## 0.6.3 - 2026-09-24

### Added

- **`emulo.py --coach` reports how you use the model, without mining anything.** The first substantive reply to the outreach round asked for exactly this: a mode focused on improving Claude Code usage rather than extracting conventions. The data was already there. Failure modes are mined today, but they are written to the agent under "protect this person from these" and never addressed to the person. `--coach` reads the same local logs and answers the other question: asks sent three times in a row unchanged, context re-explained after the agent lost it, runs of rephrasing the same request, and the rate of turns that open by correcting the last answer. It makes no model call and writes no corpus, so it runs in seconds on a first install, before anyone has decided whether mining is worth it. `--source claude` narrows it to Claude Code, and `--json` emits the same report for other tools to consume.
- Every finding carries the dated messages behind it, and a quote whose evidence sits 400 characters into a long message is windowed onto the match rather than clipped from the start, because a receipt you cannot read is not a receipt. Checks that come in under their bar are printed with their counts, so a clean result reads as a measured result and not as a check that did not run.
- `emulo --version` prints `emulo 0.6.3` and exits 0. It used to fail with `unrecognized arguments: --version` and exit 2, so a bug report had no one-line way to say which build it was about.
- A contributor guide, issue templates that spell out what not to paste from your own logs, and a PR checklist (#24). `docs/SOURCES.md` lists every session source Emulo reads today and the ones planned, each traced to the code and tests behind it (#27).
- Tests for the Copilot CLI source, which had none of its own (#32), and for the card display layer (#28).

### Fixed

- **Two harness preambles were being mined as things the user wrote.** `# Context from my IDE setup:` (an editor stapling the open file and tab list onto the turn) and `# Files mentioned by the user` (Codex listing attachments) both reached the corpus as ordinary prose. On one real corpus that is 2,543 messages, and because they repeat near-verbatim for as long as the same file stays open, mining reads them as deeply held rules. Both are now in `INJECTED_CONTEXT_PREFIXES`, which fixes the mined profile as well as the report. Found by running `--coach` against real logs and reading the receipts it printed: the loudest finding in the first run was an IDE preamble counted as the same ask sent twelve times.
- **`emulo --card` crashed on a card.json with `"first_date": null`.** A reducer that writes null instead of an empty string sent `None[:4]` into `months_between`, and the TypeError escaped both the terminal card and the HTML card. The card tests in #28 found it and pinned it as an expected failure. The first fix (#30) caught TypeError and was still incomplete: slices are hashable from Python 3.12, so a date that arrives as a JSON object raises KeyError there instead, and #30's own test failed on 3.12 while passing on 3.11. Checking the rest of the card path turned up three more shapes that crashed it: a number for a date broke the HTML date range, a list printed its Python repr on the card, and `"stats": null` crashed both renderers and `load_card`. Dates are now read only when they are strings, a `stats` that is not an object reads as empty, and a missing value drops its row like every other missing stat.
- **Parts of `emulo.py` raised on Python 3.8, the declared floor.** Three `dict |` merges in the adaptive run path are 3.9+. @Spagles found them by reading the code (#44). CI only ran 3.12, so the `requires-python >=3.8` promise was never checked. CI now runs 3.8 and 3.12, and `tests/test_python_floor.py` walks the AST for anything above 3.8, because the three fixed call sites sit in functions no test executes (#46).
- The README said the MCP server returns a work, design or writing profile. `load_emulo_profile` has served the video profile since 0.4.0. It also said the Codex plugin was proven with four skills; it ships five (#31).
- A working planning document under `docs/superpowers/` had been committed past the ignore rule. It is removed from the tree.

### Verified

- Thresholds were set by measurement against a real 2,271-session corpus rather than by guess, and the measurement changed the feature three times. Repeat runs with no word floor were almost entirely `ok`, `yes`, and `ok do it` sent three times, which is approval and not a loop; with a four-word floor the same corpus yields one genuine run. Widening the rule from consecutive sends to sends within three turns added only filler repeated 84 turns apart, so the rule stayed strict.
- Sampling the matches caught two more defects before release. `no need for the repo` counted as a correction, and a 1.4% correction rate was being reported as a problem, so corrections now need to clear a rate bar and the rate prints either way for anyone who wants to disagree with the bar.
- **The reword-loop check is unproven and is shipping anyway, which is worth stating plainly.** Across every corpus available to test it, it fired exactly once, on a pasted pygame banner sent three times, and a line-count guard now excludes that shape. It has no confirmed true positive. It ships because the behaviour it looks for is real and cheap to check, and because a check that finds nothing prints its zero rather than staying silent. Treat a hit from it with more suspicion than a hit from the other three.
- 29 tests cover the loop detectors, the exclusions, receipt quality, the injected preambles, redaction of receipts, and the promise that `--coach` leaves no files behind.
- Known limits, stated in the report itself: it reads only the messages you typed, which is all Emulo keeps, so it cannot see cost, tokens, tool calls, or whether the agent was right, and it does not score them.
- Full suite passes on Python 3.10 and 3.11 with the `[pro]` extra installed: 525 tests, 5 skipped, 0 failures. Under pytest on 3.11: 520 passed, 5 skipped. On Python 3.13 without `cryptography`, which matches CI's dependency-free 3.8 lane: 503 tests, 13 skipped, 0 failures, the extra skips being the continuity tests that need the extra. On Windows three symlink tests skip, and the two release pin tests skip until the `v0.6.3` tag exists.
- Not verified locally: Python 3.8 itself, because no 3.8 interpreter is installed on the release machine. CI's 3.8 lane is that check.
- `emulo --card` against a card.json with null dates: on the previous `main` it exits 1 with `TypeError: 'NoneType' object is not subscriptable`; on 0.6.3 it exits 0, prints the card with sessions and tokens, and writes card.html without the months cell or the date range.
- The `v0.6.3` bootstrap runtime pins `emulo.py` to SHA-256 `dad6aa010382016f` (prefix); `MINING_PROMPT.md` is unchanged at `ee22077c2cda3c1c` (prefix). Full digests in `.agents/skills/emulo/runtime.json`.
- Not verified: `pip install emulo==0.6.3` from PyPI, because the version is not published at the time of writing. Run that against a clean virtualenv after the tag.

## 0.6.2 - 2026-07-27

### Added

- **`emulo verify` traces every quote in a profile back to a real session.** A mined profile earns trust from its receipts, and the worst failure it can carry is not a missing rule but a confident rule quoting something the person never said. Nothing checked that. `emulo verify you.md` extracts every quoted span, searches the mined corpus for it, reports what it cannot find and exits non-zero. Quotes resting on a single session are flagged separately, because one session is context rather than a rule. `--json` emits the supporting session ids per quote, and that report is safe to hand to someone else: it carries quotes already present in the draft plus opaque session ids, and no session text, so a profile's receipts can be checked without its owner disclosing their logs.
- Straight quotes are paired in document order rather than by regex alternation. Alternation invents quotes out of the prose sitting between one span's closing mark and the next one's opening mark; against a real profile it reported nonsense fragments as unfound receipts. There is a regression test for exactly that shape.

### Fixed

- **The release pin test made every feature branch red.** It hashed the working tree and compared it to the digest in `runtime.json`, an equality that only holds at a release commit, so any branch editing `emulo.py` failed CI by construction. CI that always fails carries no information and the next real regression gets waved through. The pin is now checked against the bytes at the pinned tag via `git show <ref>:<file>`, which is what the bootstrap actually promises and is true on any branch. The useful half of the old assertion is kept in a second test that enforces the working tree against the pin only when `HEAD` is the release commit, which is exactly when forgetting to re-pin matters. CI checks out with `fetch-depth: 0`, since without tags the pin test cannot resolve the release bytes and would skip, retiring the guard silently.
- The `--json` report embedded the absolute profile path and output directory, so sending it disclosed a home directory, a username, and often a project name. It now carries the profile's file name only.

### Verified

- Full suite passes: 415 tests, 4 skipped, 0 failures, with 0.6.2 pinned across `emulo.py`, all four plugin manifests, the marketplace manifest, `server.json`, and the bootstrap runtime.
- Run against a real 2,177-session corpus and a real profile, `verify` immediately caught quotes that had been silently tidied. The source said `its feel static beucase you just dont move the character` while the profile rendered it in corrected English, which makes the receipt untraceable. 24 of 31 quotes failed on the first pass of a profile that had been written carefully the same day; after correction, 29 of 30 trace to a real session.
- The `v0.6.2` bootstrap runtime pins `emulo.py` to SHA-256 `982f51ed751a0a21` (prefix); `MINING_PROMPT.md` is unchanged at `ee22077c2cda3c1c` (prefix). Full digests in `.agents/skills/emulo/runtime.json`.
- Not verified: `pip install emulo==0.6.2` from PyPI, because the version is not published at the time of writing. Run that against a clean virtualenv after the tag.

## 0.6.1 - 2026-07-26

### Fixed

- **`pip install emulo` left the user at a dead end.** The published package ships `emulo.py` alone, but the miner's closing line told the user to "paste MINING_PROMPT.md" - a file pip never installs. Anyone following the documented `pip install` path had no way to reach the contract that instruction named, short of finding it on GitHub by hand. The bootstrap path was never affected: `npx skills add` downloads `MINING_PROMPT.md` alongside `emulo.py` at the pinned release tag after SHA-256 verification, so agent-driven users always had it. This closes the pip path specifically.

### Added

- **`RUN_ME.md` is written into the mining output directory.** It is self-contained: it lists every generated chunk by path, states the one-pass-per-chunk-then-merge shape, carries the four domains and the evidence bar (a rule without a verbatim dated quote gets cut), names `you.md` as the output, and ends with the install command for each supported target. The remaining step after `emulo` is now one line to an agent, `read emulo-out/RUN_ME.md and follow it`, with nothing to paste and nothing else to download. The dry-run plan and the README CLI section were updated to match.

### Changed

- **The site pricing section no longer advertises Emulo Pro.** The monthly and annual plans were displaying prices behind a "Coming soon" button for a product that cannot be bought yet, and the page's `SoftwareApplication` structured data still declared `$9` and `$79` Offers, so search results could surface prices with nothing behind them. Both plan cards and both Offer entries are removed. The second pane now describes the Profile Build service and links to email rather than checkout. The `.pro-plan` styles are deliberately kept so the plans can be restored unchanged when Pro is real, and the exact pane markup plus both Offer entries are preserved verbatim in `docs/site-pro-pricing-withdrawn.md` with restore steps. Nothing about Pro pricing was discarded; it is parked outside `site/` because `vercel.json` serves that whole directory, so an HTML comment would still ship `$9` and `$79` in the page source.

### Verified

- Full suite passes: 398 tests, 3 skipped, 0 failures, with 0.6.1 pinned across `emulo.py`, all four plugin manifests, the marketplace manifest, `server.json`, and the bootstrap runtime.
- `tests/test_site_pricing.py` was rewritten to assert the new intent rather than dropped. It previously required `$9`, `$79`, `$108` and `Save 27%` to be present; it now fails if any plan price, discount, `Coming soon` button, checkout host, or paid-account URL reappears on the static page, and it checks the visible page and the structured data agree.
- A new test executes the miner and asserts that every path `RUN_ME.md` points an agent at exists on disk, and that the file never refers the user to a repository file the package does not install. The previous handoff would have failed this test; no string-comparison test could have caught it.
- Checked against a real 103-session Claude Code history: the run wrote 15 chunks and a `RUN_ME.md` naming all 15 at their real paths. Reruns producing fewer chunks rewrite it to match.
- The `v0.6.1` bootstrap runtime pins `emulo.py` to SHA-256 `1814815ce87dd122` (prefix); `MINING_PROMPT.md` is unchanged at `ee22077c2cda3c1c` (prefix). Full digests in `.agents/skills/emulo/runtime.json`.
- Not verified: `pip install emulo==0.6.1` end to end from a clean virtualenv, because the version is not published. Run that against PyPI after the tag, before telling anyone the pip dead end is closed.

## 0.6.0 - 2026-07-20

### Added

- **Repeated procedures are mined as workflows.** Beyond taste, mining now captures how you build: the order you fix things in, what you regenerate before what, what you check before calling a step done. A sequence demonstrated in a single session stays context; a real procedure needs two distinct sessions like every other rule. Validated procedures group under a `## Workflow` heading in the domain profile, each rule stating its ordered steps in sequence order, carried through `draft-manifest.json` with their evidence IDs at the same evidence bar as every other rule. This widens what a profile can express, hence the minor bump.
- **The bootstrap offers the native plugin once mining finishes.** Previously it installed the core profile and stopped, so anyone following the site never reached the namespaced `emulo:` skills, and nothing in the repository ran a plugin install at all. New step 9 offers it once after the run reports, asks first, takes a no, and skips the offer when the host already has the plugin. It pins an exact release tag rather than `main`. Codex can run the install itself; in Claude Code `/plugin` is typed by the user and an agent cannot execute it, so the agent prints the two exact lines to paste instead.
- `pip install emulo` is documented in the Quickstart and on the site. The published package was already on PyPI but appeared in no install instructions, so `git clone` stayed the dominant install path.
- The site gained a questions section with `FAQPage` structured data, covering how this differs from agent memory, whether session logs leave your machine, supported agents, and cost.

### Fixed

- **The install command on the site prompted instead of installing.** The site shipped `npx skills add ohad6k/emulo` while the README shipped `ohad6k/emulo@emulo`. The skills CLI scans both `skills/` and `.agents/skills/`, so this repository exposes six skills to it and only auto-selects when it finds exactly one. The bare form fell through to a multiselect asking the user to pick, with no indication which entry was the bootstrap. This regressed on 2026-07-10 when the routed skills landed and went from one skill to five, and the docs were never updated. All four places on the page plus `llms.txt` now carry the explicit form.

### Verified

- Full suite passes with the widened evidence contract and 0.6.0 pinned across `emulo.py`, all four plugin manifests, the marketplace manifest, `server.json`, and the bootstrap runtime.
- The `v0.6.0` bootstrap runtime pins `emulo.py` to SHA-256 `22e305f97759fdf1` (prefix) and `MINING_PROMPT.md` to `ee22077c2cda3c1c` (prefix); full digests in `.agents/skills/emulo/runtime.json`.
- `pip install emulo` checked end to end from a clean virtualenv against the published package rather than the local checkout: the `emulo` entry point runs, and `emulo mcp` answers `initialize` and `tools/list` over stdio with the `load_emulo_profile` tool.

## 0.5.0 - 2026-07-16

### Changed

- **Ditto is now Emulo.** The name collided with several existing products (heyditto.ai, ditto.live, and a `ditto` skill already on ClawHub), so the project renamed rather than fight three namespaces. Everything ships under the new name: the module is `emulo.py`, the CLI command is `emulo` (with `emulo-cli` kept as a deprecated alias), the PyPI package is now `emulo` rather than `ditto-cli`, the MCP server is `emulo` with the `load_emulo_profile` tool, the plugin and marketplace manifests are `emulo`, the bootstrap skill lives at `.agents/skills/emulo/`, and new profile blocks are written between `<!-- emulo profile:start/end -->` markers.
- Nothing about existing installs breaks. `EMULO_HOME` wins, but `DITTO_HOME` is still honored, and an existing `~/.ditto` home keeps working in place when no `~/.emulo` exists (no data is moved). Old `<!-- ditto profile:start/end -->` adapter blocks are still recognized everywhere blocks are read, and are upgraded to the new markers on the next write. The legacy profile id `ditto-work-profile` remains accepted.
- Historical records (older CHANGELOG entries, planning docs under `docs/`) keep the old name; they describe the project as it was.

### Verified

- Full `python -m unittest discover -s tests` passes (270 tests) under the new name. Legacy support checked live: `DITTO_HOME` resolution, `EMULO_HOME` precedence, legacy-marker detection, single-pass block upgrade with no duplicates, and legacy-marker removal.
- The `v0.5.0` bootstrap runtime pins `emulo.py` to SHA-256 `fac8333eca676f2b` (prefix) and `MINING_PROMPT.md` to `8d31170cb94b0b42` (prefix); full digests in `.agents/skills/emulo/runtime.json`.

## 0.4.0 - 2026-07-16

### Added

- Fourth mined domain `video` (`ditto:video`), alongside work, design, and write. Mining now scouts, reduces, and assembles a `you-video.md` layer that an agent loads before video work, resolved by `python ditto.py plugin profile-path --domain video` (returns the core `you.md` plus `you-video.md`, integrity-checked against the version manifest). A new `skills/video/SKILL.md` launcher follows the exact work/design/write convention. The seed profile at `examples/you-video.md` distills a real BiosRios YouTube build into evidence-backed rules: a single paused GSAP HyperFrames timeline, the dark orange house style, the real live Claude app UI, 2 to 4 word captions that match the voiceover, one centered card per item, character-face cut-ins over emoji, the cloned-voice pipeline with a whisper clarity gate and accent-faithful params, the three-layer audio mix, and the fixed gates (exact install CTA, `@biosrios` handle, tension in frame 1, aspect per platform).

### Changed

- `VALID_DOMAINS` widens to four, so every scout report, per-segment worker report, and assembled profile pack must now state evidence or no-signal for `video` and carry a `video` draft. The `MINING_PROMPT.md` scout, worker, and reducer contracts and the legacy-migration manifest all enumerate the new domain. `video` is register-less (only `write` carries casual, professional, or shared registers). `resolve_profile_paths` now returns the deepen instruction instead of crashing when an older profile predates a domain. This is a contract-level change to the domain set, hence the minor bump.

### Verified

- Full `python -m unittest discover -s tests` passes (180 tests) with the widened domain set, the five-skill Copilot manifest, and the 0.4.0 version pinned across every public surface. `plugin profile-path --domain video` returns the `run ditto and deepen video` instruction until a mine populates an active `you-video.md`; a real end-to-end mine that activates the domain from history is the follow-up.
- The `v0.4.0` bootstrap runtime pins `ditto.py` to SHA-256 `c61e328a5c869646963b09e33aa103efe8a3a02d1f187e6a90d45a249c21b619` and `MINING_PROMPT.md` to SHA-256 `a62a28f02abb5a3ef81937e96e362972b0a617aa4f858eb4dcd12bfd1e99bcd7`.

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
