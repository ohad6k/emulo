# Ditto Plugin, Personal Skills, and Bounded Mining Design

## Summary

Ditto becomes one plugin that installs a small set of static, namespaced skills and stores each user's generated personal profile outside the plugin cache.

The plan has two independent release milestones.

The **Plugin release** ships first:

1. `ditto:work`, `ditto:design`, and `ditto:write` make the mined profile useful for execution, UI judgment, and marketing voice.
2. The default mine is bounded, visible, cached, and incremental so first use does not unexpectedly consume a large model allowance.

The **Benchmark release** follows from one exact already-published plugin tag. It contains the 14-entry comparison, leaderboard, and proof videos. It cannot delay or block the Plugin release.

Version numbers are assigned from repository tag state at each ship gate. `Plugin release` and `Benchmark release` are milestone names, not hardcoded `v1` and `v2` tags.

The full implementation architecture is documented in [the architecture plan](../plans/2026-07-10-ditto-plugin-architecture-plan.md).

## Product Promise

Ditto reads how a person actually worked with AI and turns that evidence into a personal layer their agent can use.

The product must prove more than tone imitation:

- **Work:** understand shorthand, definition of done, verification habits, and repeated working rules.
- **Design:** understand references, hierarchy, taste, and rejection patterns.
- **Write:** understand voice, slang, platform formats, and banned AI-writing patterns.

These are not separate brands or characters. They are task-specific views of the same person, delivered under Ditto.

## Plugin Shape

The public product remains **Ditto**. The initial plugin skills are:

- `ditto:mine`
- `ditto:work`
- `ditto:design`
- `ditto:write`

Codex and Claude are native-plugin candidates from one canonical repository. Before the new storage or mining architecture is built, a minimal per-host spike must prove that a namespaced skill can invoke local Python and read a harmless fixture under `DITTO_HOME`. Existing Cursor, Gemini, `AGENTS.md`, Codex, and Claude direct install adapters remain available. Native support is claimed only for hosts that pass the spike plus clean-install and fresh-task activation proof.

The installed plugin contains only stable product code, prompts, and loader skills. It never contains the user's generated profile.

Private state lives under `DITTO_HOME`, defaulting to:

```text
~/.ditto/
  active-profile.json
  profiles/default/
  cache/
  runs/
```

This separation ensures plugin update or uninstall cannot erase the personal profile or mining cache.

Skill descriptions route tasks deliberately:

- `ditto:mine` is only for explicit setup, mining, update, or deepen requests.
- `ditto:design` loads core plus design context for UI, UX, visual, and frontend-design work.
- `ditto:write` loads core plus writing context for marketing, social, replies, copy, and user-voice work.
- `ditto:work` loads core context for other execution and verification tasks and explicitly excludes design and writing triggers.

Combined design-and-copy work may load `design` and `write`; it must not accidentally load all three domain skills.

## End-to-End User Flow

### First use

The recommended entry point remains as simple as current Ditto:

```text
run ditto
```

The plugin routes that phrase to the mining skill. The user does not need to know skill namespaces, Python locations, chunk counts, output folders, or agent-specific install paths.

Ditto then:

1. confirms the plugin is registered without running a model;
2. finds supported local session sources;
3. performs redaction and dedupe locally;
4. shows one compact preflight with real history size, starter selection, planned calls, and cache reuse;
5. runs the bounded starter mine;
6. compiles and validates work, design, and writing profiles from one report set;
7. activates the complete profile atomically;
8. verifies one real task and returns the card plus exact evidence.

The result tells the user what changed, which skills are active, where private data lives, how much source text and how many calls were used, and whether any domain needs more evidence. There is no manual copy-and-paste installation step.

### Later updates

The user can say:

```text
update ditto
```

Ditto checks only new or changed sessions. If nothing changed, it makes zero model calls and says the profile is current. If new evidence exists, it reuses cached reports and activates a new profile version only after the full pack validates.

### Existing CLI path

The current one-file Python flow remains supported. For the Plugin release, `ditto.py` stays the canonical zero-dependency, single-file runtime, including the new cache and profile-store behavior. Dry run, extraction, card rendering, and direct installs continue to work. The plugin is the recommended path because it automates orchestration without removing the simple CLI fallback.

## Installation and Mining Are Separate

Installing or updating the Ditto plugin performs:

- zero log scans;
- zero model calls;
- zero benchmark calls;
- zero writes to private profile state, except explicit migration after the user invokes Ditto.

Mining begins only when the user invokes `ditto:mine`.

The mine starts with a local preflight that shows:

- detected sources and valid sessions;
- approximate tokens after redaction and dedupe;
- cached and uncached coverage;
- selected source-token ceiling;
- planned worker and reducer calls;
- full-history deep-mode cost as a separate option.

The default does not require a configuration wizard. It proceeds with the bounded starter contract. Only deep mode or targeted deepening requires explicit approval because it expands model usage.

## Token Contract

The current flow can send nearly the complete post-dedupe corpus through one worker per roughly 70K tokens. On the current local history, that means approximately 1.95M source tokens and about 28 workers before reduction.

The release default is calibrated rather than assumed. Ditto first tests 4×25K source tokens plus one reducer, then bounded wider-coverage candidates of 6×20K and 8×20K if needed. The calibration ceiling is 160K selected source tokens and nine planned calls. The smallest candidate that passes a predeclared must-recover checklist and the three fresh-task probes becomes the default. If none passes, Ditto does not ship the claim that bounded starter mining is good enough.

Every candidate uses one shared worker-report set for work, design, and writing and never expands beyond its displayed plan.

The model host may add system prompt or tool overhead that Ditto cannot measure precisely. Ditto reports selected source tokens and planned calls, not a guessed percentage of a subscription allowance.

Full-history mining remains available as explicit deep mode. Deep mode is separately planned, resumable, redacted, and never starts during install, update, migration, or benchmark preparation.

## Stable Selection and Reuse

The equal-N chunk splitter is replaced for mining orchestration by stable sealed segments.

- Valid session blocks are normalized after redaction and filtering.
- Whole sessions are grouped into bounded segments.
- A sealed segment is identified by a content hash and extraction schema version.
- New sessions create new segments rather than rebalancing old segments.
- Default selection is deterministic and stratified across the observed timeline and available sources.
- Known system-generated continuation summaries and invalid input are excluded.

Worker reports are cached by segment hash and prompt schema version. Reductions are cached by the ordered report-set hash and reducer schema version.

Therefore:

- identical rerun means zero model calls;
- a changed prompt invalidates only the affected cache layer;
- new history mines only uncached segments;
- corrupt cache entries fail closed and are recomputed individually.

## Quality Contract

The bounded default may reduce how much history is read. It may not reduce the evidence bar.

Evidence is counted across distinct user-authored sessions and time/source strata, not worker-report boundaries. An inferred repeated behavior needs two distinct sessions and two private quotes. A direct, unequivocal instruction may preserve a rare high-salience law from one session only when labeled as an explicit low-frequency instruction, never as a repeated habit, and only when no evidence contradicts it. Every installed instruction still needs a specific operational implication and no generic filler.

The fast worker role extracts evidence. The strongest available reducer role makes the final judgment.

Every profile manifest records:

- source tools and time coverage;
- selected source tokens;
- number of sampled reports;
- prompt and schema versions;
- report and reduction hashes;
- domains that passed or failed the evidence gate.

Receipts state the sampled sessions, strata, and occurrence count. They never imply all history was read.

If a domain is weak, Ditto does not install invented instructions. It keeps that domain inactive and gives one exact targeted deepen action. It does not silently run deep mode.

Generated runtime skills stay lean. Full quotes, contradictions, and lower-confidence evidence remain in the private appendix and are loaded only for audit or deepening.

Before any candidate runs, the existing deep Ohad profile is turned into a frozen must-recover checklist of core working laws, design rejection patterns, and voice constraints. Every candidate is judged against the same checklist and real receipts. The smallest passing candidate must also pass one fresh-task human-reviewed probe in each domain. Release dogfood failure blocks the bounded-default claim; targeted deepening remains for later users whose history is genuinely sparse, not as a waiver for failed flagship calibration.

## Generation and Activation

Each worker extracts work, design, and writing evidence together. One reducer compiles:

- `you.md`
- `you-designer.md`
- `you-writer.md`
- `appendix.md`
- `card.json`
- `manifest.json`

The complete pack is written to a staged version directory. Ditto validates every file, frontmatter name, receipt reference, and manifest hash before changing the active profile pointer.

Activation is atomic:

- all files become active together;
- any validation or write failure preserves the previous active version;
- plugin loaders fail closed if the pointer or manifest is corrupt;
- plugin uninstall leaves private state untouched.

## Blocking Correctness Fixes

The plugin work cannot ship on top of the current defects.

The release must fix and test:

- stale chunk files surviving a smaller rerun;
- corrupt or unsupported-only logs incorrectly reaching a successful empty output;
- malformed frontmatter passing substring validation;
- Hebrew and Unicode Windows paths failing at console output;
- direct in-place installs without rollback, which must become atomic before multi-file packs;
- hardcoded one-profile destinations preventing coexistence;
- misleading distinctions between source support, adapter support, and native plugin support.

The implementation uses test-driven changes for each defect and preserves the existing working extraction, card, and direct install behaviors.

## Privacy and Claim Accuracy

The honest claim is:

> Ditto's extractor, redaction, caches, and generated profiles stay local. Selected redacted text is processed by the model provider the user chooses. With a local model, the entire mining flow can remain local.

The README and security documentation must not say or imply that cloud model processing is local merely because the coding-agent client runs on the user's machine.

No public artifact contains the full profile, raw logs, or private appendix by default.

## Plugin Release Verification

The Plugin release is not called done because manifests and files exist.

Required proof includes:

- a front-loaded Codex/Claude viability spike proving namespacing, local Python invocation, and `DITTO_HOME` fixture access per claimed native host;
- the complete automated suite passing;
- stale chunk and corrupt-input regressions covered;
- exact call-count tests through a fake runner;
- identical rerun producing zero calls;
- incremental history producing only uncached work;
- failure injection preserving the prior profile after every staged-write boundary;
- plugin manifest validation;
- clean isolated install for every host still claimed as native after the spike;
- fresh-task visibility of the namespaced skills;
- positive and negative trigger tests proving domain skills do not overlap accidentally;
- plugin reinstall preserving `~/.ditto`;
- exact UTF-8/Hebrew round trip;
- one real work probe, one design probe, and one writing probe with human verdicts;
- a separate spec-compliance review and code-quality review, followed by fixes and re-review.

Native support is claimed per host only after that host passes live registration and activation proof.

## Migration and Rollback

Existing `you` installs are copied into a staged Ditto profile version after backup. While the new profile is staged and verified, the legacy skill remains active and the new personal loaders remain inactive. At cutover, the legacy skill directory is moved out of host discovery into `~/.ditto/legacy/...` before the new active pointer is enabled. A fresh task must never see both personal instruction sets.

If the plugin fails:

- uninstall or disable the plugin;
- restore the prior active-profile pointer;
- move the legacy `you` backup back to its original host discovery path;
- keep `~/.ditto` for repair or reinstall.

Marked `AGENTS.md` and `GEMINI.md` context blocks are handled as separate adapter migrations so they cannot remain always-on and compete with native loaders. No migration writes private state into a replaceable plugin cache.

## Benchmark Boundary

The benchmark is a separate second release, not part of installation, default mining, or the Plugin release gate. Benchmark preparation starts from an exact already-published plugin tag.

Before model runs, Ditto may prepare:

- the fixed task manifest;
- exact model/system roster fields;
- cold versus `+Ditto` cells;
- blind verdict workflow;
- raw artifact locations;
- a thin result schema, deterministic fixtures, and a disabled runner.

Actual model runs remain disabled until the Plugin release has shipped, its exact tag is frozen for comparison, and the user gives explicit benchmark approval.

If real-user feedback requires a Ditto fix, the fix must be verified and published as a plugin patch before the benchmark tag is frozen. If the plugin tag changes after runs begin, affected comparison cells restart; one leaderboard never mixes plugin versions or unreleased code.

The first approved run validates the result schema against real host/model/mode/tool/budget output. Only after that proof does Ditto build the polished result UI and video-facing leaderboard, avoiding speculative UI work around fields that may change.

The frozen initial roster includes every supplied menu entry: Codex `5.5`, `5.6 Sol`, `5.6 Terra`, `5.6 Luna`, `5.4`, `5.4 Mini`, and `5.3 Codex Spark`; Claude `Fable 5`, `Opus 4.8`, `Sonnet 5`, `Haiku 4.5`, `Opus 4.7`, `Opus 4.6`, and `Sonnet 4.6`. Exact menu labels, underlying model IDs when available, host version, date, mode, tools, and budgets are recorded. Different native agent harnesses are described as system comparisons, not pure model comparisons.

After the pilot validates the schema, all 14 entries run the same cold and `+Ditto` qualifier. The top four advance to the frozen repeated benchmark. Real artifacts then power the evidence-linked leaderboard, separate `done`, design, and writing proof clips, and one combined hero clip.

## Changelog and GitHub Releases

Every user-visible Ditto release gets one versioned entry in `CHANGELOG.md` with the same compact structure:

- what changed;
- why it matters;
- how to upgrade;
- what was verified;
- known limits.

The Plugin release gets the first entry and GitHub Release as soon as the plugin gates pass. It describes the plugin, bounded mining, three domain skills, migration, proof, and known limits. It contains no placeholder benchmark results and does not wait for benchmark production.

The Benchmark release gets a second entry and GitHub Release after approved runs, leaderboard, and videos are verified. It links every reported result to raw artifacts and names the exact published plugin tag used by all `+Ditto` conditions.

GitHub stars are bookmarks, not release subscriptions. Ditto must not claim that a release reaches everyone who starred the repository. The README instead gives the real notification path: open the repository's `Watch` menu, choose `Custom`, then enable `Releases`. This matches [GitHub's notification documentation](https://docs.github.com/en/subscriptions-and-notifications/get-started/configuring-notifications) and [release documentation](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

Each release draft and its evidence are prepared separately. Publication remains a separate ship gate for each: Ohad publishes it or explicitly authorizes publication after reviewing that exact draft.

## Plugin Release Boundary

The Plugin release is complete only when:

- one Ditto plugin exposes the four approved skills;
- installation performs zero model calls;
- the starter mine stays within its displayed hard plan;
- its default is the smallest bounded calibration candidate that passed the frozen recall and fresh-task gates;
- cached reruns avoid duplicate model work;
- all three personal domains pass the evidence and activation gates;
- existing profiles migrate without loss;
- every claimed native host passed the viability spike and was live-verified separately;
- privacy and cost claims match real behavior;
- separate spec-compliance and code-quality reviews were fixed and re-reviewed;
- its own changelog entry and GitHub Release match the verified plugin tag and proof;
- after explicit plugin ship approval, a clean install succeeds from the published tag.

No benchmark manifest, model run, leaderboard, or video is required to ship the Plugin release.

## Benchmark Release Boundary

The Benchmark release is complete only when:

- it uses one exact already-published plugin tag across every `+Ditto` cell;
- benchmark runners remained disabled until the Plugin release shipped and explicit benchmark approval was given;
- the first approved pilot validated the real result schema before bulk runs or UI polish;
- all 14 cold and `+Ditto` qualifiers and top-four repeated runs follow the frozen manifest;
- every approved result, leaderboard value, and proof-video claim traces to a raw artifact;
- its separate changelog entry and GitHub Release name the frozen plugin tag and match the verified benchmark tag;
- Ohad gives a second explicit ship approval before the benchmark Release, leaderboard, or videos are published.

Watchers, hosted sync, billing, correction ledgers, profile drift, broad workflow compilation, and a hosted leaderboard service remain outside both releases.
