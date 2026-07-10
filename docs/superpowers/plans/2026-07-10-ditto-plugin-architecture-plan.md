# Ditto Plugin and Bounded Mining Architecture Plan

## Objective

Turn Ditto from a single extractor plus one manually installed `you.md` into one recognizable Ditto plugin that:

- installs with zero model calls;
- exposes focused `mine`, `work`, `design`, and `write` skills under the Ditto namespace;
- keeps private generated profiles outside replaceable plugin caches;
- produces a high-quality first profile without sending the user's complete history through an unbounded agent fan-out;
- reuses prior work so identical reruns make zero model calls and incremental runs process only new or changed stable segments;
- fixes the correctness defects found during the audit before the new packaging is released;
- preserves current direct install targets while native plugin support is proven first in Codex and Claude;
- ships the verified plugin as its own release before benchmark production begins;
- treats the public multi-model benchmark, leaderboard, and proof videos as a separate second release after the exact plugin tag is frozen;
- gives each release its own versioned changelog entry and GitHub Release draft backed by that release's real proof.

The release must improve cost, clarity, and usefulness together. A cheaper but generic profile fails. A rich profile that unexpectedly consumes a large subscription allowance also fails.

## Product Path

The user path is:

1. The user installs Ditto as a plugin through the host's supported plugin flow.
2. A fresh task shows the namespaced Ditto skills. Installation does not scan logs, mine history, or run a benchmark.
3. The user invokes `ditto:mine`.
4. Ditto performs a local preflight and shows:
   - detected sources and valid session count;
   - approximate post-dedupe source tokens;
   - cached and uncached coverage;
   - the bounded default selection size;
   - planned map calls and reducer calls;
   - the separate full-history deep option.
5. The default mine selects stable, deterministic slices across the user's timeline and available sources. It never silently expands to full history.
6. Fast worker agents extract work, design, and writing evidence together from each selected slice.
7. One strong reducer compiles the shared report set into the three private profile files plus receipts and the share card.
8. Ditto validates every generated artifact, stages the complete profile version, and atomically switches the active profile only if the full pack passes validation.
9. Future tasks activate `ditto:work`, `ditto:design`, or `ditto:write` as relevant. The static loader reads the active private profile file.
10. An identical rerun resolves entirely from content-addressed caches. A later update processes only new or changed sealed segments.
11. If one domain lacks adequate evidence, Ditto keeps that domain inactive and gives one exact targeted deepen action. It does not invent rules or automatically spend more tokens.
12. After implementation, automated tests, migration, live plugin activation, and real work/design/writing probes pass, Ditto prepares and ships the plugin release. Benchmark work is not a plugin-release gate.
13. Only after the plugin release is tagged does Ditto freeze the exact released plugin version for the separate benchmark milestone. The schema and runner come first, model runs still require explicit approval, and result-UI polish starts only after the first approved run proves the schema.

### First-run experience

- The README and plugin page lead with one natural instruction: **`run ditto`**.
- The plugin routes that phrase to `ditto:mine`; the user does not need to know skill namespaces, Python paths, chunk counts, or install destinations.
- Ditto installs with zero model calls, then shows one compact preflight when the user starts mining: real sessions, post-dedupe source size, selected starter budget, planned calls, and cache reuse.
- The bounded starter mine proceeds without a configuration wizard. Only a larger targeted or deep run requires approval.
- During local scanning and model work, Ditto reports progress at meaningful boundaries so the user is never left wondering whether it stalled.
- Success returns one result: what Ditto learned, which work/design/write skills activated, where the private profile lives, the real call plan used, the card path, and the proof task result.
- The user never manually copies profile files into agent folders.

### Returning-user experience

- **`update ditto`** checks only new or changed sessions.
- No changes means no model calls and a clear `profile already current` result.
- New evidence reuses sealed reports, stages a new profile version, and switches atomically only after validation.
- If evidence is insufficient, Ditto names the weak domain and gives one exact targeted deepen command. It never silently expands the budget.

### Existing CLI compatibility

The current no-plugin path remains valid for users who prefer one-file Python. `python ditto.py --dry-run`, extraction, card rendering, and direct install targets continue to work. The plugin becomes the recommended path because it removes manual orchestration while preserving the simple current entry point.

For the Plugin release, `ditto.py` remains the canonical zero-dependency, single-file Python runtime. Segment, cache, profile-store, and migration logic stay in that file; the plugin adds static manifests and skill files but does not turn the CLI into an installed Python package. If maintainability later requires modules, Ditto must first preserve a generated standalone `ditto.py` release artifact or explicitly retire the one-file claim in a separate release.

## User Answers Translated

- **What is being built:** one Ditto plugin, patterned after Superpowers' canonical repository plus thin host overlays, containing the mining workflow and task-specific personal skills.
- **Who it serves:** an individual AI-agent user with months of local Codex, Claude, or Copilot session history.
- **Who can see or change the profile:** the local user and the local agent host. Generated profiles remain private by default. Public artifacts require explicit review.
- **Where it runs:** deterministic extraction, redaction, selection, caching, and profile storage run locally. Selected redacted text is processed wherever the user-selected model provider runs. The Python extractor itself makes no network calls.
- **The most important rules:** install must cost zero model calls; default mining must be bounded and visible; quality must remain evidence-backed; no benchmark runs yet; private data must survive plugin upgrades; no production or privacy overclaims.
- **What already exists:** a zero-dependency Python extractor, redaction, dedupe, chunk writing, one-profile installation, card rendering, mining prompts, an optional designer lens, and nine passing tests for the current flow.

## Current Repo Evidence

### Existing strengths

- `ditto.py` auto-detects Codex, Claude, and Copilot log roots and parses user-role messages.
- Redaction happens before extracted text is written.
- Long verbatim duplicates are collapsed, saving substantial input on repeated specifications and injected rules.
- `MINING_PROMPT.md` already separates per-slice extraction from reduction and includes optional thinking and designer lens guidance.
- `skills/ditto/SKILL.md` already defines the agent-orchestrated extract, mine, reduce, install, and card flow.
- The installer supports Codex, Claude, Cursor, `AGENTS.md`, and Gemini destinations.
- The current automated suite passes 9/9.

### Measured cost path

The latest local dry run inspected 1,978 JSONL files, retained 7,681 messages, removed 1,466 duplicate long messages, and still produced approximately 1,951,558 source tokens. The current skill sizes work around roughly 70K tokens per mining agent, which would plan about 28 worker calls plus reduction for this corpus. There is no hard default call or token ceiling.

### Correctness defects that block release

Temporary-directory reproductions on 2026-07-10 confirmed the key audit findings against the current `ditto.py`: a six-chunk output followed by a one-chunk rerun still contained `chunk-01` through `chunk-06`; malformed `notname:`/`notdescription:` frontmatter returned valid; corrupt-only JSONL exited `0` and wrote stats; and a Hebrew destination under `PYTHONIOENCODING=cp1252` raised `UnicodeEncodeError`.

- `write_outputs` creates chunk files without atomically replacing or clearing a previous chunk directory. A smaller rerun can leave stale chunk files that are mined again.
- Corrupt or unsupported-only JSONL input can reach the end with zero valid sessions and still exit successfully with instructions to mine empty output.
- Skill frontmatter validation uses substring checks, so malformed keys such as `notname:` can be accepted.
- Windows console output can raise `UnicodeEncodeError` for Hebrew or other Unicode destination paths under a non-UTF-8 code page.
- The current installer writes directly into the destination with no staged rollback. The new multi-file profile pack would multiply that risk unless activation becomes atomic first.
- Codex and Claude destinations are hardcoded to one `you` skill, so three side-by-side domain skills cannot coexist through the installer.
- Current docs blur source detection, install destination, and native plugin support. Cursor and Gemini are context adapters today, not proven native Ditto plugins.
- Current privacy copy can be read as saying the complete mining workflow is local. In reality, selected redacted text is processed by the chosen model provider unless that provider is local.

## Architecture Boundaries

### In scope

- One canonical Ditto repository.
- Candidate Codex and Claude plugin manifests, retained as native Plugin release surfaces only for hosts that pass Workstream 0.
- Static namespaced skills: `ditto:mine`, `ditto:work`, `ditto:design`, and `ditto:write`.
- Durable private storage under `DITTO_HOME`, defaulting to `~/.ditto`.
- Bounded deterministic starter mining.
- Content-addressed stable segments, worker reports, and reductions.
- One report fan-out shared by all three domain outputs.
- Strong evidence and quality gates.
- Atomic profile activation and migration from the legacy single-profile paths.
- Existing direct Cursor, `AGENTS.md`, Gemini, Codex, and Claude install adapters retained for compatibility.
- Honest documentation and privacy wording.
- Automated and live verification proportional to the risk.
- A separate post-plugin-release benchmark milestone containing the manifest, result schema, fixtures, disabled runner, approved model runs, result UI, and proof clips.

### Explicitly out of scope for both releases

- Persistent filesystem watchers or session hooks.
- Automatic background mining.
- Hosted profile storage, accounts, billing, or telemetry.
- Public leaderboard service or result aggregation.
- Automatic model API orchestration across providers.
- Full workflow-skill compiler beyond the approved work/design/write profile layer.
- Profile drift, contradiction resolution across versions, or a weekly correction ledger.
- Native Cursor or Gemini plugin claims without separate installation and live registration proof.
- Benchmark execution before the rest of the product is complete.

## Options Considered

### Option 1: Keep the existing single skill and only reduce the number of chunks

This is the smallest code change, but it does not solve stale chunks, incremental reuse, plugin packaging, domain activation, atomic installation, or misleading cost expectations. It also provides no durable place for profile data across plugin updates.

**Decision:** rejected.

### Option 2: Generate private skills directly inside the installed plugin directory

This visually keeps everything in one folder, but installed plugin caches are replaceable. Reinstalling or upgrading the plugin can erase private profiles. It also mixes immutable product code with private mutable user data.

**Decision:** rejected.

### Option 3: One canonical plugin with static loader skills and durable private profile storage

The plugin contains stable behavior and thin loaders. The generated profile pack and report cache live under `~/.ditto`, outside any host cache. Codex and Claude overlay candidates come from the same canonical repository, but only Workstream 0 survivors ship as native surfaces. Existing adapters remain available for other hosts.

**Decision:** recommended.

### Option 4: Run the complete history by default but use cheaper worker models

Cheaper workers reduce monetary cost when the host supports model selection, but they do not create a predictable usage ceiling. Some hosts cannot enforce a worker model, and subscription allowances may still be consumed heavily.

**Decision:** rejected as the default; retained as an explicit deep mode with a visible plan.

## Recommended Architecture

### Canonical repository and plugin overlays

```text
ditto/
  .codex-plugin/
    plugin.json
  .claude-plugin/
    plugin.json
    marketplace.json            # development/publishing overlay only
  assets/
  skills/
    mine/
      SKILL.md
    work/
      SKILL.md
    design/
      SKILL.md
    write/
      SKILL.md
  ditto.py
  MINING_PROMPT.md
  README.md
  SECURITY.md
  tests/
```

The plugin name is `ditto`; host namespacing yields `ditto:mine`, `ditto:work`, `ditto:design`, and `ditto:write`. The current `skills/ditto` path receives a compatibility wrapper or migration note so existing users are not silently broken.

### Durable private state

```text
~/.ditto/
  config.json
  active-profile.json
  profiles/
    default/
      versions/
        <profile-version>/
          manifest.json
          you.md
          you-designer.md
          you-writer.md
          appendix.md
          card.json
      current.json
  cache/
    segments/
      <content-hash>.txt
    reports/
      <prompt-schema-version>/
        <segment-hash>.json
    reductions/
      <reducer-schema-version>/
        <report-set-hash>.json
  runs/
    <timestamp>/
      plan.json
      stats.json
      selected-segments.json
```

`DITTO_HOME` can override the default for tests and advanced users. Plugin uninstall never deletes this directory. Profile activation uses a staged version directory and an atomic pointer replacement.

### Bounded mining contract

- Plugin installation: zero scan calls and zero model calls.
- Preflight: deterministic local work only.
- The release default is selected by dogfood calibration, not fixed in advance.
- First calibration candidate: four stable segments capped near 25K source tokens each, four map calls, and one reducer call. On the current 1.95M-token corpus this samples only about 5%, so it is explicitly a recall-risk hypothesis, not a validated constant.
- Additional bounded candidates improve temporal/source coverage with more, smaller segments: six near 20K plus one reducer, then eight near 20K plus one reducer.
- Calibration has an absolute candidate ceiling of 160K selected source tokens and nine planned calls. Changing that ceiling requires a visible plan decision; no candidate silently exceeds it.
- The smallest candidate that passes the predeclared recall and fresh-task quality gates becomes the release default. If none passes, Ditto does not claim the bounded starter is sufficient and the release decision is revisited.
- Workers use a fast role when the host supports model choice. One strong reducer compiles compact structured reports.
- Host/system prompt overhead is disclosed as outside Ditto's exact measurement.
- Identical input plus identical prompt/schema versions: zero model calls through report and reduction cache hits.
- New history: only new or changed stable segments become uncached work.
- Deep mode: explicit request only, separately estimated, resumable, and never started by install, update, setup, or benchmark preparation.

### Stable segmentation

The current equal-N splitter rebalances old chunks when history grows, invalidating caches. Replace it with append-only sealed segments:

1. Sort valid session blocks by source, timestamp, and stable session identity.
2. Exclude known system-generated compaction/continuation wrappers and invalid messages before selection.
3. Build segments on whole-session boundaries until the configured source-token target is reached.
4. Seal a segment and address it by the hash of normalized redacted content plus extraction schema version.
5. Never alter a sealed segment. New sessions create new segments.
6. Default selection is deterministic and stratified across time and available sources. It samples the whole observed period instead of only the newest or longest sessions.

### Shared evidence model

Every worker report extracts all approved categories together:

- working laws, shorthand, definition of done, verification behavior;
- design taste, references, hierarchy, rejection patterns;
- writing voice, slang, format choices, banned patterns;
- receipts with verbatim evidence and source identifiers;
- uncertainty and contradictions.

One strong reducer reads the report set once and produces all three profile files. This prevents three separate full mining passes.

### Quality contract

The starter path is allowed to be smaller, not weaker in judgment.

- Evidence independence is measured by distinct user-authored sessions and time/source strata, not by how many worker reports happened to contain the same session.
- An inferred repeated behavior requires at least two distinct sessions and at least two verbatim quotes in the private appendix. Cross-stratum support increases confidence and is required when the selected corpus contains adequate coverage.
- One direct, unequivocal user instruction may preserve a rare but high-salience law with one receipt only when it is labeled as an explicit instruction rather than a repeated pattern, carries lower frequency confidence, and has no contradictory evidence. It cannot be described as a consensus or habit.
- Generic traits a stranger could guess are rejected.
- The reducer receives the strongest available model role; worker model choice optimizes cost, not final judgment.
- Reports record stable session IDs, time/source strata, occurrence counts, and sampled coverage; they cannot imply the full history was read.
- The manifest records source coverage by tool and time range, selected source tokens, prompt/schema versions, and every cache hash.
- A weak domain is not installed as if complete. It remains inactive and exposes one exact targeted deepen action.
- Generated skills remain lean for runtime context. Deep evidence stays in the appendix and is loaded only for audit or deepening.
- Before calibration, freeze a must-recover checklist from the existing deep Ohad profile covering non-negotiable working laws, design rejection patterns, and voice constraints. Run all bounded candidates against the same checklist and real receipts; choose the smallest passing candidate rather than tuning the gate after seeing results.
- A failed release dogfood blocks the bounded-default claim. Targeted deepening remains a valid post-release response for an individual user's genuinely sparse domain, not a way to waive the flagship calibration gate.
- Fresh-task probes must show correct activation and a human verdict for work, design, and writing. The public multi-model benchmark is a later, larger proof and does not replace these release checks.

### Skill routing contract

The four skill descriptions are part of the product routing layer and require positive and negative trigger tests.

- `ditto:mine` triggers only for explicit Ditto setup, mining, updating, or deepening requests.
- `ditto:design` handles UI, UX, visual judgment, and frontend-design work; it loads the core profile plus the design profile.
- `ditto:write` handles marketing, social, replies, product copy, and writing in the user's voice; it loads the core profile plus the writing profile.
- `ditto:work` handles other execution and verification tasks; its description explicitly excludes design and writing requests and it loads only the core profile.
- A task that genuinely combines design and copy may deliberately load `design` and `write`. The host must not load `work` alongside them merely because all three skills mention the user profile.

## Workstream Map

```text
host plugin viability spike
        ↓
P0 correctness + usage gates
        ↓
stable segmentation + caches
        ↓
shared evidence reduction
        ↓
durable profile store + atomic activation
        ↓
Codex/Claude plugin overlays + loaders
        ↓
migration + honest docs
        ↓
automated and live verification
        ↓
plugin changelog + GitHub Release
        ↓
PLUGIN RELEASE SHIPPED
        ↓
freeze exact released plugin tag
        ↓
benchmark schema + disabled runner
        ↓
approved benchmark runs
        ↓
result UI + proof clips
        ↓
benchmark changelog + GitHub Release
```

## Workstreams

### Workstream 0: Host plugin viability spike

**Purpose:** prove the packaging premise before building storage, caches, and reducers around it.

**User outcome:** native host support is based on a working path, not the presence of plausible manifest files.

**Areas:** minimal Codex and Claude development manifests, one temporary namespaced proof skill, an isolated `DITTO_HOME` fixture, and spike notes/tests.

**Tasks:**

- Register the smallest valid `ditto:spike` skill in Codex and Claude through each host's supported development flow.
- In a fresh task, prove the skill can invoke the repository's local Python runtime and read a harmless fixture through `DITTO_HOME`.
- Record the exact host version, install command, discovered namespace, task transcript, and any shell/filesystem restrictions.
- Use no real user logs, mining prompts, benchmark models, or generated profiles during the spike.
- Remove the temporary public skill after the result is captured; retain only the fixture/test or decision record needed to protect the proven contract.

**Dependencies:** none. It runs before the main architecture work; the existing CLI correctness fixes remain conceptually independent but follow it in the implementation sequence so the packaging decision is known first.

**Acceptance signals:** a fresh Codex task discovers and invokes the namespaced skill, local Python runs, and the isolated fixture is read. Claude must pass the same proof before native Claude support remains in the Plugin release scope.

**Verification:** host validator output plus fresh-task transcripts and fixture output. Manifest existence alone is not proof.

**Risk/fallback:** if Codex cannot support the shape, stop the plugin architecture and retain the CLI/direct-skill product path. If only Claude fails, the Plugin release is native Codex plus the existing Claude adapter; the docs must not claim a native Claude plugin.

### Workstream 1: Correctness and usage safety

**Purpose:** remove defects that can waste quota, accept invalid data, or corrupt installs.

**User outcome:** Ditto stops before costly work when inputs or outputs are invalid and never mines stale files.

**Areas:** `ditto.py`, `tests/test_ditto.py`, `skills/ditto/SKILL.md`.

**Tasks:**

- Replace chunk/output directories through a staged atomic swap.
- Fail nonzero when no valid sessions remain after parsing and filtering.
- Replace substring frontmatter checks with an exact parser and safe fixed skill identifiers.
- Make console output UTF-8-safe on Windows without changing stored UTF-8 bytes.
- Add a preflight plan containing selected source tokens, planned calls, reducer count, and cache reuse.
- Remove the instruction that depth always beats token efficiency and prohibit implicit deep mode.

**Dependencies:** none.

**Acceptance signals:** stale chunks cannot survive rerun; corrupt-only input fails before output; Hebrew paths round-trip; preflight has a hard default ceiling.

**Verification:** run the full unit suite plus targeted Windows subprocess tests under an isolated `DITTO_HOME`.

**Risk/fallback:** if atomic directory replacement behaves differently on Windows, use same-volume staging plus backup/restore and verify failure injection at each boundary.

### Workstream 2: Stable segmentation and content-addressed caching

**Purpose:** make the bounded mine deterministic, resumable, and incremental.

**User outcome:** the first mine is predictable; reruns do not pay again for unchanged history.

**Areas:** `ditto.py`, new cache/manifest helpers, test fixtures.

**Tasks:**

- Normalize valid redacted session blocks.
- Define extraction, segment, report, and reducer schema versions.
- Seal stable segments by whole-session boundaries and hash normalized bytes.
- Implement deterministic stratified default selection across time and sources.
- Cache worker reports by segment hash plus prompt schema version.
- Cache reductions by sorted report-set hash plus reducer schema version.
- Produce run plans and stats without secrets or raw profile content.

**Dependencies:** Workstream 1.

**Acceptance signals:** identical rerun plans zero calls; adding one fixture session leaves old segment hashes unchanged and plans only new work.

**Verification:** golden hash fixtures, repeat-run tests, incremental-add tests, prompt-schema invalidation tests, corrupt-cache fail-closed tests.

**Risk/fallback:** if stratified selection misses a source/time bucket because the history is small, consume the full small corpus while staying under the same hard ceiling.

### Workstream 3: Shared evidence and three-profile compilation

**Purpose:** produce high-quality work, design, and writing skills from one mining pass.

**User outcome:** Ditto becomes materially more useful across execution, UI judgment, and marketing voice without tripling mining cost.

**Areas:** `MINING_PROMPT.md`, skill orchestration, examples, output validation.

**Tasks:**

- Update worker output to one structured evidence report covering all three domains.
- Update the reducer to compile `you.md`, `you-designer.md`, `you-writer.md`, `appendix.md`, and `card.json` in one pass.
- Add the dedicated writer lens.
- Apply the session-based evidence rules, including the narrowly defined explicit-instruction exception.
- Record contradictions and insufficient-evidence status.
- Validate exact frontmatter names and profile manifest references before staging.

**Dependencies:** Workstream 2.

**Acceptance signals:** one report fan-out feeds all profile files; weak domains fail closed; generic filler is absent; all instructions trace to private receipts.

**Verification:** reducer fixture tests, invalid-output tests, missing-receipt tests, controlled Ohad dogfood comparison, human review of the three generated files.

**Risk/fallback:** if one-pass reduction harms quality, retain one shared evidence JSON and run small domain-specific compilers over that JSON only, never over the raw corpus again.

### Workstream 4: Durable profile storage and atomic activation

**Purpose:** separate private mutable profile state from replaceable plugin code.

**User outcome:** plugin updates cannot erase or partially replace the user's personal layer.

**Areas:** new `DITTO_HOME` storage helpers, installer paths, migration code, tests.

**Tasks:**

- Create versioned profile directories outside host caches.
- Stage and validate the complete profile pack.
- Atomically update the active pointer.
- Back up the previous active pointer and restore it on failure.
- Support one safe profile ID initially while using a schema that can support multiple profiles later.
- Preserve legacy direct installers.

**Dependencies:** Workstream 3.

**Acceptance signals:** injected failure after any staged write leaves the prior active version intact; uninstall/reinstall leaves private data unchanged.

**Verification:** failure-injection matrix, read-only directory tests, path traversal tests, reserved Windows name tests, Unicode/Hebrew round-trip tests.

**Risk/fallback:** if atomic pointer replacement is unavailable on a filesystem, use a backup-and-rename sequence on the same volume and fail without deleting the prior version.

### Workstream 5: Plugin packaging and loaders

**Purpose:** deliver one Ditto product through the native host surfaces proven in Workstream 0.

**User outcome:** one plugin install reveals the relevant Ditto skills together, like Superpowers.

**Areas:** `.codex-plugin/plugin.json`, `.claude-plugin/plugin.json`, `skills/mine`, `skills/work`, `skills/design`, `skills/write`, assets, plugin validation.

**Tasks:**

- Scaffold and validate the Codex manifest with real metadata and assets if Codex passed Workstream 0.
- Add the Claude manifest and local development marketplace overlay only if Claude passed Workstream 0.
- Move or wrap the current orchestrator as `mine` without breaking current direct-skill users.
- Create static domain loaders that resolve `DITTO_HOME`, read the active pointer, validate the manifest, and load only the relevant private file.
- Give each skill mutually clear positive and negative trigger descriptions and test overlap cases, including design-plus-copy tasks.
- Ensure missing/corrupt profile state instructs the exact recovery action and never silently uses a stale or partial profile.
- Keep benchmark capability absent or inert until its final workstream.

**Dependencies:** Workstream 0 and Workstream 4.

**Acceptance signals:** every claimed native host shows the four exact namespaced skills in an isolated clean install; fresh tasks load the expected active profile; plugin reinstall preserves private state.

**Verification:** Codex plugin validator, Claude manifest validation, isolated marketplace install, cachebuster reinstall, fresh-task activation transcripts.

**Risk/fallback:** ship Codex first if Claude registration cannot be proven in the same release window. Do not claim native Claude plugin support from manifest existence alone.

### Workstream 6: Migration, documentation, and release truth

**Purpose:** move existing users safely and explain the real privacy/cost boundaries.

**User outcome:** existing profiles are preserved, instructions are clear, and no one is surprised by model-provider processing or usage.

**Areas:** `README.md`, `SECURITY.md`, `ROADMAP.md`, existing install code, examples.

**Tasks:**

- Detect legacy `you` skill destinations and copy into a staged private profile version after backup.
- Keep the legacy skill active while the new private profile and loaders are staged but not yet activated.
- After live verification, move the legacy skill directory out of host discovery into `~/.ditto/legacy/<host>/<timestamp>/`, then atomically activate the new pointer. Never allow a fresh task to see both the legacy personal skill and the new Ditto profile loaders.
- If activation or a fresh-task probe fails, deactivate the new pointer and restore the legacy directory to its original discovery path.
- Treat marked `AGENTS.md`/`GEMINI.md` blocks as separate adapter migrations; a native plugin migration must not silently leave an always-on legacy context block competing with the new loaders.
- Distinguish source auto-detection, install adapters, and native plugin support.
- State that `ditto.py` makes no network calls while selected redacted mining text is processed by the chosen provider.
- Document the zero-call plugin install, bounded default mine, exact preflight fields, explicit deep mode, and incremental reuse.
- Explain sampled receipts without implying complete-history consensus.

**Dependencies:** Workstreams 1-5.

**Acceptance signals:** a current user can migrate without losing the existing profile; a fresh task sees exactly one active personal-profile path; docs match live behavior and tests.

**Verification:** migration tests from all supported legacy destinations, documentation command smoke tests, manual claim audit against code and live plugin state.

**Risk/fallback:** if automatic migration detects ambiguous or conflicting installs, stop and show exact paths rather than choosing silently.

### Workstream 7: Plugin release verification

**Purpose:** prove the plugin upgrade independently of any benchmark or launch-video production.

**User outcome:** Ditto is demonstrably installed, efficient, and behaviorally useful early enough to ship while launch momentum is still active.

**Areas:** tests, isolated homes, plugin development marketplace, migration fixtures, live activation evidence, and claim review.

**Tasks:**

- Run all automated correctness, cache, atomicity, and migration tests.
- Validate clean installs in fresh tasks for every host still claimed as native after Workstream 0.
- Run one real `done` probe, one design probe, and one writing probe with human verdicts.
- Record source-token and call-plan evidence for bounded mining without claiming subscription-percentage savings.
- Complete separate read-only spec-compliance and code-quality reviews, fix actionable findings, and re-review.
- Keep all benchmark runners absent or disabled; benchmark preparation is not required for plugin-release approval.

**Dependencies:** Workstreams 0-6.

**Acceptance signals:** every plugin-release gate is backed by output, hashes, screenshots/transcripts, and human verdicts; no benchmark model has run and no benchmark artifact is required.

**Verification:** complete the plugin release checklist against the exact candidate commit and repeat the clean-install/fresh-task probes from that commit.

**Risk/fallback:** if the chosen bounded candidate fails a real release probe, reopen calibration or block the plugin release; do not use targeted deepening to disguise a failed flagship default. For later users with sparse evidence in one domain, show a separate targeted deepen plan.

### Workstream 8: Plugin release handoff

**Purpose:** ship the verified plugin as the first independent distribution moment.

**User outcome:** users receive the plugin, bounded mining, and work/design/write skills without waiting for 28 qualifier cells, repeated finals, leaderboard production, or videos.

**Areas:** `CHANGELOG.md`, `README.md`, Git tag, GitHub Release, upgrade instructions, and plugin-release proof.

**Tasks:**

- Add the plugin release's own versioned changelog entry: what changed, why it matters, how to upgrade, verified proof, and known limits.
- Assign the next valid repository version at ship time from the existing tag history; `Plugin release` is a milestone name, not a hardcoded `v1` tag.
- Draft a GitHub Release from the exact verified plugin commit and changelog entry.
- State that the benchmark is a later release; include no placeholder scores, speculative winner, or promised date.
- Add the README notification path `Watch` → `Custom` → `Releases` without claiming that stars notify stargazers.
- Obtain final ship approval before publishing the tag or GitHub Release.

**Dependencies:** Workstreams 0-7 only. Nothing in Workstreams 9-10 may block this release.

**Acceptance signals:** after explicit ship approval, the plugin tag resolves to the verified commit, install/upgrade commands work from that tag, and the GitHub Release contains no benchmark dependency or unverified claim.

**Verification:** preview the release, resolve tag-to-commit, smoke-test every command and link, perform a final claim audit, and repeat one clean install from the tagged artifact.

**Risk/fallback:** if release evidence is incomplete, delay only the plugin release handoff. Do not pull benchmark scope forward as a substitute for missing product proof.

### Workstream 9: Benchmark preparation, approved execution, and visual proof

**Purpose:** create the separate benchmark distribution event on top of an already released Ditto plugin.

**User outcome:** people can see whether Ditto improves behavior and how the current Codex/Claude systems compare, with every result traceable to raw evidence and an installable released product behind it.

**Areas:** benchmark manifest/schema, disabled runner, raw artifacts, blind verdicts, result UI, leaderboard, and three cold-versus-Ditto proof clips plus one combined hero clip.

**Tasks:**

- Freeze the exact already-published plugin tag used by every `+Ditto` condition. Never benchmark a dirty worktree or unreleased plugin commit.
- If user feedback requires a product fix, verify and publish the patch first, then freeze that new tag before starting or restart affected cells so one result set never mixes plugin versions.
- Freeze the supplied 14-label roster: Codex `5.5`, `5.6 Sol`, `5.6 Terra`, `5.6 Luna`, `5.4`, `5.4 Mini`, `5.3 Codex Spark`; Claude `Fable 5`, `Opus 4.8`, `Sonnet 5`, `Haiku 4.5`, `Opus 4.7`, `Opus 4.6`, `Sonnet 4.6`.
- Build the thin manifest, result schema, deterministic fixtures, and disabled runner before any real model run.
- Obtain explicit approval before the first model invocation.
- Run one approved pilot cell, validate the schema against real host/model/mode/tool/budget output, and revise it before bulk execution if needed.
- Run the same cold and `+Ditto` qualifier conditions for all 14 entries and retain every raw prompt, output, environment field, timing, and verdict.
- Advance the top four qualifier systems into the repeated full benchmark defined by the frozen manifest; do not change tasks or scoring after seeing results.
- Build the polished leaderboard only from validated artifacts.
- Produce separate `done`, design, and writing proof clips plus one combined hero clip from real cold-versus-Ditto outputs. Never reconstruct or improve a weak result for the video.

**Dependencies:** the published plugin release from Workstream 8; model execution additionally requires explicit user approval.

**Acceptance signals:** all 14 entries have comparable qualifier artifacts from one frozen plugin tag; top-four advancement is reproducible; repeated results link to raw evidence; UI and videos contain no placeholder or hand-entered claims.

**Verification:** tag proof, schema validation on the pilot, runner logs, artifact hashes, blind-verdict records, leaderboard-to-artifact link audit, and frame-by-frame claim audit of the proof clips.

**Risk/fallback:** if a menu label or host changes, stop that system's run, record the drift, and ask before substituting it. If the frozen plugin tag changes, restart affected comparison cells rather than combining incomparable versions.

### Workstream 10: Benchmark release handoff

**Purpose:** ship the verified benchmark and visual proof as the second independent distribution moment.

**User outcome:** the leaderboard and hero story land as a focused release rather than being buried inside plugin packaging notes.

**Areas:** second `CHANGELOG.md` entry, benchmark artifacts, README/result links, Git tag, GitHub Release, leaderboard, and proof videos.

**Tasks:**

- Add a separate benchmark-release changelog entry using only verified results and links to raw artifacts.
- Assign the next valid repository version at ship time; `Benchmark release` is a milestone name, not a hardcoded `v2` tag.
- Draft a second GitHub Release from the matching changelog entry and exact benchmark commit.
- Verify that the release names the frozen plugin tag used in every `+Ditto` run and clearly describes cross-host results as system comparisons.
- Obtain final ship approval before publishing the benchmark tag, Release, leaderboard, or videos.

**Dependencies:** completed and verified Workstream 9 artifacts.

**Acceptance signals:** after explicit ship approval, the benchmark tag, second changelog entry, GitHub Release, leaderboard, proof clips, frozen plugin tag, and raw artifacts all agree.

**Verification:** preview the second release, resolve both relevant tags, test every link, trace every displayed number to a raw artifact, and perform a final frame-by-frame claim audit.

**Risk/fallback:** GitHub stars do not notify stargazers. Treat this as a second release and distribution moment, but direct users to `Watch` → `Custom` → `Releases` for reliable notifications.

## Execution Tasks

- [ ] Create a git checkpoint before product changes.
- [ ] Run the minimal Codex/Claude plugin viability spike and record the per-host decision before building plugin-dependent architecture.
- [ ] Add failing tests for stale chunks, zero-session success, malformed frontmatter, Hebrew paths, and partial install rollback.
- [ ] Fix P0 correctness defects one at a time and keep the existing suite green.
- [ ] Add a deterministic preflight/run-plan model with no model calls.
- [ ] Add stable sealed segment generation and schema-versioned hashes.
- [ ] Add deterministic stratified starter selection with configurable bounded calibration candidates and a 160K/nine-call calibration ceiling.
- [ ] Add report and reduction cache lookups and fail-closed validation.
- [ ] Update mining prompts to one shared evidence report per segment.
- [ ] Add one-pass profile compilation for work, design, writing, appendix, and card.
- [ ] Add output validation and insufficient-evidence behavior.
- [ ] Add versioned `DITTO_HOME` profile storage and atomic active pointer.
- [ ] Add staged legacy migration with backup, discovery-path deactivation, single-active-profile proof, and rollback restoration.
- [ ] Scaffold and validate the Codex plugin manifest if Codex passed the spike.
- [ ] Add and validate the Claude plugin overlay if Claude passed the spike.
- [ ] Add static `mine`, `work`, `design`, and `write` skills.
- [ ] Add isolated clean-install and cachebuster-reinstall tests.
- [ ] Correct README and security claims.
- [ ] Run bounded mining dogfood and compare against the existing deep profile.
- [ ] Run fresh-task work, design, and writing activation probes.
- [ ] Complete separate spec-compliance and code-quality reviews.
- [ ] Fix all actionable findings and rerun verification.
- [ ] Create the plugin-release changelog entry, README notification instructions, and GitHub Release draft from the verified plugin commit.
- [ ] Ask for plugin ship approval, then publish the plugin tag and Release before benchmark production begins.
- [ ] Freeze the exact published plugin tag used by every `+Ditto` benchmark cell.
- [ ] Prepare a thin benchmark manifest, result schema, fixtures, and disabled runner without running models.
- [ ] Ask for explicit approval before any benchmark model run.
- [ ] Validate the schema against one approved pilot cell, then run cold and `+Ditto` qualifiers for all 14 frozen menu entries.
- [ ] Advance the top four into the repeated full benchmark and retain raw artifacts and blind verdicts.
- [ ] Build the evidence-linked result UI, leaderboard, three domain proof clips, and combined hero clip.
- [ ] Create a separate benchmark-release changelog entry and GitHub Release draft from verified artifacts.
- [ ] Ask for benchmark ship approval before publishing its tag, Release, leaderboard, or videos.

## Implementation Sequence

1. Checkpoint, then run the minimal Codex/Claude host-plugin viability spike.
2. Add failing tests for current correctness defects.
3. Fix P0 correctness defects.
4. Add the preflight plan and stable segmentation.
5. Add cache and incremental behavior.
6. Add shared evidence extraction, session-based receipts, and three-profile compilation.
7. Add the durable versioned profile store and atomic activation.
8. Build the proven Codex plugin path, then only the host overlays that passed Workstream 0.
9. Add staged legacy cutover, rollback, skill-routing tests, and honest documentation.
10. Run bounded-candidate dogfood and select the smallest passing release default.
11. Run automated verification, failure injection, and real fresh-task quality probes.
12. Complete separate reviews, fixes, and re-review.
13. Create and verify the plugin changelog entry, tag candidate, upgrade instructions, and GitHub Release draft.
14. Obtain plugin ship approval and publish the plugin release.
15. Freeze the exact published plugin tag, then prepare the benchmark manifest, schema, fixtures, and disabled runner.
16. After explicit benchmark approval, run one pilot cell and validate the result schema.
17. Complete the frozen 14-entry qualifier and top-four repeated stage.
18. Build the benchmark UI, leaderboard, and proof clips from verified artifacts.
19. Create and verify the separate benchmark changelog entry, tag candidate, and GitHub Release draft.
20. Obtain benchmark ship approval before publishing its release and visual assets.

## Data, Auth, Provider, And Deploy Boundaries

- **Data:** raw logs remain at their original local paths. Redacted selected segments, caches, reports, and profiles live under `DITTO_HOME`. Public artifacts never include the full profile or private receipts by default.
- **Auth:** no new authentication system.
- **Providers:** `ditto.py` makes no network calls. Agent mining uses the user's chosen model host. Ditto cannot guarantee where that provider processes data, so the preflight and docs must say exactly what selected text will be sent.
- **Secrets:** redaction remains mandatory before selected text is written or handed to an agent. Deep mode does not disable redaction.
- **Deploy:** no web deployment or provider dashboard action. Codex and Claude plugin installation are local/marketplace packaging operations that require live host verification.
- **Benchmark:** no model provider calls until the final explicit benchmark stage.

## Test Matrix

| Area | Happy path | Failure/edge path | Required evidence |
|---|---|---|---|
| Extraction | Valid Codex/Claude/Copilot sessions | Corrupt JSONL, unsupported-only logs, zero valid sessions | Exit code, counts, no output on failure |
| Redaction | Known secret patterns removed | Unicode text around secrets, malformed tokens | Byte-level fixture comparison |
| Segmentation | Calibrated bounded candidate | Small corpus, huge session, added session, deleted file | Stable hashes and plan below selected ceiling |
| Chunk replacement | Rerun replaces prior set | Previous 5 chunks then new 1 chunk | Directory listing contains only new set |
| Cache | Identical rerun hits all caches | Changed prompt schema, corrupt report, changed segment | Planned call count and invalidation reason |
| Reduction | Valid three-profile pack | Missing receipt, invalid frontmatter, contradiction, weak domain | Validation report and no activation on failure |
| Atomic activation | Full pack activates | Failure after each staged write, read-only target | Prior active hash preserved |
| Windows/Unicode | Spaces, CRLF, Hebrew paths | Long paths, reserved names, case collisions | Exact UTF-8 round trip and safe failure |
| Plugin viability | Namespaced spike invokes local Python and reads `DITTO_HOME` fixture | Host rejects manifest, namespace, shell, or file access | Per-host validator output and fresh-task transcript |
| Plugin install | Proven host manifests register | Invalid manifest, stale cache, reinstall | Exact version and skill list in fresh task |
| Migration | Legacy `you` is backed up then removed from discovery at cutover | Multiple legacy files, activation failure, double-load attempt | Exactly one active path; restoration transcript |
| Runtime activation | Correct domain skill loads | Missing/corrupt active pointer, overlapping trigger | Transcript shows exact loader/recovery and trigger matrix result |
| Usage budget | Selected default stays under the calibrated ceiling | No candidate passes, deep requested, host lacks model selection | Visible plan; no implicit expansion; failed calibration blocks claim |
| Regression | Existing card and direct installs work | Existing user updates plugin | Full suite plus legacy command smoke tests |
| Benchmark | All 14 qualifiers and top-four repeats follow the frozen manifest | Accidental invocation, schema gap, menu drift, missing artifact | Zero pre-approval calls; raw hashes and blind verdicts before UI/video claims |
| Plugin release | Plugin entry, tag, and Release agree without benchmark data | Benchmark blocks plugin, stale command, unverified claim | Tagged clean-install proof and link/command smoke tests |
| Benchmark release | Second entry, tag, UI, videos, and raw artifacts agree | Mixed plugin tags, missing proof, unverified metric | Frozen-plugin-tag proof and artifact-to-claim audit |

Unauthorized-access, archived-data, and external-provider-failure cases are not applicable because this plan adds no shared accounts, remote database, or hosted provider. Equivalent fail-closed coverage is provided for invalid local paths, corrupt caches, missing profiles, and model-host capability limits.

## Verification Plan

### Automated

- Run `python -m unittest discover -s tests -v` after every focused change and at the end.
- Run Codex plugin validation from the plugin-creator tooling.
- Add a fake runner that records planned and actual calls without invoking a model.
- Prove identical rerun equals zero calls and incremental addition equals only uncached segment calls.
- Run failure injection after each atomic staging step.
- Run subprocess tests with an isolated Windows home and UTF-8/Hebrew paths.

### Manual/live

- Complete the bounded Workstream 0 spike first and record whether each host supports the required namespace, local Python invocation, and `DITTO_HOME` read.
- Install the plugin into a development marketplace.
- Confirm the exact enabled plugin version and the four namespaced skills.
- Start a fresh Codex task after reinstall and verify `ditto:work`, `ditto:design`, and `ditto:write` load the active private profile.
- Repeat in Claude before claiming native Claude plugin support.
- Perform one real task in each domain and collect the artifact plus the user's verdict.
- Inspect every calibration candidate on the current 1.95M-token corpus, freeze the must-recover checklist before model work, and select the smallest candidate that passes it and the three fresh-task probes.
- Verify plugin update and uninstall do not modify `~/.ditto`.
- Preview the plugin changelog and GitHub Release, then repeat a clean install from the exact plugin tag before publication.
- Confirm the benchmark runner remains absent or disabled and no benchmark artifact is required for the plugin release.
- After the plugin is published, freeze its exact tag before benchmark preparation or model approval.
- After approved model runs, preview the separate benchmark changelog and GitHub Release and verify every result link.
- Confirm the README accurately directs users to `Watch` → `Custom` → `Releases` without claiming stars trigger notifications.

## Rollout And Rollback

### Plugin release rollout

1. Prove the minimum native plugin path per host; remove any host that fails from native plugin-release claims.
2. Ship correctness and usage fixes behind the existing CLI without changing the default installed profile.
3. Add durable profile storage, loaders, routing, and migration tests.
4. Install the new plugin in a personal development marketplace with its personal loaders inactive.
5. Import a backed-up copy of the existing Ohad profile and verify all new loaders against the staged profile.
6. Move the legacy skill out of host discovery into `~/.ditto/legacy/...`, then activate the new pointer as one cutover operation.
7. Start a fresh task and prove exactly one personal-profile path is active. On failure, deactivate the new pointer and restore the legacy discovery path.
8. Keep the legacy backup for one release, but never keep it discoverable while the new profile is active.
9. Publish updated docs only after behavior matches them.
10. Prepare the plugin changelog entry and GitHub Release from the verified commit without waiting for benchmark work.
11. After explicit plugin ship approval, publish the plugin tag and Release.

### Benchmark release rollout

1. Start only from an exact published plugin tag.
2. Apply user-feedback fixes only through separately verified and published plugin patch releases; freeze the final chosen tag before comparisons.
3. Prepare the manifest, schema, fixtures, and disabled runner.
4. Obtain explicit model-run approval, validate one pilot cell, then complete the frozen qualifier and top-four repeated stages.
5. Build the leaderboard and proof clips only from verified artifacts.
6. Prepare a separate benchmark changelog entry and GitHub Release draft.
7. After explicit benchmark ship approval, publish its tag, Release, leaderboard, and videos.

### Rollback

- Disable or uninstall the plugin without deleting `~/.ditto`.
- Restore the previous active profile pointer from its backup.
- Move the backed-up legacy `you` skill from `~/.ditto/legacy/...` back to its original host discovery path before the next fresh task.
- Revert or supersede the plugin release with a verified patch if live behavior regresses.
- A benchmark failure never requires rolling back the already working plugin release; stop the benchmark milestone, preserve its raw artifacts, and correct or rerun it under one frozen plugin tag.

## Risks And Fallbacks

- **Starter sample misses an important trait during release calibration:** try the next predeclared bounded candidate. If no candidate under the ceiling passes, block the bounded-default claim and revisit the release decision.
- **A later user's domain is genuinely sparse:** keep that domain inactive and offer a separately planned targeted deepen. Never invent or silently full-mine.
- **Worker model quality is inadequate:** keep the same bounded source selection and rerun only failed report hashes with a stronger worker after showing the revised plan.
- **One-pass reducer produces weaker domain files:** compile domain files from the cached shared evidence model, not from raw history again.
- **Cache corruption:** fail closed, quarantine the corrupt entry, and recompute only that entry.
- **Plugin cache replaces generated data:** prevented architecturally by storing profiles under `DITTO_HOME`.
- **Cross-host behavior differs:** claim support per host only after live proof. Keep direct adapters for unproven hosts.
- **Usage estimate differs from subscription allowance:** report source tokens and planned calls only. Do not promise a percentage of a proprietary quota.
- **Legacy migration ambiguity:** preserve every legacy file and require explicit selection rather than overwriting.
- **Legacy and plugin profiles both trigger:** make discoverability mutually exclusive at cutover and verify in a fresh task; a backup is not left in an active skill directory.
- **Benchmark production grows or slips:** the plugin release is already shipped and remains independent; cut benchmark scope only through an explicit plan revision, never by weakening evidence.
- **User feedback changes Ditto before benchmarking:** ship a verified patch first and restart affected comparison cells under the newly frozen tag; never mix plugin versions in one leaderboard.
- **Scope expands into a living-memory platform:** reject watchers, hosted sync, drift systems, and broad workflow compilation until the focused plugin and benchmark prove demand.

## Open Questions

No blocking product questions remain for the implementation plan. The following release decisions are deliberately fixed:

- The plugin release targets Codex and Claude only if each passes the front-loaded viability spike; Cursor and Gemini remain adapters until separately proven.
- Four segments near 25K are the first calibration candidate, not a fixed release default. The smallest candidate that passes under the 160K/nine-call ceiling becomes the default.
- Full-history deep mode is explicit only.
- Generated profile state lives outside plugin caches.
- The core CLI remains a zero-dependency, single-file `ditto.py` runtime for the plugin release.
- The plugin release ships after Workstreams 0-8 and has no benchmark dependency.
- The benchmark is a separate release based on one exact already-published plugin tag; real runs require approval, and result UI follows the first schema-valid run.
- Version numbers are assigned from repository tag state at each ship gate; `Plugin release` and `Benchmark release` are milestone names, not hardcoded `v1`/`v2` tags.

The exact public marketplace destination is a later distribution decision and does not affect the local plugin architecture or implementation tests.

## Decision Log

- Chose one canonical Ditto repository with thin host overlays, following the useful part of the Superpowers pattern.
- Chose static plugin loaders plus durable external private profile state.
- Chose bounded starter mining over full-history default mining.
- Chose dogfood calibration under a hard ceiling over treating 4×25K as an already validated constant.
- Chose session-based corroboration over worker-report counts, with a narrow labeled exception for direct high-salience instructions.
- Chose stable content-addressed segments over equal-N rebalanced chunks.
- Chose one shared evidence fan-out and one reducer for all three profiles.
- Chose evidence failure over generic profile completion.
- Chose exact source-token/call disclosure over subscription-percentage claims.
- Chose a front-loaded Codex/Claude viability spike before plugin-dependent implementation and per-host claims.
- Chose mutually exclusive legacy/new profile activation over a one-release double-load window.
- Chose to preserve `ditto.py` as the canonical zero-dependency single-file runtime for the Plugin release.
- Chose to defer every benchmark model run until all product and verification work is complete.
- Chose two independent releases so benchmark and video production cannot delay the plugin, creating two honest distribution moments.
- Chose to benchmark one exact published plugin tag and reject mixed-tag or unreleased comparisons.
- Chose `CHANGELOG.md` plus GitHub Releases for updates and rejected the false claim that stars notify every stargazer.

## Next Skill

Next skill: `superpowers:writing-plans` for Workstreams 0-8, the Plugin release only.

Workstreams 9-10 receive their own implementation plan after the Plugin release ships and its benchmark tag is chosen. This keeps benchmark production from expanding or delaying the first implementation plan and allows real user feedback and current model-menu state to inform the second plan without changing the frozen evidence rules.
