# Ditto Plugin, Personal Skills, and Bounded Mining Design

## Summary

Ditto becomes one plugin that installs a small set of static, namespaced skills and stores each user's generated personal profile outside the plugin cache.

The release has three connected outcomes:

1. `ditto:work`, `ditto:design`, and `ditto:write` make the mined profile useful for execution, UI judgment, and marketing voice.
2. The default mine is bounded, visible, cached, and incremental so first use does not unexpectedly consume a large model allowance.
3. A public benchmark is prepared only after the plugin is correct and useful. No benchmark model runs occur during this release work until the final explicit stage.

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

Codex and Claude receive native plugin overlays from one canonical repository. Existing Cursor, Gemini, `AGENTS.md`, Codex, and Claude direct install adapters remain available, but native plugin support is claimed only where a clean install and fresh-task activation have been proven.

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

The current one-file Python flow remains supported. Dry run, extraction, card rendering, and direct installs continue to work. The plugin is the recommended path because it automates orchestration without removing the simple CLI fallback.

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

The new starter mine uses:

- four stable selected segments;
- approximately 25K source tokens maximum per segment;
- four worker calls;
- one reducer call;
- one shared worker-report set for work, design, and writing;
- no implicit expansion beyond the displayed plan.

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

Every instruction installed into a personal skill requires:

- support from at least two independent selected reports;
- at least two verbatim quotes in the private appendix;
- a specific operational implication for the agent;
- no generic filler a stranger could have guessed.

The fast worker role extracts evidence. The strongest available reducer role makes the final judgment.

Every profile manifest records:

- source tools and time coverage;
- selected source tokens;
- number of sampled reports;
- prompt and schema versions;
- report and reduction hashes;
- domains that passed or failed the evidence gate.

Receipts state `x/4 sampled reports`. They never imply all history was read.

If a domain is weak, Ditto does not install invented instructions. It keeps that domain inactive and gives one exact targeted deepen action. It does not silently run deep mode.

Generated runtime skills stay lean. Full quotes, contradictions, and lower-confidence evidence remain in the private appendix and are loaded only for audit or deepening.

Before release, the starter mine is compared with the existing deep Ohad profile. It must preserve the core working laws, design rejection patterns, and voice constraints with real receipts. It must also pass one fresh-task human-reviewed probe in each domain.

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
- partial multi-file installs without rollback;
- hardcoded one-profile destinations preventing coexistence;
- misleading distinctions between source support, adapter support, and native plugin support.

The implementation uses test-driven changes for each defect and preserves the existing working extraction, card, and direct install behaviors.

## Privacy and Claim Accuracy

The honest claim is:

> Ditto's extractor, redaction, caches, and generated profiles stay local. Selected redacted text is processed by the model provider the user chooses. With a local model, the entire mining flow can remain local.

The README and security documentation must not say or imply that cloud model processing is local merely because the coding-agent client runs on the user's machine.

No public artifact contains the full profile, raw logs, or private appendix by default.

## Verification

The release is not called done because manifests and files exist.

Required proof includes:

- the complete automated suite passing;
- stale chunk and corrupt-input regressions covered;
- exact call-count tests through a fake runner;
- identical rerun producing zero calls;
- incremental history producing only uncached work;
- failure injection preserving the prior profile after every staged-write boundary;
- plugin manifest validation;
- clean Codex and Claude install in isolated environments;
- fresh-task visibility of the namespaced skills;
- plugin reinstall preserving `~/.ditto`;
- exact UTF-8/Hebrew round trip;
- one real work probe, one design probe, and one writing probe with human verdicts;
- a separate spec-compliance review and code-quality review, followed by fixes and re-review.

Native support is claimed per host only after that host passes live registration and activation proof.

## Migration and Rollback

Existing `you` installs are copied into a staged Ditto profile version after backup. The original file is not deleted during the migration release.

If the plugin fails:

- uninstall or disable the plugin;
- restore the prior active-profile pointer;
- continue using the untouched legacy `you` skill;
- keep `~/.ditto` for repair or reinstall.

No migration writes into a replaceable plugin cache.

## Benchmark Boundary

The benchmark is the final proof layer, not part of installation or default mining.

Before model runs, Ditto may prepare:

- the fixed task manifest;
- exact model/system roster fields;
- cold versus `+Ditto` cells;
- blind verdict workflow;
- raw artifact locations;
- a result UI where every value is `--`.

Actual model runs remain disabled until the plugin, token contract, quality gates, migration, tests, and live probes are complete and the user gives explicit approval.

The initial roster includes all entries supplied from the Codex and Claude model menus. Exact menu labels, underlying model IDs when available, host version, date, mode, tools, and budgets are recorded. Different native agent harnesses are described as system comparisons, not pure model comparisons.

## Changelog and GitHub Releases

Every user-visible Ditto release gets one versioned entry in `CHANGELOG.md` with the same compact structure:

- what changed;
- why it matters;
- how to upgrade;
- what was verified;
- known limits.

At the end of this plan, after the benchmark is explicitly approved and its results are verified, the matching changelog entry becomes the source for a GitHub Release draft. The release tag, commands, proof links, benchmark artifacts, and limitations must all match the verified commit.

GitHub stars are bookmarks, not release subscriptions. Ditto must not claim that a release reaches everyone who starred the repository. The README instead gives the real notification path: open the repository's `Watch` menu, choose `Custom`, then enable `Releases`. This matches [GitHub's notification documentation](https://docs.github.com/en/subscriptions-and-notifications/get-started/configuring-notifications) and [release documentation](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

The release draft and evidence are prepared as part of the work. Publication remains the final ship gate: Ohad publishes it or explicitly authorizes publication after reviewing the exact draft.

## Release Boundary

This release is complete only when:

- one Ditto plugin exposes the four approved skills;
- installation performs zero model calls;
- the starter mine stays within its displayed hard plan;
- cached reruns avoid duplicate model work;
- all three personal domains pass the evidence and activation gates;
- existing profiles migrate without loss;
- Codex and Claude support are live-verified separately;
- privacy and cost claims match real behavior;
- benchmark runners stayed disabled until every preceding gate passed and explicit approval was given;
- approved benchmark results are backed by raw artifacts;
- the changelog entry and GitHub Release draft match the verified tag and proof.

Watchers, hosted sync, billing, correction ledgers, profile drift, broad workflow compilation, and a public leaderboard remain outside this release.
