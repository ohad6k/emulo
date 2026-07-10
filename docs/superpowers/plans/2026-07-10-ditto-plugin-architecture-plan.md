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
- prepares, but does not execute, the public multi-model benchmark until every preceding product and verification gate passes.
- ends with a versioned changelog entry and GitHub Release draft backed by the real shipped proof.

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
12. After implementation, automated tests, migration, live plugin activation, and real work/design/writing probes pass, the benchmark harness can be completed. Model runs remain the final stage.

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

- `write_outputs` creates chunk files without atomically replacing or clearing a previous chunk directory. A smaller rerun can leave stale chunk files that are mined again.
- Corrupt or unsupported-only JSONL input can reach the end with zero valid sessions and still exit successfully with instructions to mine empty output.
- Skill frontmatter validation uses substring checks, so malformed keys such as `notname:` can be accepted.
- Windows console output can raise `UnicodeEncodeError` for Hebrew or other Unicode destination paths under a non-UTF-8 code page.
- Multi-file profile installation is not atomic and has no rollback.
- Codex and Claude destinations are hardcoded to one `you` skill, so three side-by-side domain skills cannot coexist through the installer.
- Current docs blur source detection, install destination, and native plugin support. Cursor and Gemini are context adapters today, not proven native Ditto plugins.
- Current privacy copy can be read as saying the complete mining workflow is local. In reality, selected redacted text is processed by the chosen model provider unless that provider is local.

## Architecture Boundaries

### In scope

- One canonical Ditto repository.
- Native Codex and Claude plugin manifests.
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
- Benchmark schema and an inert empty-results UI only after the plugin is stable; actual model runs last.

### Explicitly out of scope for this release

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

The plugin contains stable behavior and thin loaders. The generated profile pack and report cache live under `~/.ditto`, outside any host cache. Codex and Claude receive native overlays from the same canonical repository. Existing adapters remain available for other hosts.

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
- Default starter mine: four stable segments capped near 25K source tokens each.
- Worker plan: four map calls, using a fast worker role when the host supports model choice.
- Reducer plan: one strong reducer call over compact structured reports.
- Default total: five planned model calls. Host/system prompt overhead is disclosed as outside Ditto's exact measurement.
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

- Every installed instruction must be supported by at least two independent selected reports and at least two verbatim quotes in the private appendix.
- Generic traits a stranger could guess are rejected.
- The reducer receives the strongest available model role; worker model choice optimizes cost, not final judgment.
- Reports must disclose sampled coverage as `x/4 sampled reports`; they cannot imply the full history was read.
- The manifest records source coverage by tool and time range, selected source tokens, prompt/schema versions, and every cache hash.
- A weak domain is not installed as if complete. It remains inactive and exposes one exact targeted deepen action.
- Generated skills remain lean for runtime context. Deep evidence stays in the appendix and is loaded only for audit or deepening.
- Before release, the bounded mine is dogfooded against the existing deep Ohad profile. It must recover the non-negotiable working laws, design rejection patterns, and voice constraints with real receipts.
- Fresh-task probes must show correct activation and a human verdict for work, design, and writing. The public multi-model benchmark is a later, larger proof and does not replace these release checks.

## Workstream Map

```text
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
benchmark harness preparation
        ↓
benchmark model runs last
```

## Workstreams

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
- Require minimum independent support and two verbatim quotes for installed instructions.
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

**Purpose:** deliver one Ditto product with native Codex and Claude plugin surfaces.

**User outcome:** one plugin install reveals the relevant Ditto skills together, like Superpowers.

**Areas:** `.codex-plugin/plugin.json`, `.claude-plugin/plugin.json`, `skills/mine`, `skills/work`, `skills/design`, `skills/write`, assets, plugin validation.

**Tasks:**

- Scaffold and validate the Codex manifest with real metadata and assets.
- Add the Claude manifest and local development marketplace overlay.
- Move or wrap the current orchestrator as `mine` without breaking current direct-skill users.
- Create static domain loaders that resolve `DITTO_HOME`, read the active pointer, validate the manifest, and load only the relevant private file.
- Ensure missing/corrupt profile state instructs the exact recovery action and never silently uses a stale or partial profile.
- Keep benchmark capability absent or inert until its final workstream.

**Dependencies:** Workstream 4.

**Acceptance signals:** isolated clean installs show the four exact namespaced skills; fresh tasks load the expected active profile; plugin reinstall preserves private state.

**Verification:** Codex plugin validator, Claude manifest validation, isolated marketplace install, cachebuster reinstall, fresh-task activation transcripts.

**Risk/fallback:** ship Codex first if Claude registration cannot be proven in the same release window. Do not claim native Claude plugin support from manifest existence alone.

### Workstream 6: Migration, documentation, and release truth

**Purpose:** move existing users safely and explain the real privacy/cost boundaries.

**User outcome:** existing profiles are preserved, instructions are clear, and no one is surprised by model-provider processing or usage.

**Areas:** `README.md`, `SECURITY.md`, `ROADMAP.md`, existing install code, examples.

**Tasks:**

- Detect legacy `you` skill destinations and copy into a staged private profile version after backup.
- Leave the legacy file intact until the new plugin is live-verified.
- Distinguish source auto-detection, install adapters, and native plugin support.
- State that `ditto.py` makes no network calls while selected redacted mining text is processed by the chosen provider.
- Document the zero-call plugin install, bounded default mine, exact preflight fields, explicit deep mode, and incremental reuse.
- Explain sampled receipts without implying complete-history consensus.

**Dependencies:** Workstreams 1-5.

**Acceptance signals:** a current user can migrate without losing the existing profile; docs match live behavior and tests.

**Verification:** migration tests from all supported legacy destinations, documentation command smoke tests, manual claim audit against code and live plugin state.

**Risk/fallback:** if automatic migration detects ambiguous or conflicting installs, stop and show exact paths rather than choosing silently.

### Workstream 7: Verification and benchmark preparation

**Purpose:** prove the upgrade before public benchmark execution.

**User outcome:** Ditto is demonstrably installed, efficient, and behaviorally useful before model-comparison content is produced.

**Areas:** tests, isolated homes, plugin development marketplace, benchmark manifest/schema, empty-results UI.

**Tasks:**

- Run all automated correctness, cache, atomicity, and migration tests.
- Validate clean Codex and Claude plugin installs in fresh tasks.
- Run one real `done` probe, one design probe, and one writing probe with human verdicts.
- Record source-token and call-plan evidence for bounded mining without claiming subscription-percentage savings.
- Define the 14-entry initial benchmark roster from the supplied model menus.
- Build the benchmark manifest and UI with every result as `--`.
- Keep every model runner disabled until an explicit final-stage approval.

**Dependencies:** all prior workstreams.

**Acceptance signals:** every release gate is backed by output, hashes, screenshots/transcripts, and human verdicts; no benchmark model has run.

**Verification:** complete release checklist and separate read-only spec/code-quality reviews followed by fixes and re-review.

**Risk/fallback:** if the bounded profile fails a real probe, deepen only the failing domain after showing the additional plan. Do not silently fall back to full history.

### Workstream 8: Changelog and GitHub release handoff

**Purpose:** make every shipped Ditto update visible, understandable, and easy to follow from GitHub.

**User outcome:** users can see exactly what changed, why it matters, how to upgrade, and what was actually verified.

**Areas:** new `CHANGELOG.md`, `README.md`, Git tags, GitHub Releases, release notes.

**Tasks:**

- Add a chronological `CHANGELOG.md` with one versioned entry per user-visible release.
- Use the same compact structure for every entry: changed, why, upgrade path, proof, and known limits.
- After the benchmark is explicitly approved and verified, include only real model results and link to raw benchmark artifacts.
- Draft a GitHub Release from the matching changelog entry and exact release tag.
- Add a README note explaining that starring bookmarks the repository but does not subscribe to release notifications. Give the exact GitHub path: `Watch` → `Custom` → `Releases`, backed by GitHub's official notification and release documentation.
- Keep release publication as the final ship gate. Prepare the draft and evidence; Ohad publishes it or explicitly authorizes publication.

**Dependencies:** all product, live verification, and approved benchmark work.

**Acceptance signals:** changelog, tag, release draft, upgrade instructions, proof links, and known limitations all describe the same verified release; no benchmark number is copied without a raw artifact.

**Verification:** preview the GitHub Release draft, confirm its tag resolves to the verified commit, test every command and link, and perform a final claim audit.

**Risk/fallback:** GitHub stars do not notify stargazers. Never promise delivery to all starred users; use GitHub Releases and teach users to watch Releases instead.

## Execution Tasks

- [ ] Create a git checkpoint before product changes.
- [ ] Add failing tests for stale chunks, zero-session success, malformed frontmatter, Hebrew paths, and partial install rollback.
- [ ] Fix P0 correctness defects one at a time and keep the existing suite green.
- [ ] Add a deterministic preflight/run-plan model with no model calls.
- [ ] Add stable sealed segment generation and schema-versioned hashes.
- [ ] Add deterministic stratified starter selection with a four-segment hard default.
- [ ] Add report and reduction cache lookups and fail-closed validation.
- [ ] Update mining prompts to one shared evidence report per segment.
- [ ] Add one-pass profile compilation for work, design, writing, appendix, and card.
- [ ] Add output validation and insufficient-evidence behavior.
- [ ] Add versioned `DITTO_HOME` profile storage and atomic active pointer.
- [ ] Add migration from legacy profile destinations without deletion.
- [ ] Scaffold and validate the Codex plugin manifest.
- [ ] Add and validate the Claude plugin overlay.
- [ ] Add static `mine`, `work`, `design`, and `write` skills.
- [ ] Add isolated clean-install and cachebuster-reinstall tests.
- [ ] Correct README and security claims.
- [ ] Run bounded mining dogfood and compare against the existing deep profile.
- [ ] Run fresh-task work, design, and writing activation probes.
- [ ] Complete separate spec-compliance and code-quality reviews.
- [ ] Fix all actionable findings and rerun verification.
- [ ] Prepare benchmark manifest and empty-results UI without running models.
- [ ] Ask for explicit approval before any benchmark model run.
- [ ] Create `CHANGELOG.md` and add the release-notification instructions to the README.
- [ ] After approved benchmark runs, draft the matching changelog entry and GitHub Release from verified evidence.
- [ ] Ask for final ship approval before publishing the GitHub Release.

## Implementation Sequence

1. Checkpoint and failing tests for current correctness defects.
2. P0 correctness fixes.
3. Preflight plan and stable segmentation.
4. Cache and incremental behavior.
5. Shared evidence prompt and three-profile compilation.
6. Durable versioned profile store and atomic activation.
7. Codex plugin packaging, then Claude overlay.
8. Legacy migration and honest documentation.
9. Automated verification and failure injection.
10. Real fresh-task activation and quality probes.
11. Separate reviews, fixes, and re-review.
12. Benchmark harness and empty-results UI.
13. Benchmark model runs only after explicit approval.
14. Verified changelog entry and matching GitHub Release draft.
15. Final ship approval and GitHub Release publication.

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
| Segmentation | Four stable selected segments | Small corpus, huge session, added session, deleted file | Stable hashes and bounded plan |
| Chunk replacement | Rerun replaces prior set | Previous 5 chunks then new 1 chunk | Directory listing contains only new set |
| Cache | Identical rerun hits all caches | Changed prompt schema, corrupt report, changed segment | Planned call count and invalidation reason |
| Reduction | Valid three-profile pack | Missing receipt, invalid frontmatter, contradiction, weak domain | Validation report and no activation on failure |
| Atomic activation | Full pack activates | Failure after each staged write, read-only target | Prior active hash preserved |
| Windows/Unicode | Spaces, CRLF, Hebrew paths | Long paths, reserved names, case collisions | Exact UTF-8 round trip and safe failure |
| Plugin install | Codex/Claude manifests register | Invalid manifest, stale cache, reinstall | Exact version and skill list in fresh task |
| Migration | Legacy `you` copied safely | Multiple conflicting legacy files | Backup, no deletion, explicit stop |
| Runtime activation | Correct domain skill loads | Missing/corrupt active pointer | Transcript shows exact loader or recovery |
| Usage budget | Default plans four maps and one reducer | Deep requested, host lacks model selection | Visible plan; no implicit expansion |
| Regression | Existing card and direct installs work | Existing user updates plugin | Full suite plus legacy command smoke tests |
| Benchmark | Empty roster/UI exists | Accidental runner invocation | All result values remain `--`; zero runner calls |
| Changelog/release | Entry, tag, and release draft agree | Missing proof, stale command, unverified metric | Draft preview, tag-to-commit proof, command/link smoke tests |

Unauthorized-access, archived-data, and external-provider-failure cases are not applicable because this release adds no shared accounts, remote database, or hosted provider. Equivalent fail-closed coverage is provided for invalid local paths, corrupt caches, missing profiles, and model-host capability limits.

## Verification Plan

### Automated

- Run `python -m unittest discover -s tests -v` after every focused change and at the end.
- Run Codex plugin validation from the plugin-creator tooling.
- Add a fake runner that records planned and actual calls without invoking a model.
- Prove identical rerun equals zero calls and incremental addition equals only uncached segment calls.
- Run failure injection after each atomic staging step.
- Run subprocess tests with an isolated Windows home and UTF-8/Hebrew paths.

### Manual/live

- Install the plugin into a development marketplace.
- Confirm the exact enabled plugin version and the four namespaced skills.
- Start a fresh Codex task after reinstall and verify `ditto:work`, `ditto:design`, and `ditto:write` load the active private profile.
- Repeat in Claude before claiming native Claude plugin support.
- Perform one real task in each domain and collect the artifact plus the user's verdict.
- Inspect preflight output on the current 1.95M-token corpus and confirm the default remains bounded.
- Verify plugin update and uninstall do not modify `~/.ditto`.
- Confirm benchmark results remain `--` and no model runner was called.
- After approved model runs, preview the changelog and GitHub Release together and verify every result link.
- Confirm the README accurately directs users to `Watch` → `Custom` → `Releases` without claiming stars trigger notifications.

## Rollout And Rollback

### Rollout

1. Ship correctness and usage fixes behind the existing CLI without changing the default installed profile.
2. Add durable profile storage and migration tests.
3. Install the new plugin in a personal development marketplace.
4. Migrate a copy of the existing Ohad profile while leaving the old skill intact.
5. Verify plugin activation in a fresh task.
6. Switch the active profile pointer only after all three loaders pass.
7. Keep the legacy skill for one release as a fallback.
8. Publish updated docs only after behavior matches them.
9. After explicit benchmark approval and verified results, prepare the final changelog entry and GitHub Release draft.
10. Publish the release only after the final ship approval.

### Rollback

- Disable or uninstall the plugin without deleting `~/.ditto`.
- Restore the previous active profile pointer from its backup.
- Continue using the untouched legacy `you` skill.
- Revert the release commit if automated or live verification regresses.
- Do not attempt to migrate benchmark artifacts because benchmark execution is deferred.

## Risks And Fallbacks

- **Starter sample misses an important trait:** fail the affected domain quality gate and offer targeted deepening. Never invent or silently full-mine.
- **Worker model quality is inadequate:** keep the same bounded source selection and rerun only failed report hashes with a stronger worker after showing the revised plan.
- **One-pass reducer produces weaker domain files:** compile domain files from the cached shared evidence model, not from raw history again.
- **Cache corruption:** fail closed, quarantine the corrupt entry, and recompute only that entry.
- **Plugin cache replaces generated data:** prevented architecturally by storing profiles under `DITTO_HOME`.
- **Cross-host behavior differs:** claim support per host only after live proof. Keep direct adapters for unproven hosts.
- **Usage estimate differs from subscription allowance:** report source tokens and planned calls only. Do not promise a percentage of a proprietary quota.
- **Legacy migration ambiguity:** preserve every legacy file and require explicit selection rather than overwriting.
- **Scope expands into a living-memory platform:** reject watchers, hosted sync, drift systems, and broad workflow compilation until the focused plugin and benchmark prove demand.

## Open Questions

No blocking product questions remain for the implementation plan. The following release decisions are deliberately fixed:

- Native plugin v1 targets Codex and Claude; Cursor and Gemini remain adapters until separately proven.
- The default starter mine plans four bounded worker segments and one reducer.
- Full-history deep mode is explicit only.
- Generated profile state lives outside plugin caches.
- The benchmark is built and run last.

The exact public marketplace destination is a later distribution decision and does not affect the local plugin architecture or implementation tests.

## Decision Log

- Chose one canonical Ditto repository with thin host overlays, following the useful part of the Superpowers pattern.
- Chose static plugin loaders plus durable external private profile state.
- Chose bounded starter mining over full-history default mining.
- Chose stable content-addressed segments over equal-N rebalanced chunks.
- Chose one shared evidence fan-out and one reducer for all three profiles.
- Chose evidence failure over generic profile completion.
- Chose exact source-token/call disclosure over subscription-percentage claims.
- Chose Codex and Claude native proof before broader plugin claims.
- Chose to defer every benchmark model run until all product and verification work is complete.
- Chose `CHANGELOG.md` plus GitHub Releases for updates and rejected the false claim that stars notify every stargazer.

## Next Skill

Next skill: `superpowers:writing-plans`
