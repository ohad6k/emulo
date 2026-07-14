# Ditto Benchmark/Proof Release Design

**Status:** Proposed for Ohad review

**Date:** 2026-07-15

**Owner:** Ohad

**Implementation branch:** `codex/ditto-benchmark-proof-release`

**Frozen starting point:** Ditto plugin `v0.3.7` at `5f4008b0c0df40dcadb92c8fd1ba4dcf3aee40d0`

## 1. Outcome

Create a reproducible, privacy-safe benchmark that can show where Ditto improves an operator's work, design, and writing outcomes. The release must produce evidence people can inspect, proof clips that link back to that evidence, and honest limitations.

This is the first focused product milestone toward broader distribution. It does not attempt to build the full Ditto Operator OS. It preserves the current miner, profiles, defaults, CLI behavior, and local-first product identity.

The benchmark is successful when it answers a narrower question:

> Under controlled, paired conditions, does using the frozen Ditto release help the same operator produce a better result with fewer hard failures than the cold condition?

The benchmark compares complete systems: model, host, tools, permissions, budget, task state, and Ditto condition. It must not present results as pure model rankings.

## 2. Protected concurrent work

> **Hard scope lock:** Ohad is concurrently implementing Antigravity support on `feat/antigravity-source`. This benchmark branch must not copy, rebase, merge, stage, edit, or depend on that branch's uncommitted changes. Antigravity is not a benchmark host or roster entry unless its own branch independently ships and is live-verified in a later release.

The benchmark work must remain in its isolated worktree. No command from this workstream may switch, stash, reset, clean, or commit the main `D:\ditto` checkout.

## 3. Product invariants

The benchmark may add isolated fixtures, schemas, validation, documentation, and disabled-by-default tooling. It may not:

- change Ditto's current mining behavior, profile format, profile-selection behavior, or default commands;
- reduce the specificity or intelligence of an existing Ditto profile;
- publish private receipts, raw conversations, personal profile text, secrets, or local paths;
- introduce network execution into normal Ditto commands;
- imply that Ditto is a hosted data-mining service;
- use the internal "1000x" ambition as a public measured claim;
- publish a positive result when the evidence is neutral, mixed, invalid, or negative.

If the benchmark exposes a Ditto weakness, that is product evidence. The affected result remains unpublished while the product is fixed on a separate branch, a new version is frozen, and all affected cells are rerun. Results from different Ditto versions must never be combined.

## 4. Scope

This release includes:

- a versioned benchmark manifest and result schema;
- three deterministic task families: work/done, design, and writing;
- paired cold and `+Ditto` conditions;
- pre-registered scoring rules and hard-failure rules;
- randomized condition labels and blind operator verdicts;
- isolated fixtures and disposable execution worktrees;
- artifact hashing, validation, redaction, and publication status;
- a disabled-by-default runner or runbook that requires explicit approval;
- one schema-validation pilot before the full run;
- a sanitized, evidence-linked static results surface;
- proof-clip specifications for each task family and one combined launch clip;
- an opt-in tester workflow with no promotional obligation.

This release does not include:

- Antigravity support or any file from `feat/antigravity-source`;
- profile drift detection, workflow compilation, or the wider Operator OS;
- hosted accounts, billing, cloud mining, or a hosted leaderboard;
- new source adapters or changes to current source ingestion;
- automatic outreach, direct messages to stargazers, or bulk awesome-list submissions;
- a ClawHub update;
- public benchmark claims before evidence review and Ohad's explicit ship approval.

## 5. Frozen benchmark unit

Every scored cell is identified by the following immutable tuple:

`benchmark version + Ditto ref + profile manifest hash + system identity + host version + task ID + trial + condition + fixture hash + tool policy + budget policy`

Changing any member creates a different cell. A run is rejected if the manifest and artifacts disagree.

The first benchmark uses the already-published Ditto plugin tag `v0.3.7` and commit `5f4008b0c0df40dcadb92c8fd1ba4dcf3aee40d0`. If that ref cannot run safely or deterministically, the run stops. A fix requires a separately reviewed release, a newly frozen ref, and a clean benchmark restart for affected cells.

## 6. Task families

Each family has one canonical task for the public benchmark. The fixture, instructions, success tests, time/tool budget, and rubric are frozen before the pilot. The implementation plan may choose concrete fixture content, but it may not change the behaviors measured below.

### 6.1 Work/done

The system receives a small, deterministic repository with a scoped defect or feature request, relevant tests, unrelated surfaces, and one misleading but plausible path.

The task measures whether the system:

- identifies the correct scope;
- makes the smallest complete change;
- preserves unrelated behavior;
- runs proportionate verification;
- distinguishes verified facts from assumptions;
- reports incomplete or blocked work honestly;
- avoids destructive repository operations and fabricated completion claims.

Hard failures include a regression, out-of-scope modification, destructive command, fabricated test result, secret exposure, or claiming completion with required verification missing.

### 6.2 Design

The system receives a deterministic interface fixture, a named surface, a user goal, and explicit boundaries. The expected improvement requires structural hierarchy and interaction judgment, not a palette-only change.

The task measures whether the system:

- changes only the named surface;
- improves hierarchy, comprehension, and task flow;
- preserves working behavior and accessibility;
- avoids generic visual noise and recolor-only "redesigns";
- verifies the rendered result at the required viewport;
- explains material decisions with reference to the brief.

Hard failures include touching excluded surfaces, breaking the primary flow, failing the accessibility floor, presenting a recolor as a redesign, or claiming visual verification without a rendered artifact.

### 6.3 Writing

The system receives the same grounded product facts, evidence packet, audience, channel, and length constraints. It must create a channel-native launch or outreach artifact in the operator's established voice.

The task measures whether the system:

- uses only supported facts;
- preserves the operator's builder voice and specificity;
- leads with a concrete outcome or insight;
- follows channel and length constraints;
- avoids generic AI phrasing, inflated claims, spam pressure, and em dashes in X copy;
- produces a useful call to action without pretending at social proof.

Hard failures include an unsupported metric, invented testimonial, false availability claim, privacy leak, prohibited formatting, or a materially spammy call to action.

## 7. Personalization ground truth

Ditto is evaluated against a pre-registered operator rubric derived from the active profile, not against a vague impression after the run.

Before execution, Ohad approves a private checklist containing the relevant working laws for each task. The checklist is hashed and linked in the run manifest. The public package contains a sanitized rubric and the private checklist hash, never the raw profile, receipts, conversations, or examples that could identify private work.

Rubric changes after seeing an output invalidate the affected task family. Editorial clarifications that do not change scoring must be versioned and disclosed.

## 8. Experimental design

### 8.1 Conditions

- **Cold:** the system receives the frozen task and normal system/host instructions, without Ditto's operator profile or Ditto-specific skill context.
- **+Ditto:** the same system receives the same task, state, tools, permissions, and budgets with the frozen Ditto profile/skill context enabled through the supported product path.

The cold condition must not receive a paraphrase of Ditto's operator knowledge. The `+Ditto` condition must not receive additional task hints unrelated to Ditto.

### 8.2 Pair controls

Within a pair, keep constant:

- starting fixture and commit;
- system label, underlying model ID when available, host, and host version;
- system instructions other than the Ditto condition;
- tools and permission policy;
- token, time, and retry budgets;
- task text and evaluation tests;
- sampling controls or seeds when the host exposes them.

Each cell runs in a fresh disposable copy or worktree. No transcript, filesystem change, cache, memory, or evaluator note may cross from one condition into the other.

### 8.3 Blinding and order

Condition order is randomized per pair. Outputs receive opaque IDs before operator review. The reviewer must not see the condition, system identity, file path, run order, or metadata that reveals Ditto. Machine-checkable tests run independently of the blind preference review.

If output text directly reveals its condition, the objective checks remain usable but the blind preference verdict is invalid and marked as such.

### 8.4 Primary outcomes

The primary public outcomes are:

1. paired blind preference win/tie/loss rate for `+Ditto`;
2. hard-failure count by condition;
3. constraint-adherence pass rate by condition;
4. task-completion pass rate by condition.

Duration and token/tool usage are descriptive secondary outcomes. They are not framed as efficiency gains unless the host provides complete, comparable measurements.

No composite score may be introduced after results are visible. If a composite is useful, its weights and tie policy must be frozen in the manifest before the pilot.

## 9. System roster and run size

The intended qualifier roster records these supplied menu labels exactly as seen:

**Codex:** `5.5`, `5.6 Sol`, `5.6 Terra`, `5.6 Luna`, `5.4`, `5.4 Mini`, `5.3 Codex Spark`

**Claude:** `Fable 5`, `Opus 4.8`, `Sonnet 5`, `Haiku 4.5`, `Opus 4.7`, `Opus 4.6`, `Sonnet 4.6`

At execution time, each entry also records the underlying model ID when exposed, host version, date, mode, tools, permissions, and budgets. An unavailable entry is recorded as unavailable and is never silently replaced with a nearby model.

The full run consists of:

- **Qualifier:** 14 systems x 3 task families x 2 conditions x 1 trial = 84 executions.
- **Repeat stage:** the four qualifier systems with the strongest pre-registered selection result receive two additional trials per task and condition, for three total trials: 4 x 3 x 2 x 2 = 48 additional executions.
- **Total after pilot:** 132 executions if all 14 entries are genuinely available.

The top-four selection rule is frozen before the qualifier: fewest hard failures, then highest `+Ditto` paired preference result, then highest constraint-adherence result, then a deterministic alphabetical tie-break on the captured system label. This selection identifies systems for repeatability testing; it is not a claim that one underlying model is universally better.

Before any paid or rate-limited execution, the run operator records expected cost and quota from the current provider interfaces and obtains Ohad's explicit approval. Reducing the roster or repetitions to save cost creates a separately named benchmark edition and must be disclosed.

## 10. Pilot gate

The pilot uses one currently available system and all three task families in both conditions: six executions. It validates the mechanism, not Ditto's public performance.

The pilot passes only when:

- every required field is captured without manual patching;
- fixtures reset deterministically;
- condition separation is demonstrated;
- randomization and opaque labeling work;
- hashes reproduce;
- objective tests and blind verdict capture work;
- redaction detects seeded private markers;
- a sanitized artifact package can be generated from the private run root;
- no normal Ditto command or profile is changed.

Pilot outputs are labelled non-comparable and excluded from public aggregate results. A failed pilot is diagnosed and rerun from clean fixtures after the harness is fixed.

## 11. Artifact model

Private run artifacts live outside the repository under an explicit local run root. The repository contains schemas, deterministic fixtures, validators, sanitized examples, and publication manifests only.

Each execution record contains at least:

- benchmark schema and benchmark version;
- run ID, pair ID, opaque review ID, task ID, trial, condition, and randomized order;
- Ditto tag, commit SHA, profile manifest hash, and public rubric hash;
- exact menu label, underlying model ID when available, host, host version, mode, and run date;
- tool list, permission policy, token/time/tool budgets, and sampling controls when exposed;
- input fixture commit and content hash;
- start/end timestamps and duration;
- exit status, timeout/retry history, and invalidation reason;
- transcript, final output, patch, test report, and rendered-artifact hashes where applicable;
- objective rubric results, hard failures, blind verdict, and reviewer consent reference;
- redaction result and publication status.

Artifacts are append-only after evaluation. Corrections create a superseding record with a reason; they never overwrite scored evidence.

## 12. Failure, retry, and invalidation policy

- A provider or host failure before meaningful output may receive one same-system retry under the original budget. Both attempts are retained.
- A model error, poor answer, tool misuse, or budget exhaustion is a result, not grounds to cherry-pick a retry.
- If a retry is allowed, the manifest determines which attempt is scored; the operator cannot select the better output.
- Missing required artifacts make the cell invalid rather than a loss.
- Cross-condition contamination invalidates the pair.
- A changed fixture, rubric, tool policy, model identity, host mode, profile, or Ditto ref invalidates the affected comparison.
- A leaked condition label invalidates the blind preference verdict but not independently captured objective checks.
- Mixed Ditto versions, silent model substitutions, and manually reconstructed transcripts are rejected by validation.

All exclusions and invalidations appear in the public limitations record.

## 13. Privacy and consent

The benchmark is local-first. Private artifacts must be excluded from Git, screenshots, videos, public releases, and hosted analytics.

Before publishing any tester-derived artifact:

- the tester opts in to the specific task and artifact use;
- the tester can review the sanitized artifact attributed to them;
- attribution is optional;
- participation does not require a star, post, testimonial, or positive result;
- withdrawal before publication removes their public artifact while preserving an anonymous integrity record if needed;
- automated redaction and a manual privacy review both pass.

Seeded canary strings representing secrets, usernames, private paths, profile text, and receipt fragments must be caught by redaction tests. A detected leak blocks packaging.

## 14. Tester recruitment

Recruitment is opt-in and narrowly targeted after the design and implementation plan are approved. The first invitation is a public call in the existing feedback issue and Discord, not unsolicited direct messages to stargazers.

Potential participants with existing relevant context include `theconsultant`, `rjmurillo`, `TomLucidor`, and `aplaceforallmystuff`. They may be invited to one concrete role:

- review the sanitized rubric;
- validate a task fixture;
- provide one blind verdict;
- test the artifact package or reproduction instructions.

The invitation states the time required, what is private, what may become public, and that no promotion is expected. One reminder at most is allowed when someone explicitly opts in and then goes quiet.

## 15. Verification requirements

Implementation must include automated checks for:

- schema validity and rejection of unknown incompatible versions;
- deterministic fixture reset and content hashing;
- unique run/pair/review IDs;
- condition-order randomization and label concealment;
- no cross-cell workspace reuse;
- artifact hash verification and append-only behavior;
- mixed tag, profile, system, fixture, and budget rejection;
- allowed retry selection and invalidation rules;
- secret, local-path, profile-text, and canary redaction;
- sanitized package completeness and private-root exclusion;
- UTF-8 and Hebrew round trips;
- Windows path behavior;
- runner disabled by default and requiring explicit approval.

The existing Ditto suite must remain green. Benchmark tooling must not be imported or executed during normal Ditto mining, bootstrap, installation, or profile loading.

## 16. Publication package

The publication package is static and evidence-linked. It contains:

- benchmark version, frozen refs, captured system identities, dates, and environment limitations;
- the public task and rubric definitions;
- aggregate paired outcomes and hard-failure tables;
- per-cell sanitized evidence links and artifact hashes;
- all exclusions, invalidations, unavailable roster entries, and retry history;
- clear language that these are complete-system comparisons;
- reproduction and independent-review instructions.

The proof media set contains:

1. a work/done clip showing scope, verification, and evidence;
2. a design clip showing the structural before/after and rendered verification;
3. a writing clip showing grounded voice and constraint adherence;
4. a short combined hero clip that links to the full evidence package.

Clips may simplify presentation but may not hide losses, splice outputs into a fictional run, or introduce metrics absent from the published evidence.

## 17. Claim and ship gates

No public benchmark claim is drafted as a conclusion until the complete sanitized evidence package passes review. Allowed language must match the observed scope, such as "In this frozen paired benchmark..." rather than universal claims.

Publication requires all of the following:

- the full run or explicitly named smaller edition is complete;
- validators and the existing Ditto test suite pass;
- private-data review passes;
- exclusions and limitations are included;
- all claimed numbers recalculate from published sanitized records;
- Ohad reviews the evidence and explicitly approves shipping;
- the benchmark receives a separate GitHub release from the plugin release.

If `+Ditto` does not show a supported advantage, the team publishes no inflated launch claim. The evidence becomes a product-improvement input.

## 18. Distribution handoff

Only after the ship gate, launch preparation coordinates the GitHub release, README proof surface, website, YouTube proof, Product Hunt, Hacker News, relevant Reddit communities, X, creator follow-ups, and existing registries in one concentrated window. Every placement uses channel-native copy and points to inspectable proof.

The current traffic model suggests roughly 4,900 additional qualified visitors would be needed to gain 826 stars if the observed visitor-to-star conversion stayed near 17%. This is a planning estimate, not a promise. The benchmark's job is to create a credible reason for those visitors to arrive, try Ditto, and talk about it.

No more bulk awesome-list pull requests are part of this milestone. Existing high-value submissions may be maintained when maintainers respond, without repeated promotional follow-ups.

## 19. Exit criteria

The Benchmark/Proof release is ready for explicit ship review when:

- the frozen benchmark can be reproduced from documented inputs;
- all scored cells are valid or transparently accounted for;
- paired results and hard failures recalculate from sanitized artifacts;
- privacy and redaction checks pass;
- proof clips trace to exact benchmark evidence;
- the current Ditto miner, CLI, profiles, and tests show no regression;
- Antigravity work remains untouched and independent;
- public claims are narrower than or equal to what the evidence proves.

The next phase, including wider Operator OS features or monetized team pilots, begins as a separate design and release decision after this milestone produces trustworthy evidence.
