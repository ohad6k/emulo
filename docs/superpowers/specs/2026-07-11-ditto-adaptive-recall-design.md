# Ditto Adaptive Recall Design

Date: 2026-07-11

Status: approved architecture, pending written-spec review

## Objective

Replace Ditto's failed random bounded-sampling pipeline with an adaptive, high-recall mining pipeline that preserves the quality of a deep personal profile while remaining honest and controllable about model cost.

The first useful profile must recover important work laws, design taste, and writing voice from real user-authored local session history. Installation itself remains zero-call. Mining may spend more than the former 160K-token ceiling, but every immutable stage must disclose its exact selected source tokens, cache reuse, worker calls, and reducer calls before model work starts.

Benchmark execution and launch-video production are not part of this design or its release path.

## Evidence Behind The Redesign

The frozen Ohad calibration used 22 private must-recover requirements: 10 work, 5 design, and 7 writing requirements. The checklist was frozen before candidate output and was not changed.

The old ladder produced these results:

| Candidate | Selected tokens | Validated evidence items | Frozen recovery |
| --- | ---: | ---: | --- |
| 0 | 70,902 | 20 | work 2/10, design 0/5, write 0/7 |
| 1 | 116,387 | 35 | work 2/10, design 0/5, write 2/7 |
| 2 | 147,277 | 41 | work 0/10, design 0/5, write 0/7 |

Candidate 2's evidence covered 25 work sessions, 11 design sessions, and 11 writing sessions. The final reducer still installed only one unrelated work rule and deactivated design and writing. Therefore the failure was not only insufficient source text. Recall was lost at four boundaries:

1. Random source/time sampling had no way to prioritize rare but forceful corrections, rejections, or preferences.
2. A global 12-item report ceiling made work, design, and writing compete inside every worker report.
3. One reducer had to cluster all domains, resolve contextual contradictions, author files, and satisfy a strict pack schema in one pass.
4. Cost approval happened before the corpus was frozen, allowing live-session churn to change cache keys and increase the disclosed call count.

The new design fixes those boundaries rather than increasing the old random candidate count.

## Product Contract

### Installation

Native plugin installation and the bounded `npx skills add ohad6k/ditto@ditto` bootstrap continue to scan no logs and schedule zero mining calls.

### First setup

`run ditto` performs local extraction and planning first. Before any model pass, the user sees:

- valid session count;
- post-dedupe source tokens;
- immutable selected receipt tokens;
- packet count and per-packet token totals;
- cache hits;
- planned scout calls;
- planned work, design, and writing reducer calls;
- the separate next adaptive stage and full-history option;
- a statement that no model work has started.

The displayed run is immutable. Approval starts exactly that run. If the user does not approve, the private frozen plan may be deleted without activating a profile.

### Adaptive expansion

Stage A is the default high-recall plan. It selects at most 300K source tokens into six packets of at most 50K tokens, followed by one reducer per domain. Its maximum is nine model calls: six fast scouts and three strong domain reducers.

If Stage A is objectively weak, Ditto prepares the next immutable stage from the same frozen corpus and displays only the additional cost. It does not silently expand. A later stage reuses every validated receipt and reducer artifact that remains content-addressable.

Full-history mining remains a separately planned final fallback. It is never started automatically and never described as cheap.

### Completion

Ditto may activate a structurally valid partial profile for an ordinary user only when every active rule has valid evidence and inactive domains have exact deepen instructions. The flagship release gate is stricter: the unchanged private calibration must recover all 22 requirements and pass one fresh work, design, and writing probe through the installed development plugin.

If the flagship gate fails after an approved adaptive stage, the release remains stopped. The checklist is never weakened and missing behavior is never relabeled as success.

## Architecture

### 1. Immutable corpus freeze

The flow changes from approval-before-prepare to prepare-before-approval:

1. `plugin preflight` remains a read-only estimate.
2. `plugin prepare` performs local extraction, redaction, receipt indexing, packet construction, and immutable private writes under `DITTO_HOME` without model calls.
3. The agent displays the exact prepared plan and asks for approval.
4. Workers and reducers use only the prepared run paths.

The frozen run stores content hashes for every selected receipt and packet. Subsequent user messages cannot change its cost or invalidate its cache keys. Adaptive stages reference the same corpus snapshot instead of rescanning live logs.

Raw source paths never appear in public output. Existing stable hashed session IDs remain the only session identity exposed to reports.

### 2. Receipt ledger

Local Python converts redacted user messages into immutable receipts before selection. A receipt contains:

- stable receipt ID;
- stable session ID;
- source and exact date;
- redacted user text;
- source-token estimate;
- content hash;
- deterministic salience features;
- zero or more domain hints.

Receipts are the smallest selection unit. Sessions remain available as a grouping and corroboration boundary, but one large session can no longer become entirely ineligible because it exceeds a packet target.

The ledger stays stdlib-only and private. Its schema version participates in every downstream cache key.

### 3. Deterministic salience index

The local index scores every receipt across the full deduplicated corpus. It does not attempt to write personality rules. It only prioritizes which real receipts deserve model attention.

The score combines versioned feature families:

- explicit directives and prohibitions;
- user corrections of previous agent output;
- acceptance and rejection language;
- stated preferences and comparisons;
- completion, verification, launch, and failure language;
- design, UI, visual-reference, copy, marketing, and social-writing hints;
- repeated normalized phrases or shingles across distinct sessions;
- recurrence across source and time strata;
- unusually forceful formatting or repetition;
- adjacency to a user-requested revision after an unsatisfactory result.

Language-neutral structural signals are primary. Small English and Hebrew vocabularies may improve routing, but no receipt is discarded solely because it lacks a known keyword.

Domain hints are non-exclusive. One receipt may enter multiple domain candidate pools. Unknown receipts remain eligible through the general preference and recurrence pools.

### 4. Salience lanes and packet construction

Stage A constructs three private lanes: work, design, and writing. Each lane combines:

- high-salience explicit receipts;
- representative receipts from repeated cross-session clusters;
- corrections and rejections;
- time/source-stratified reserve receipts;
- a deterministic exploration reserve for signals the heuristic classifier could not confidently route.

Selection is deterministic for a frozen ledger. It is not random and it is not top-heavy. Receipts are round-robined across domain, source, time stratum, and signal family.

Stage A uses six packets of at most 50K source tokens, capped at 300K total. Packet composition reserves meaningful capacity for all three domains. Work may not consume design or writing capacity. Identical receipt text is deduplicated, while distinct dated receipts supporting recurrence remain separate.

The packet manifest records selected and skipped receipt counts by domain hint and signal family without exposing private text.

### 5. High-recall scout reports

One fast scout reads each packet completely. A scout covers all domains but receives independent output budgets:

- at most 12 work evidence items;
- at most 12 design evidence items;
- at most 12 writing evidence items;
- at most 24,576 serialized bytes total;
- the existing 200-character receipt quote ceiling.

The report schema adds:

- `scope`: universal, contextual, platform-specific, product-specific, or uncertain;
- `signal_family`: directive, correction, rejection, preference, recurrence, or exploration;
- `context`: a short evidence-backed boundary when the instruction is not universal;
- exact receipt IDs in addition to session IDs.

Scouts do not merge rules across packets. They maximize recall, preserve contradictions, and label uncertainty. A valid no-signal result remains preferable to invented evidence.

Every scout runs the read-only report validator inside its own pass before returning. Python caches only validated reports.

### 6. Isolated domain reducers

The single global reducer is removed. Three strong reducers run independently:

- work reducer reads only work evidence;
- design reducer reads only design evidence;
- writing reducer reads only writing evidence.

Each reducer writes one bounded domain-draft JSON file, not Markdown and not a complete pack. A draft contains:

- active or inactive state;
- specific rules and operational implications;
- kind and confidence;
- evidence IDs and receipt IDs;
- scope and context;
- contradictions;
- discarded cluster IDs with machine-readable reasons;
- evidence coverage and novelty metrics.

An inferred rule still requires distinct-session corroboration. Cross-source/time support remains preferred, but lack of a second provider cannot erase a repeated rule from a user who primarily uses one host. The revised policy requires two distinct sessions and either two time strata or an explicit explanation that the available corpus is single-stratum. One unequivocal uncontradicted explicit instruction may survive with low-frequency confidence.

Contextual evidence cannot be promoted into a universal rule. Conflicting preferences remain scoped, are omitted, or trigger targeted expansion.

Each domain reducer validates its own draft inside the same pass. Reducer calls are independently cacheable by domain evidence-set hash.

### 7. Deterministic pack assembly

Python, not a fourth model, assembles the final pack from the three validated domain drafts and validated scout reports.

The assembler:

- writes exact profile frontmatter and filenames;
- renders each rule and implication once;
- builds the appendix from referenced exact receipts;
- computes distinct-session card counts;
- selects up to three validated work laws for the card;
- writes the draft manifest;
- validates every evidence reference and file hash;
- activates atomically only after the complete pack passes.

This removes schema authoring, file cleanup, and card arithmetic from the reducer's reasoning workload. It also eliminates the timeout pattern observed during candidate-2 reduction.

### 8. Adaptive stage controller

After assembly, Python computes non-semantic coverage signals without reading the private calibration checklist:

- active/inactive domains;
- rule and evidence counts per domain;
- explicit versus inferred balance;
- distinct sessions and time/source strata;
- unresolved contradiction count;
- evidence-cluster novelty relative to the prior stage;
- lane exhaustion and unprocessed high-salience tokens.

A weak or unstable domain produces a proposed next-stage plan. The plan adds the next highest-value unprocessed receipts for only the weak domains, reuses prior reports, and reruns only affected reducers. The user sees and approves the exact additional calls and tokens.

The flagship calibration compares the assembled profile to the frozen checklist outside the runtime selection algorithm. Checklist text is never supplied to scouts or reducers and therefore cannot seed the result.

## Cost And Model Policy

The architecture separates cheap recall work from expensive judgment:

- scouts use the fastest capable host model;
- domain reducers use the strongest available host model;
- deterministic Python performs validation and assembly;
- no model is invoked during installation, extraction, redaction, indexing, planning, cache lookup, or pack assembly.

Host adapters may map these roles to different models only when the host exposes an explicit supported model choice. Otherwise the skill describes fast versus strong roles without making an unsupported model claim.

Public cost output uses selected source tokens and actual/planned pass counts. It never converts subscription limits into percentages.

## Privacy And Safety

- Only real user-authored session messages are eligible.
- Known injected agent context, rules files, memory files, and typed self-descriptions remain banned as mining sources.
- Redaction runs before receipts, packets, or model-visible files are written.
- All receipts, reports, drafts, packs, and snapshots remain under `DITTO_HOME`.
- Public dogfood and changelog files contain hashes and counts only.
- Validators are read-only until explicit cache or activation commands run.
- Active profile replacement remains atomic and rollback-safe.
- Legacy and evidence-backed discovery paths remain mutually exclusive.

## Error Handling

- A prepared run whose packet or receipt hash changes is rejected; it is never silently rebuilt after approval.
- A scout or reducer must self-correct inside its approved pass until its read-only validator accepts the artifact.
- A host timeout leaves the previous active profile unchanged and preserves validated caches.
- Unsupported or contradictory domain evidence keeps that domain inactive and proposes targeted expansion.
- No report-set or domain-draft mismatch can activate a profile.
- If an adaptive stage exceeds its approved envelope, execution stops and displays a new plan.

## Test Strategy

### Local unit and property tests

- receipt IDs remain stable across repeated extraction;
- large sessions split into receipts without losing session identity;
- salience scoring is deterministic;
- rare explicit corrections survive among large volumes of low-signal text;
- repeated patterns require distinct sessions;
- work cannot consume reserved design or writing capacity;
- English, Hebrew, and mixed Unicode round-trip exactly;
- redaction happens before ledger and packet writes;
- frozen plans remain unchanged when live source files later change;
- adaptive stages reuse the original corpus snapshot;
- report and domain-draft validators are read-only;
- deterministic assembly produces exact files, hashes, receipts, and card counts;
- failure injection preserves the prior active pointer.

### Synthetic recall fixtures

Create large synthetic histories where each required behavior appears in a known difficult position: rare early receipt, rare late receipt, correction after failure, repeated cross-session preference, contextual contradiction, and multilingual instruction. Assert that salience selection and domain reduction recover the expected evidence without access to an answer checklist.

### Private flagship calibration

Use the unchanged checklist SHA-256 `9778cb1eb2fcdbd7aafed01600fc7a1ceaf59f99943d54b692b0aaff9efaab09`.

For each approved adaptive stage, record:

- selected tokens;
- cache reuse;
- planned and actual scout/reducer calls;
- per-domain recovery counts;
- active manifest hash;
- known gaps;
- whether fresh probes ran.

The first passing stage must recover work 10/10, design 5/5, and writing 7/7, then pass one fresh installed-plugin probe per domain. Checklist misses stop progression to release proof unless the next stage is separately approved.

## Release Sequence After Recall Passes

1. Lock the smallest passing adaptive stage as the public default.
2. Prove live native plugin activation, routing, cache reuse, updates, and mutually exclusive legacy migration.
3. Run separate read-only specification and code-quality reviews, fix findings, and re-review.
4. Prepare the plugin changelog and GitHub Release artifacts.
5. Stop at the explicit publication gate for push, tag, and public release approval.

Benchmark execution, leaderboard production, proof clips, and launch video remain deferred to a separate later release.

## Decisions

- Quality-first adaptive mining replaces the 160K random bounded ladder.
- Local salience selection operates across the full history, but models see only approved packets.
- Stage A is capped at 300K selected tokens and nine model calls.
- Work, design, and writing use independent evidence budgets and reducers.
- Python assembles the pack deterministically.
- Approval occurs after the run is frozen.
- Expansion is adaptive, cached, and separately approved.
- The 22-item flagship checklist remains unchanged and hidden from the mining models.
- Benchmark and launch-video work are excluded.

## Non-Goals

- No visual redesign.
- No benchmark model roster or benchmark execution.
- No launch-video production.
- No cloud account, API key, telemetry, or remote profile storage.
- No synthesis from AGENTS.md, CLAUDE.md, memory files, or questionnaires.
- No guarantee that a user with no design or writing history receives invented domain instructions.
