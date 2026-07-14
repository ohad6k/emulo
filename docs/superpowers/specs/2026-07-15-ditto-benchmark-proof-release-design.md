# Ditto Benchmark/Proof Release Design

**Status:** Revised after additional Ohad Step 8 distribution review; proposed for final approval

**Date:** 2026-07-15

**Owner:** Ohad

**Implementation branch:** `codex/ditto-benchmark-proof-release`

**Frozen starting point:** Ditto plugin `v0.3.7` at `5f4008b0c0df40dcadb92c8fd1ba4dcf3aee40d0`

## Review changelog (A1-A12)

- **A1:** Sections 6.3, 8.3, 8.4, and 8.5 now treat writing voice as structurally de-blindable. Writing uses pre-registered mechanism checks; any public preference verdict comes only from reviewers unfamiliar with the operator.
- **A2:** New Section 8.4 defines the independent reviewer role, disqualifies Ohad from blind preference judging, and makes consent and blinding evidence mandatory in Section 11.
- **A3:** Sections 8.1, 8.2, and 11 freeze host-native persistent personalization as absent in both v1 arms and record that state per cell. Claims are explicitly limited to a clean-host cold-start comparison.
- **A4:** Section 6 now requires a primary and held-out variant per family, and Section 9 requires two trials per variant. The later 14-system qualifier is explicitly non-v1 and non-evidentiary.
- **A5:** Section 8.5 pre-commits to raw denominators, Wilson 95% intervals where defined, and the label "small-n, directional only," with no significance claims.
- **A6:** Sections 7, 8.5, and 16 restrict profile-derived rubric adherence to mechanism validation; it cannot be published as a standalone proof of value.
- **A7:** Section 9 replaces the 132-execution default with the named **Ditto Proof v1** edition: 24 paired comparisons and 48 isolated cell executions. The 14-system roster is deferred to a separately approved Atlas edition.
- **A8 (superseded by A10):** Section 18 originally kept the top-down traffic estimate as a non-binding scenario before the additional distribution review removed it entirely.
- **A9:** Section 9 retains exact captured labels, allows attrition, and forbids substitution or backfilling of unavailable systems.
- **A10:** Section 18 was rebuilt from fixed operator channel constraints and live research captured on 2026-07-15. The top-down 17% conversion and 4,900-visitor scenario is removed. The new plan uses dated per-channel evidence, marks unsupported reach and star conversion unknown, assigns execution ownership, stages channel-native copy/assets, gives a conditional dated calendar, sets Hacker News planned traffic to zero, and keeps every external action behind a separate approval.
- **A11:** A live launch-readiness audit on 2026-07-15 separated ClawHub downloads, installs, PyPI packages, GitHub clones, and stars instead of treating them as one adoption number. It also found that the public Discord invite is broken and that GitHub `v0.3.8` is newer than PyPI `0.3.6`; Section 18 now fails closed on both release-surface and community-link drift.
- **A12:** A read-only release review on 2026-07-15 confirmed that `v0.3.8` still pins MCP `server.json` to PyPI `0.3.6`, has no PyPI publish workflow, and has no repository-secret or local-credential evidence for an approved upload path. Section 18 now separates the repository changes, PyPI dashboard/trusted-publisher action, credential boundary, and provider receipt required to align those surfaces.

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
- randomized condition labels and independent third-party blind verdicts;
- isolated fixtures and disposable execution worktrees;
- artifact hashing, validation, redaction, and publication status;
- a disabled-by-default runner or runbook that requires explicit approval;
- one schema-validation pilot before the scored Ditto Proof v1 run;
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

Each family has two canonical variants for the public benchmark: one primary variant and one held-out variant. Both are frozen and hashed before the pilot. The held-out variant is excluded from pilot execution, task tuning, rubric tuning, and prompt iteration. Its content remains concealed from scored systems and preference reviewers until its executions are complete, then is published with the final evidence package.

The fixture, instructions, success tests, time/tool budget, and rubric are frozen before the pilot. The implementation plan may choose concrete fixture content, but it may not change the behaviors measured below. The pilot uses separate non-scored schema fixtures so it does not consume either public benchmark variant.

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

The system receives the same grounded synthetic-product facts, evidence packet, audience, channel, and length constraints. Scored fixtures use fictional product and person names so they do not reveal Ohad's identity. The system must create a channel-native launch or outreach artifact in the operator's established voice.

The task measures whether the system:

- uses only supported facts;
- preserves the operator's builder voice and specificity;
- leads with a concrete outcome or insight;
- follows channel and length constraints;
- avoids generic AI phrasing, inflated claims, spam pressure, and em dashes in X copy;
- produces a useful call to action without pretending at social proof.

Hard failures include an unsupported metric, invented testimonial, false availability claim, privacy leak, prohibited formatting, or a materially spammy call to action.

Voice match is expected to reveal the `+Ditto` condition to anyone familiar with Ohad's writing, so operator-recognition preference is not a valid blind outcome for this family. Voice and operator-specific constraints are scored only as pre-registered mechanism checks. A public writing preference verdict, if collected, is limited to channel quality, clarity, usefulness, and groundedness and must come from independent reviewers with no prior exposure to the operator's identity or voice.

## 7. Personalization ground truth

Ditto is evaluated against a pre-registered operator rubric derived from the active profile, not against a vague impression after the run.

Before execution, Ohad approves a private checklist containing the relevant working laws for each task. The checklist is hashed and linked in the run manifest. The public package contains a sanitized rubric and the private checklist hash, never the raw profile, receipts, conversations, or examples that could identify private work.

Rubric changes after seeing an output invalidate the affected task family. Editorial clarifications that do not change scoring must be versioned and disclosed.

Profile-derived rubric adherence is an internal mechanism check: it can show that the profile was applied as designed, but it cannot by itself prove product value. It is never published as a standalone Ditto win and is excluded from public system-selection or launch claims.

## 8. Experimental design

### 8.1 Conditions

- **Cold:** the system receives the frozen task and clean benchmark-host instructions, without Ditto's operator profile or Ditto-specific skill context.
- **+Ditto:** the same system receives the same task, state, tools, permissions, budgets, and clean benchmark-host instructions with the frozen Ditto profile/skill context enabled through the supported product path.

The cold condition must not receive a paraphrase of Ditto's operator knowledge. The `+Ditto` condition must not receive additional task hints unrelated to Ditto.

For Ditto Proof v1, host-native persistent personalization is absent in both arms. The dedicated benchmark home must contain no user `AGENTS.md`, `CLAUDE.md`, memory, rules, prior chat memory, custom instructions, or equivalent operator context. Repository-local task instructions and host safety/tool instructions remain identical in both arms. This isolates the addition of Ditto but limits the claim to **Ditto versus a clean-host cold start**, not Ditto versus another personalization product or an already-personalized host. The effect is attributable to Ditto only because host-native personalization is held constant across the pair.

### 8.2 Pair controls

Within a pair, keep constant:

- starting fixture and commit;
- system label, underlying model ID when available, host, and host version;
- system instructions other than the Ditto condition;
- host-native persistent-context state and dedicated benchmark home;
- tools and permission policy;
- token, time, and retry budgets;
- task text and evaluation tests;
- sampling controls or seeds when the host exposes them.

Each cell runs in a fresh disposable copy or worktree. No transcript, filesystem change, cache, memory, or evaluator note may cross from one condition into the other.

### 8.3 Blinding and order

Condition order is randomized per pair. Outputs receive opaque IDs before reviewer access. The reviewer must not see the condition, system identity, operator identity, file path, run order, or metadata that reveals Ditto. Machine-checkable tests run independently of the blind preference review.

If output text directly reveals its condition, the objective checks remain usable but the blind preference verdict is invalid and marked as such.

Writing receives family-specific treatment. Because operator voice itself may expose the condition, the public preference question cannot ask which output sounds more like Ohad. A writing preference verdict is valid only when the reviewer has no prior exposure to Ohad or his voice and judges profile-independent qualities defined in Section 6.3. If those conditions cannot be met, writing reports no blind preference outcome.

### 8.4 Independent reviewer role

Blind preference verdicts are cast by an independent third party who:

- did not create or approve the operator rubric;
- has no prior exposure to the operator's identity, writing voice, Ditto profile, or benchmark conditions;
- did not operate the model runs or prepare the blinded artifacts;
- consents to the specific review task and publication of an anonymous verdict;
- confirms after review that no condition-revealing metadata or context was visible.

Ohad is the benchmark operator and rubric approver and is explicitly disqualified from casting blind preference verdicts. The run record links the reviewer's consent reference, eligibility attestation, blinding confirmation, and any invalidation reason. A reviewer who recognizes the operator or condition stops and records the verdict as invalid.

### 8.5 Public outcomes and uncertainty

The primary public outcomes are:

1. paired blind preference win/tie/loss rate for `+Ditto`;
2. hard-failure count by condition;

Blind preference is omitted for writing cells that do not satisfy Sections 6.3, 8.3, and 8.4. Profile-derived rubric adherence, operator-specific voice match, profile-independent constraint adherence, and task-completion checks remain diagnostic evidence, but they are not promoted to standalone proof that Ditto creates value.

Duration and token/tool usage are descriptive secondary outcomes. They are not framed as efficiency gains unless the host provides complete, comparable measurements.

No composite score may be introduced after results are visible. If a composite is useful, its weights and tie policy must be frozen in the manifest before the pilot.

Ditto Proof v1 is pre-labelled **small-n, directional only**. The publication reports raw numerators, denominators, ties, exclusions, and invalidations. Where a binary proportion is defined, it also reports a two-sided Wilson 95% confidence interval; `+Ditto` preference intervals exclude ties and show the tie count separately. No p-values, statistical-significance language, universal model ranking, or population-level performance claim is permitted. This uncertainty policy is frozen in the manifest before the pilot and cannot change after outputs are visible.

## 9. Ditto Proof v1 and later roster

### 9.1 Shippable v1 edition

The default public edition is named **Ditto Proof v1**. During cost preflight, Ohad selects exactly two systems: one general-purpose Codex-host system and one general-purpose Claude-host system. Mini, fast, and preview-labelled entries are ineligible. Selection may use documented capability, availability, and cost, but no benchmark output. The exact visible menu label, underlying model ID when exposed, host version, and selection screenshot are frozen before the pilot. Once frozen, an unavailable system is not substituted; the edition must wait or restart under a new benchmark version.

The scored v1 run consists of:

- 2 frozen systems;
- 3 task families;
- 2 frozen variants per family, one primary and one held-out;
- 2 independent trials per system/family/variant;
- 2 conditions per paired comparison, cold and `+Ditto`.

This produces **24 paired comparisons and 48 isolated cell executions**: `2 systems x 3 families x 2 variants x 2 trials = 24 pairs`; each pair contains two condition executions. It is small enough for one operator to finish while providing repeated trials and a held-out variant in every family.

There is no result-driven qualifier or top-system selection in v1. Both systems are preselected and every valid cell is reported. Reducing the systems, variants, or trials creates a separately named incomplete pilot edition and cannot be presented as Ditto Proof v1.

Before any paid or rate-limited execution, the run operator records current expected cost and quota from provider interfaces and obtains Ohad's explicit approval.

### 9.2 Aspirational Atlas edition

A later broad-roster edition, provisionally named **Ditto Proof Atlas**, may evaluate these supplied menu labels exactly as seen:

**Codex:** `5.5`, `5.6 Sol`, `5.6 Terra`, `5.6 Luna`, `5.4`, `5.4 Mini`, `5.3 Codex Spark`

**Claude:** `Fable 5`, `Opus 4.8`, `Sonnet 5`, `Haiku 4.5`, `Opus 4.7`, `Opus 4.6`, `Sonnet 4.6`

At execution time, each entry also records the underlying model ID when exposed, host version, date, mode, tools, permissions, and budgets. An unavailable entry is recorded as unavailable and is never silently replaced with a nearby model.

Roster attrition is expected. Unavailable entries remain visible as unavailable; no nearby, newer, cheaper, or similarly named system may backfill them. Atlas is aspirational, outside Ditto Proof v1, and not authorized by this specification. It requires its own reviewed design, cost approval, repetition policy, and ship gate. Any future qualifier is exploratory and cannot itself be published as a performance result or used to hide unselected systems.

## 10. Pilot gate

The pilot uses one currently available system and separate non-scored fixtures for all three task families in both conditions: six executions. It validates the mechanism, not Ditto's public performance, and cannot use the primary or held-out v1 fixtures.

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
- host-native persistent-context state, dedicated benchmark-home identifier, and hashes of all host/repository instruction files visible to the cell;
- tool list, permission policy, token/time/tool budgets, and sampling controls when exposed;
- input fixture commit and content hash;
- start/end timestamps and duration;
- exit status, timeout/retry history, and invalidation reason;
- transcript, final output, patch, test report, and rendered-artifact hashes where applicable;
- objective rubric results, hard failures, blind verdict, reviewer consent reference, reviewer eligibility attestation, and post-review blinding confirmation;
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
- provide one blind verdict only after satisfying the independent-reviewer eligibility screen;
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
- a clear separation between profile-derived mechanism checks and profile-independent public outcomes;
- reproduction and independent-review instructions.

Profile-derived rubric adherence may appear only as labelled mechanism-validation evidence. It cannot be headlined, ranked, or presented as a standalone Ditto win.

The proof media set contains:

1. a work/done clip showing scope, verification, and evidence;
2. a design clip showing the structural before/after and rendered verification;
3. a writing clip showing grounded voice and constraint adherence;
4. a short combined hero clip that links to the full evidence package.

Clips may simplify presentation but may not hide losses, splice outputs into a fictional run, or introduce metrics absent from the published evidence.

## 17. Claim and ship gates

No public benchmark claim is drafted as a conclusion until the complete sanitized evidence package passes review. Allowed language must match the observed scope, such as "In this frozen paired benchmark..." rather than universal claims.

Publication requires all of the following:

- all 48 Ditto Proof v1 cells are complete, or the result is explicitly labelled as an incomplete non-v1 pilot edition;
- validators and the existing Ditto test suite pass;
- private-data review passes;
- exclusions and limitations are included;
- all claimed numbers recalculate from published sanitized records;
- Ohad reviews the evidence and explicitly approves shipping;
- the benchmark receives a separate GitHub release from the plugin release.

If `+Ditto` does not show a supported advantage, the team publishes no inflated launch claim. The evidence becomes a product-improvement input.

## 18. Distribution handoff

Distribution and proof are one system. No channel fires until Section 17 passes and the sanitized evidence package has a stable public URL. Every claim token in every draft must resolve from the approved publication record; if a value is missing, invalid, neutral, mixed, or negative, the copy says so or the claim is removed.

This section is a plan and staging contract only. It authorizes research and local preparation, not posting, scheduling, outreach, dashboard changes, or launch execution. A later approval must identify the exact final artifacts and actions to fire.

### 18.1 Fixed operator constraints and ownership rule

- **Hacker News:** Ohad's account is flagged or effectively banned. Planned HN reach, visits, and stars are all `0`. Ditto never auto-submits. HN becomes observable bonus traffic only if an unaffiliated third party submits organically.
- **Reddit:** prior spam friction and a promotional-spam warning are hard constraints. Use two native posts at most, one subreddit at a time, seven days apart, with different titles and bodies. Never cross-post identical copy, auto-post, comment-bump, mass-DM, or ask for coordinated votes.
- **X:** use number-first posts led by the already verified mining scale (`1,656 sessions`, `9 months`, `approximately 3M tokens`) plus the proof clip. Scheduling automation is eligible only through an authenticated, explicitly approved X-native or API path and only after Ohad approves the rendered posts and times.
- **Product Hunt:** use one timed spike after proof is public. Ditto is self-hunted by Ohad; no reach is attributed to a famous hunter. The Product Hunt draft, assets, maker comment, links, and launch-day response sheet are staged before Ohad manually schedules or fires it.
- **YouTube:** use one durable, search-oriented two-condition proof video. Publishing time is chosen to give the other channels a stable proof URL, not because of an unsupported algorithm hack.
- **Agent ownership:** the agent owns research, copy, asset production, link validation, evidence substitution, calendars, local staging, preview screenshots, and approved X scheduling. Ohad performs the final manual action only where account trust, community rules, or ban risk make automation unsafe. The reason for each manual boundary is stated below.

### 18.2 Dated evidence ledger and bottom-up forecast

Research was refreshed on **2026-07-15**. Private provider evidence comes from GitHub Traffic API reads available to the repository owner; public mechanics and benchmarks are linked directly.

| Channel | Dated evidence | Reach / qualified-visit planning value | Star, install, or download conversion | Decision |
|---|---|---|---|---|
| Reddit | The first r/ClaudeSkills launch receipt records `102K` post views, `200` upvotes, and `32` comments in the [repository screenshot](../../../assets/reddit-proof.png). GitHub Traffic on 2026-07-15 reported `260` Reddit unique referrers plus `117` `com.reddit.frontpage` uniques for the launch window; those groups can overlap and are not attributable exclusively to one post. | **Unknown forecast.** The 102K post is a single observed breakout, not a repeatable reach estimate. The only honest reference is the observed 102K post views and 260-377 non-deduplicated Reddit-origin GitHub uniques across the launch window. | **Unknown.** GitHub does not attribute stars to a referring post, and the two Reddit referrer rows can overlap. | Keep Reddit because it has the strongest observed channel signal, but use two spaced native posts and no automation. |
| X | The public [@BiosRiosz profile](https://x.com/BiosRiosz) showed `47` followers on 2026-07-15. GitHub Traffic reported `24` `t.co` unique referrers in the launch window. X impressions were not available. | **Unknown forecast.** Neither follower count nor 24 historical referrals proves future impressions. | **Unknown.** No impression export or channel-attributed star data is available. | Schedule a short evidence series because X's native scheduler is supported, but assign no traffic or star target. |
| YouTube | The existing [8:27 Ditto walkthrough](https://www.youtube.com/watch?v=Ic8jAx_2RWk) had `82` views, `4` likes, and `2` comments; the channel had `61` subscribers when read on 2026-07-15. GitHub Traffic reported `55` YouTube unique referrers in the launch window. | **Unknown forecast.** `82` views is the observed baseline for the current video, not a floor for the proof video. | **Unknown.** The YouTube view snapshot and GitHub referrer window use different entities and cutoffs, so `55 / 82` must not be published as a conversion rate. | Make YouTube the evergreen evidence carrier and measure the new video's own impressions, CTR, retention, and outbound clicks after publication. |
| Product Hunt | Product Hunt's [official posting guide](https://help.producthunt.com/en/articles/479557-how-to-post-a-product) says launches start at 12:01 a.m. platform time, a first comment should open the discussion, makers can self-hunt, hunter followers do not receive email, and maker followers are notified only if the launch reaches the homepage. Public 2026 founder receipts report about [20 visitors at #64](https://www.reddit.com/r/ProductHunters/comments/1uehbaw/we_ranked_64_on_product_hunt_and_got_0_signups/), [369 visitors at #10](https://www.reddit.com/r/SideProject/comments/1uadf33/i_ranked_10_on_product_hunt_with_a_solo_chrome/), and [638 visitors at #2](https://www.reddit.com/r/ProductHuntLaunches/comments/1upmr2s/we_hit_2_on_product_hunt_yesterday_here_is_what/). A live third-party census reported `586` featured versus `20,771` unfeatured launches in the prior 30 days on [Product Hunt Pulse](https://hunted.space/product-hunt-pulse). | **20-638 qualified site visits is a scenario band, not a Ditto forecast.** Position, featuring, audience, and product fit dominate the result; an unfeatured launch may sit near the low end or below it. | **Unknown for GitHub stars/downloads.** The cited cases measure visitors, signups, or installs for different products. Their conversion rates do not transfer to Ditto. | Run one proof-backed launch only. Record actual Product Hunt referrer visits and outcomes without projecting rank. |
| Hacker News | Human operator receipt: the account is flagged/effectively banned. GitHub Traffic showed `1` HN unique referrer in the prior launch window, but no approved submission produced it. | **0 planned.** | **0 planned.** | No submission, automation, or projection. Respond once only if a third party submits organically. |

Marketplace and package counters are a separate evidence class from channel reach:

- The public [ClawHub API receipt](https://clawhub.ai/api/v1/skills/ditto-profile) returned `42` cumulative downloads, `0` installs, `1` ClawHub star, and a clean moderation verdict on 2026-07-15. The earlier `41` was a real value of that counter before it incremented, but the API exposes no unique-person or successful-use denominator. Report it only as **42 ClawHub download requests**, never as 42 users or installations.
- The official [PyPI project record](https://pypi.org/pypi/ditto-cli/json) still returned `0.3.6` while the public [GitHub release](https://github.com/ohad6k/ditto/releases/tag/v0.3.8) was `v0.3.8`. PyPI's project JSON reports download fields as `-1`, so it does not validate a download total. The tagged `v0.3.8` `server.json` also deliberately points the MCP Registry package record at `ditto-cli==0.3.6`. The repository has test and scanner workflows but no PyPI publish workflow, repository publishing secret, or local publishing-credential indicator. This version drift must be resolved or named explicitly before any copy implies that every install surface serves the current release.
- GitHub Traffic reported `965` clones from `371` unique cloners over its 14-day window. Those are Git clone events, not GitHub release downloads, package installs, active users, or retained users. The repository had `179` stars at the same audit point, with `15` timestamped stars in the preceding 24 hours; that is an observed baseline, not a channel forecast.

There is **no aggregate visitor or star forecast**. Product Hunt is the only channel with a sourced prospective visit scenario, and the other channels remain unknown; summing one scenario with unknowns would create fake precision. The former `17%` repository-wide visitor-to-star ratio and `4,900` visitor line are removed because repository-wide uniques mix channels, repeat exposure, and self-selected launch traffic while GitHub does not attribute stars to referrers.

Before execution, each channel receives a measurement receipt with: publication timestamp; exact URL; platform impressions/views; platform engagements; GitHub referrer uniques; site proof-page uniques when available; clones; release-asset downloads when available; Discord joins when attributable; and the repository star delta during the window labelled **temporal, not causal**. If the platform or provider does not expose a field, it remains `unknown`.

### 18.3 Evidence substitution and asset staging contract

The agent creates one local, non-public, gitignored staging root outside both the repository and the private benchmark run root, ending in `distribution/ditto-proof-v1-2026-08/`. It contains:

- `evidence.json`: the approved public aggregate record and its SHA-256;
- `claims.json`: exact permitted substitutions for `{VALID_BLIND_PAIRS}`, `{DITTO_WINS}`, `{COLD_WINS}`, `{TIES}`, `{DITTO_HARD_FAILURES}`, `{COLD_HARD_FAILURES}`, `{INVALIDATIONS}`, `{DITTO_REF}`, `{EVIDENCE_URL}`, and `{VIDEO_URL}`;
- `release-surfaces.json`: point-in-time versions and clean-install receipts for GitHub release/tag, native plugin manifests, the skills bootstrap, PyPI, MCP Registry, Glama, ClawHub, and every install command used in public copy;
- `x/`: rendered 280-character posts, the short proof clip, captions, schedule screenshot, and link check;
- `reddit/`: separate r/ClaudeSkills and r/ClaudeAI Markdown drafts, rule snapshots, flairs, preview screenshots, and a no-duplicate-copy diff;
- `youtube/`: final video, thumbnail, title, description, chapters, captions, transcript, end-screen plan, and checksum manifest;
- `product-hunt/`: icon, gallery assets, video URL, product copy, maker comment, topics, pricing state, launch checklist, response sheet, and preview screenshots;
- `github/`: benchmark release notes, README proof block, website proof block, and link map;
- `measurements/`: empty per-channel receipt templates filled only from observed provider data after firing.

The brace-delimited values above are immutable evidence substitutions, not authoring placeholders. Every text artifact fails staging if it contains an unresolved claim token, unsupported number, hidden private path, profile text, receipt text, universal claim, significance language, fake testimonial, or result not present in `evidence.json`. Asset checks validate sizes, duration, captions, links, alt text, and SHA-256. The existing talking-head video can be linked as background, but it cannot substitute for the new two-condition proof video.

### 18.4 GitHub proof hub

GitHub is the conversion and inspection surface, not a traffic forecast.

**Agent executes after a separate repository-change approval:** prepare the benchmark release branch, release notes, README proof block, static evidence pages, checksums, and link verification. **Ohad manually fires:** merge the approved PR and publish the separate benchmark GitHub release because those are public repository actions. The agent may execute them only if Ohad later gives exact publish authorization.

The proof hub must be live before any distribution item. It opens with the frozen comparison question, raw win/tie/loss denominators, hard failures, exclusions, and `small-n, directional only`; every clip and post links to the same evidence URL.

The benchmark may remain frozen at `v0.3.7` while the product advances, but every public install path must name what it actually serves. Before staging, the agent records the current GitHub, plugin, PyPI, registry, and marketplace versions and runs the exact public install commands in clean temporary homes. A mismatch is allowed only when the copy states it precisely and the intended path still passes; otherwise distribution stops. No channel may use `latest`, `current`, or `v0.3.8` as interchangeable labels while PyPI still resolves `0.3.6`.

PyPI alignment is a separate approved release action, not an implied consequence of the GitHub tag. The recommended durable route is a SHA-pinned GitHub Actions publish workflow plus [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/adding-a-publisher/) scoped to `ohad6k/ditto`, the exact workflow filename, and a protected publishing environment. That route requires both a reviewed repository change and a human PyPI dashboard receipt. A one-off local upload is an explicit fallback only; credentials stay in the local keyring/environment or an interactive provider prompt and are never pasted into chat, committed, logged, or written into the staging package. After either route, the agent verifies the public PyPI JSON, exact wheel/sdist hashes, a clean pinned `uvx --from ditto-cli==0.3.8 ditto-cli mcp` initialization whose `serverInfo.version` is `0.3.8`, and updated `server.json` before distribution can claim alignment.

### 18.5 Reddit: two manual, native posts

**Mechanics and safety evidence.** Reddit's [spam guidance](https://support.reddithelp.com/hc/en-us/articles/360043504051-Spam) says to post authentic content in communities where the user has a personal interest, be thoughtful when contributions primarily link to a business, and follow community-specific rules. The current [r/ClaudeSkills rules](https://www.reddit.com/r/ClaudeSkills/about/rules.json) require relevant detail, a repository/download link for self-made skills, free/open-source disclosure, flair, and explicitly forbid posting the same thing across many subreddits. The current [r/ClaudeAI rules](https://www.reddit.com/r/ClaudeAI/about/rules.json) allow maker showcases only with minimal promotion, a free-to-try product, and OP karma above 50; they also ban vote manipulation and require sourced comparative benchmarks. [r/ChatGPTCoding](https://www.reddit.com/r/ChatGPTCoding/about/rules.json) restricts self-promotion to a designated thread or sponsorship/modmail, so it receives no planned feed post without written moderator approval.

**Ownership.** The agent researches rules on the day of posting, rewrites and stages the native draft, validates every claim, selects the correct flair, and may fill an authenticated composer without submitting after exact approval. **Ohad must read the preview and click Post manually** because the account already has spam friction and community-specific judgment cannot be delegated safely. The agent does not auto-comment. Ohad answers genuine replies; the agent may draft replies from the actual thread. No comment is added merely to resurface the post.

**r/ClaudeSkills draft, confession format.** Fire only if the current rules still permit it and at least seven days have passed since any Ditto promotion there.

Title:

```text
I thought my agents needed better prompts. The embarrassing part was that I had already written 3M tokens of the answer.
```

Body:

```text
I kept trying to explain the same things to coding agents: what done means, what UI I reject, when I need live proof, and how I write when I am not trying to sound polished.

Then I counted the history I was ignoring: 1,656 sessions across 9 months, roughly 3M tokens of prompts I had already typed.

I built Ditto to mine only my messages from those local sessions and turn repeated, evidenced patterns into a profile the agent loads before work. It is free and open source.

The first launch post did well, but that was not proof the profile improved the work. So I froze Ditto at {DITTO_REF} and ran the same systems cold and with Ditto across {VALID_BLIND_PAIRS} valid blind pairs.

Blind result: Ditto {DITTO_WINS}, cold {COLD_WINS}, ties {TIES}.
Hard failures: Ditto {DITTO_HARD_FAILURES}, cold {COLD_HARD_FAILURES}.
Invalid or excluded comparisons: {INVALIDATIONS}.

This is small-n and only measures a clean-host cold start. The tasks, outputs, hashes, losses, and limitations are here: {EVIDENCE_URL}

Repo: https://github.com/ohad6k/ditto

The part I would genuinely like feedback on: is the evidence package enough for you to trust the comparison, or is there a control I missed?
```

Required asset: one native image or short clip showing the cold and Ditto outputs beside the exact evidence-record ID, plus alt text. Flair: `Skill Share` unless the live rule list changes.

**r/ClaudeAI draft, evidence-first and non-duplicative.** Fire seven days later only if the account's visible karma exceeds the current threshold, no new spam warning exists, the live rules still allow it, and the r/ClaudeSkills post did not trigger moderation friction.

Title:

```text
I tested the same coding agents cold vs with a mined working profile across {VALID_BLIND_PAIRS} valid blind pairs
```

Body:

```text
I use Claude Code and Codex every day, and I realized my local history already contained the working rules I kept re-explaining.

I mined only the messages I typed from 1,656 sessions, then froze the resulting Ditto profile and compared the same complete systems under two conditions: clean-host cold start and the same host with Ditto loaded.

The public result was {DITTO_WINS} Ditto preferences, {COLD_WINS} cold preferences, and {TIES} ties across {VALID_BLIND_PAIRS} valid blind pairs. Hard failures were {DITTO_HARD_FAILURES} with Ditto and {COLD_HARD_FAILURES} cold.

Important limits: this is small-n, directional only, not a model ranking, and not Ditto versus another personalization product. Writing preference is omitted wherever voice made blinding invalid. Every exclusion stays visible.

The full tasks, outputs, hashes, scoring rules, and limitations are here: {EVIDENCE_URL}

Ditto is free and open source: https://github.com/ohad6k/ditto

I am posting the evidence because comparative claims should be inspectable. If you see a control failure, I would rather fix the benchmark than defend the result.
```

Required asset: the combined proof clip with captions and the evidence URL visible in the last frame. No vote request, repost request, star request, urgency language, or repeated title/body from r/ClaudeSkills.

### 18.6 X: approved number-first scheduled series

**Mechanics and evidence.** X's [official recommendation description](https://help.x.com/en/rules-and-policies/recommendations) says For You recommendations can reach non-followers and use many interaction, network, interest, and media signals without one statically dominant signal. X's [official posting guide](https://help.x.com/en/using-x/how-to-post) supports 280-character posts, video, drafts, and native scheduling. These mechanics justify short video-backed posts and safe scheduling; they do not justify a reach forecast.

**Ownership.** The agent renders the final posts, validates 280-character limits and evidence substitutions, attaches the approved clip, and **executes native X scheduling only after Ohad approves the exact previews and an authenticated scheduling path is verified**. If that path is unavailable, the status changes to `manual-required`; the agent does not improvise credentials or a third-party bot.

Post 1, scale plus test:

```text
1,656 sessions. 9 months. About 3M tokens of my own prompts.

I turned that history into a working profile, then tested the same agents cold vs with Ditto across {VALID_BLIND_PAIRS} valid blind pairs.

Result: {DITTO_WINS}-{COLD_WINS}-{TIES}.

Proof: {EVIDENCE_URL}
```

Attach: 20-35 second combined clip. If the resolved post exceeds 280 characters, put the proof URL in the first reply scheduled one minute later; never delete limitations to make it fit.

Post 2, failures:

```text
The useful Ditto benchmark number was not speed. It was hard failures.

Cold: {COLD_HARD_FAILURES}
With Ditto: {DITTO_HARD_FAILURES}

Same systems, tasks, tools, budgets, and clean homes. Small-n, directional only.

Every output and exclusion: {EVIDENCE_URL}
```

Attach: work/done proof clip with the exact cell IDs.

Post 3, limits:

```text
What the Ditto benchmark does not prove:

It is not a model ranking.
It is not statistical significance.
It is not Ditto vs another memory product.

It is one frozen clean-host comparison with inspectable receipts.

Method and losses: {EVIDENCE_URL}
```

Attach: static limitations card sourced from the publication record.

Post 4, durable demo:

```text
Cold agent. Same task with 1,656 sessions of working context behind it.

No highlight reel. The video shows both outputs, the hard failures, and where Ditto still lost.

Full two-condition demo: {VIDEO_URL}
Evidence: {EVIDENCE_URL}
```

Attach: native 20-35 second trailer for the YouTube proof video.

### 18.7 YouTube: evergreen two-condition proof carrier

**Mechanics and evidence.** YouTube's [official recommendation guide](https://support.google.com/youtube/answer/16533387?hl=en) says recommendations follow viewer personalization and content performance, including whether viewers click, continue watching, and report satisfaction. It explicitly says long-term performance is not known to depend on publish time and recommends quality over frequency. Therefore this plan optimizes the title, thumbnail, opening, retention, chapters, captions, and evidence trail, not a magic posting hour.

**Ownership.** The agent writes the script, creates the edit decision list, produces captions, stages the final file and thumbnail, validates links and claims, and prepares the upload metadata. **Ohad manually clicks Publish** because the YouTube account is identity-bound and no approved publishing automation exists. The agent may fill an authenticated upload form without publishing only after a later explicit staging approval.

Title:

```text
I tested AI agents cold vs with 1,656 sessions of context
```

Thumbnail: split-screen `COLD` / `DITTO`, one identical task between them, and a small `24 paired comparisons` label only if all 24 pairs are valid. Do not use `INSANE`, a fake reaction face, or a result number that the evidence record does not support.

Opening 20 seconds:

```text
I had 1,656 coding-agent sessions and kept explaining the same rules anyway. So I froze one profile from that history and ran the same agents twice: cold, and with Ditto. This video shows both outputs, the failures, and the parts Ditto did not win. Every result links to the raw sanitized evidence.
```

Video structure:

1. `0:00` the repeated-context failure and frozen question;
2. `0:20` controls: same system, fixture, tools, budgets, fresh homes;
3. `1:10` work/done cold versus Ditto, including verification receipts;
4. `2:40` design cold versus Ditto, including rendered artifacts;
5. `4:10` writing, including why some voice preference is not blind-valid;
6. `5:20` raw `{DITTO_WINS}-{COLD_WINS}-{TIES}` and hard failures;
7. `6:10` invalidations, losses, and small-n limits;
8. `7:00` how to inspect/reproduce the evidence and try Ditto locally.

Description:

```text
I compared the same coding-agent systems under two frozen conditions: clean-host cold start and the same setup with a Ditto profile mined from 1,656 sessions, 9 months, and approximately 3M tokens of my own prompts.

Valid blind preference: Ditto {DITTO_WINS}, cold {COLD_WINS}, ties {TIES} across {VALID_BLIND_PAIRS} pairs.
Hard failures: Ditto {DITTO_HARD_FAILURES}, cold {COLD_HARD_FAILURES}.
Invalidations/exclusions: {INVALIDATIONS}.

This is small-n, directional only. It is a complete-system comparison, not a model ranking or a universal claim.

Evidence, tasks, outputs, hashes, and limitations: {EVIDENCE_URL}
Open-source repo: https://github.com/ohad6k/ditto
```

Required assets: final 16:9 video; 1280x720 thumbnail; embedded and uploaded captions; clean transcript; chapters; evidence URL in description, pinned comment, and final frame; one 20-35 second trailer; three family clips; and a local checksum manifest. The pinned comment repeats the limitations and asks for control/evidence feedback, not stars.

### 18.8 Product Hunt: one proof-backed timed spike

**Mechanics and collision risk.** The official Product Hunt guide sets the image sizes, YouTube-only gallery video, first-comment expectation, 260-character description, scheduling flow, and self-hunt mechanics. Live search on 2026-07-15 found multiple unrelated products already named Ditto, including an established product-copy tool. The draft must use the disambiguated product name **Ditto for AI Agents**, verify the final slug and trademark/confusion risk, and link directly to the correct proof landing page.

**Ownership.** The agent prepares every local asset, fills the Product Hunt draft and captures previews after a later staging approval, validates the final platform-displayed launch time, and runs the response checklist from observed comments. **Ohad manually clicks Schedule/Launch** because Product Hunt is an account-bound community action and accidental duplicate/collision submission is costly. Ohad is both hunter and maker; no external hunter traffic is assumed.

Product name:

```text
Ditto for AI Agents
```

Tagline:

```text
Turn your coding-agent history into working rules your agents load first
```

Description, maximum 260 characters:

```text
Ditto mines only the prompts you typed in supported local coding-agent logs, then turns repeated, evidenced patterns into a private profile. The Proof v1 launch includes frozen cold-vs-Ditto tasks, outputs, failures, hashes, and limitations.
```

Maker first comment:

```text
I built Ditto because I kept correcting agents in ways I had already written hundreds of times.

My history was 1,656 sessions across 9 months, roughly 3M tokens of my own prompts. Ditto mines only the human-authored text locally, redacts it, and builds an evidence-backed working profile the agent can load before a task.

I did not want to launch the benchmark as a victory graphic. Proof v1 freezes the systems, tasks, tools, budgets, homes, profile, and Ditto ref. The public package includes the cold and Ditto outputs, blind results, hard failures, invalidations, hashes, and the controls we could not satisfy.

Result: Ditto {DITTO_WINS}, cold {COLD_WINS}, ties {TIES} across {VALID_BLIND_PAIRS} valid blind pairs. Hard failures were {DITTO_HARD_FAILURES} with Ditto and {COLD_HARD_FAILURES} cold.

It is small-n and directional only. I would value scrutiny of the evidence and controls more than a launch-day compliment: {EVIDENCE_URL}
```

Launch checklist:

- [ ] proof URL, GitHub benchmark release, and YouTube video are live and cross-linked;
- [ ] name/slug collision check passes for `Ditto for AI Agents`;
- [ ] Ohad's personal Product Hunt account has completed onboarding and is added as hunter/maker;
- [ ] pricing is `Free` unless a verified paid plan exists by launch day;
- [ ] 240x240 icon is legible at small size and under the platform limit;
- [ ] at least two 1270x760 gallery images show mechanism, paired proof, limitations, and install path;
- [ ] full public YouTube URL loads and is not private;
- [ ] description is at most 260 characters and every number resolves from `claims.json`;
- [ ] every displayed install command resolves to the intended release and has a clean smoke receipt in `release-surfaces.json`; the GitHub `v0.3.8` / PyPI `0.3.6` drift is resolved or disclosed before approval;
- [ ] first comment, FAQ replies, privacy answer, prior-art answer, and negative-result answer are staged;
- [ ] audience mobilization is limited to the approved X/YouTube/Reddit sequence and one evidence-first notice to the existing Discord; no unsolicited DM, vote request, coordinated upvote, or promised endorsement is used;
- [ ] the Discord link remains valid through the `+7 days` measurement window. The invite linked from live `main` returned Discord `Unknown Invite` / HTTP `404` on 2026-07-15; the older worktree invite was also unavailable. Ohad must manually create or select a durable invite after separate approval using Discord's [Edit Invite Link](https://support.discord.com/hc/en-us/articles/208866998-Invites-101) controls with no expiry and no use limit, or Discord is removed from the launch. The agent validates and stages the link but does not create or send invites autonomously;
- [ ] launch date/time is verified in the Product Hunt dashboard and captured in the approval receipt;
- [ ] no hunter-email, rank, homepage, traffic, upvote, signup, or star projection appears in copy;
- [ ] launch-day owner sheet covers moderation, support, real replies, evidence corrections, and stop conditions;
- [ ] Ohad reviews the final preview and performs the single manual Schedule/Launch action.

### 18.9 Hacker News: zero planned traffic, organic-response only

There is no HN submission draft, launch slot, automated action, or traffic estimate. The agent may monitor GitHub referrers after launch without touching HN. If an unaffiliated third party creates a thread, the agent stages one factual maintainer disclosure and Ohad may post it manually once; neither adds bump comments.

Maintainer response draft for an organic thread:

```text
Maintainer here. The narrow claim is a frozen clean-host comparison, not a model ranking. The public package includes both conditions, losses, invalidations, hard failures, task fixtures, and hashes: {EVIDENCE_URL}. Ditto is local-first and open source. I am happy to answer questions about the controls or privacy boundary.
```

Any organic HN visits are reported after the fact as third-party traffic, never as planned or caused by this launch workstream.

### 18.10 Conditional dated calendar

The first eligible launch window is **2026-08-10 through 2026-08-19**. It is not a benchmark deadline. At **2026-08-07 12:00 Asia/Jerusalem**, if Section 17 has not passed or any final artifact lacks approval, every item becomes `not-fired` and the whole calendar rolls to the next Tuesday-based window. No partial launch leaks before the proof hub is ready.

| Date and time, Asia/Jerusalem | Action | Owner | Fire rule |
|---|---|---|---|
| 2026-08-10 14:00 | Publish GitHub proof hub and separate benchmark release | Ohad manual publish; agent stages and verifies | Section 17 plus exact repository publish approval |
| 2026-08-10 16:00 | Publish YouTube two-condition proof video | Ohad manual Publish; agent stages upload | Proof URL live; final video/metadata approved |
| 2026-08-10 18:00 | X Post 1 with combined native clip | Agent schedules through approved X path | Authenticated scheduler verified; exact preview approved |
| 2026-08-11 10:01 target | Product Hunt launch at the platform's 12:01 a.m. day boundary | Ohad manual Schedule/Launch; agent fills and verifies draft | Dashboard confirms exact displayed time and collision-free draft |
| 2026-08-11 15:00 | X Post 2 with work/done hard-failure clip | Agent schedules | Post 1 live without claim correction |
| 2026-08-12 18:30 | r/ClaudeSkills confession post | Ohad manual Post; agent fills reviewed composer | Live rules pass; seven-day spacing; no moderation friction |
| 2026-08-13 17:00 | X Post 3 limitations card | Agent schedules | Evidence/limits unchanged |
| 2026-08-18 17:00 | X Post 4 linking full YouTube proof | Agent schedules | Video public; analytics receipt captured |
| 2026-08-19 18:30 | r/ClaudeAI evidence post | Ohad manual Post; agent fills reviewed composer | Karma/rules pass; no Reddit warning or removal; body is non-duplicate |

Product Hunt's dashboard is authoritative for its launch boundary. The `10:01` target assumes Pacific daylight time relative to Israel; the agent must replace it with the exact dashboard-confirmed Israel time in the final approval receipt. YouTube's date is ordered before Product Hunt to create a stable gallery/evidence URL, not to claim a recommendation advantage.

### 18.11 Measurement, corrections, and stop rules

The agent captures provider receipts at `+1 hour`, `+24 hours`, `+72 hours`, and `+7 days` for every fired channel that exposes them. Reports keep raw denominators and distinguish platform views, GitHub unique referrals, site visits, clones, downloads, Discord joins, and star delta. No star delta is attributed to one channel when windows overlap.

Stop the remaining sequence and ask for review when any of these occurs:

- a benchmark number or evidence URL changes after staging;
- a privacy, canary, or broken-link failure appears;
- Reddit removes a post, sends a warning, or live rules conflict with the draft;
- X scheduling uses an unapproved client or the rendered post differs from the preview;
- Product Hunt detects a duplicate/collision, wrong product, wrong date, or incomplete maker state;
- YouTube publishes the wrong visibility, captions, thumbnail, or evidence URL;
- an install command resolves a different release than the approved copy, or any required marketplace/package surface fails its clean smoke;
- the Discord invite is expired, expiring inside the measurement window, or replaced without link validation;
- a post attracts a substantive methodological correction that changes the claim;
- any platform action would require credentials, vote coordination, unsolicited bulk messaging, or ban-evasion behavior.

No more bulk awesome-list pull requests are part of this milestone. Existing high-value submissions are maintained only when maintainers respond, with one factual reply and no promotional bump. Existing creator email threads may receive at most one evidence-linked follow-up after the ship gate if the recipient previously engaged or the thread is still contextually active; no traffic is projected and no new bulk list is created.

The 2026-07-15 submission audit found `22` open Ditto listing PRs and two merged external listings. It produced no new human-maintainer request requiring a reply:

- [agentic-awesome-skills #842](https://github.com/sickn33/agentic-awesome-skills/pull/842) has all four checks passing, both Codex review threads resolved, and a final review reporting no major issue. Its remaining blocked state is maintainer review, so no further comment is staged.
- [awesome-copilot #2296](https://github.com/github/awesome-copilot/issues/2296) now has both intake gates passing and the `ready-for-review` label. The separate contributor-reputation flag reports `Credential audit: NONE`; it is a maintainer trust review, not a failed Ditto install. Do not rerun or comment again without a maintainer request.
- [awesome-mcp-servers #10103](https://github.com/punkpeye/awesome-mcp-servers/pull/10103) is clean after the Glama/introspection receipt already posted. It waits without another bump.
- [awesome-agent-skills #348](https://github.com/heilcheng/awesome-agent-skills/pull/348) has a Vercel deployment authorization failure tied to the maintainer's team. The agent must not authorize, request access to, or repeatedly comment on another maintainer's deployment surface.

The agent checks this inventory read-only for new human requests. A bot summary, ranking delay, `review required`, or maintainer-side deployment gate does not by itself justify a follow-up.

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
