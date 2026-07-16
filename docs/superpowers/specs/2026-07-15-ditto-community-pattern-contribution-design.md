# Ditto Community Pattern Contribution Design

**Status:** Exploratory design proposed for Ohad review; not approved for implementation

**Date:** 2026-07-15

**Owner:** Ohad

**Design branch:** `codex/ditto-community-pattern-contribution-design`

**Working name:** Ditto Pattern Commons

## 1. Decision summary

Ditto may explore an optional community contribution system that helps it recognize vibe-coder slang, idioms, and recurring workflow shapes. The system accepts only derived, sanitized, user-reviewed contribution items. It never accepts session transcripts, full profiles, receipt appendices, code, file content, or raw log excerpts.

The chosen architecture keeps extraction and review local. The core Ditto runtime can prepare an export file but never uploads it. A separate, explicit web flow handles contribution. Low-frequency candidates remain encrypted and unusable; only patterns supported by at least five distinct contributors, followed by safety moderation, can enter a versioned community pack. That pack can influence candidate recognition only. It can never establish a personal trait or directly write a rule into `you.md`.

This is a separate future product and release. It is not part of Ditto Proof v1, the benchmark branch, or the current local-first launch.

## 2. Why this is separate

Ditto currently says that extraction, redaction, caches, and generated profiles stay local and that `ditto.py` makes no network calls. The README also tells users that their logs never leave their machine. Folding contribution into the benchmark release would weaken that message at the exact moment Ditto is trying to prove value and earn trust.

The Pattern Commons therefore has four independent boundaries:

- its own design, implementation plan, branch, release, and messaging;
- a local export boundary that sends nothing automatically;
- a separate contribution service that the user visits deliberately;
- a curated aggregate pack that returns through reviewed Ditto releases, not through runtime telemetry.

The benchmark may continue to say "local-first" and "logs never leave your machine" without an asterisk because the benchmark contains no contribution code or flow.

## 3. Product goal

Improve Ditto's ability to notice relevant language and workflow shapes without making personal profiles generic, crowd-driven, or less accurate.

Community knowledge can answer:

- "This phrase is often a vibe-coder shorthand worth examining."
- "This sequence resembles a known debug or shipping workflow shape."
- "This wording may signal a correction, rejection, proof request, or completion rule."

Community knowledge cannot answer:

- "This user definitely believes this rule."
- "This phrase has the same meaning for every operator."
- "Add this community preference to the user's profile."

The user's private local evidence remains the only authority for their profile. Community patterns can improve recall and classification, never supply evidence.

## 4. Hard invariants

The future feature must preserve all of these:

- Contribution is off by default and requires a direct user request.
- Normal install, mining, updates, profile loading, and MCP operation make no contribution request and expose no contribution prompt.
- `ditto.py` performs no upload and does not gain hidden telemetry.
- The exact outbound payload is visible locally before the user approves it.
- Every contribution item is unchecked by default and approved individually.
- Declining contribution loses no feature, quality tier, support, badge, or access.
- Raw logs, raw excerpts, assistant messages, tool output, code, profiles, receipts, paths, project names, customer names, and secrets are rejected by schema and content gates.
- Contributions cannot directly create, rank, or activate personal profile rules.
- User-specific receipts always outrank community hints.
- No contribution data is sold or licensed as a dataset.
- The system is not used to train a general-purpose model.
- Benchmark data and contribution data never share a store, identifier, service, or release artifact.

## 5. Considered approaches

### 5.1 Raw shared log pool

Users upload real session histories to maximize training signal.

**Rejected.** Logs routinely contain third-party code, client work, credentials, personal conversations, and other participants' content. The uploader cannot grant consent for every third party. This approach would contradict Ditto's local-first differentiator and create a data-harvesting risk no benchmark result could offset.

### 5.2 "Anonymized" excerpts

Users upload redacted snippets or receipts with obvious identifiers removed.

**Rejected.** Distinctive wording, code structure, project context, dates, and rare phrases can re-identify people even after direct identifiers are removed. Excerpts also tempt future reuse as training data and blur the line between private evidence and community knowledge.

### 5.3 Derived contribution envelopes with gated aggregation

Ditto locally derives bounded phrase or workflow items, shows the exact payload, and exports only approved items. A separate service groups equivalent contributions and promotes nothing until at least five distinct contributors support it.

**Chosen.** This gives Ditto useful vocabulary and workflow-shape signal while keeping private evidence local, bounding the payload, enabling withdrawal, and preserving a clean core-runtime boundary.

## 6. Allowed contribution types

The first design permits only two contribution types.

### 6.1 Phrase pattern

A short operator-authored slang term or idiom that may help the miner recognize a category of intent.

Required fields:

- normalized phrase, maximum 64 Unicode characters;
- broad language tag selected by the user;
- one category from a fixed taxonomy such as correction, rejection, proof request, scope control, design judgment, writing register, completion, or escalation;
- local support bucket: `2`, `3-5`, or `6+` distinct sessions;
- confidence bucket: low, medium, or high.

The payload contains no source sentence, surrounding text, timestamp, session identifier, path, or receipt.

### 6.2 Workflow shape

A bounded sequence of abstract workflow steps selected from a fixed taxonomy, for example:

`reproduce -> isolate -> minimal patch -> focused verification -> live proof`

Required fields:

- two to eight approved step identifiers;
- one broad domain: work, design, or writing;
- local support bucket: `2`, `3-5`, or `6+` distinct sessions;
- confidence bucket: low, medium, or high.

Free-form step text, commands, filenames, repository names, and code are forbidden.

New contribution types require a new reviewed schema version. Arbitrary prose, full traits, personality labels, and verbatim receipts are outside v1.

## 7. Local derivation and review

The local flow is a separate explicit command family and is never called by normal mining:

1. The user explicitly asks to preview community contributions.
2. Ditto derives bounded candidates locally from already-redacted, user-authored evidence.
3. Local validators reject forbidden fields, unique identifiers, code-like content, URLs, credentials, high-entropy strings, email addresses, phone numbers, paths, and seeded canaries.
4. Ditto shows each candidate with the exact outbound JSON fields and why it qualified locally.
5. Every candidate begins unchecked. The user can edit only the category/language metadata or remove the item; editing the phrase or workflow content requires revalidation as a new candidate.
6. The user approves items one at a time under the displayed data-use policy version.
7. Ditto writes a hash-sealed, immutable local export package and a private deletion-token file. It sends nothing.

The export package excludes the local profile ID, machine ID, user name, email, provider account, repository, full local counts, and source dates. The private deletion token is never included in screenshots or the public package.

## 8. Outbound envelope

Each approved item contains exactly:

- schema version;
- random payload ID unrelated to Ditto profile or run IDs;
- contribution type;
- normalized phrase plus fixed category, or fixed workflow-step sequence plus domain;
- optional broad language tag;
- clipped local support bucket;
- confidence bucket;
- local validator version;
- data-use policy version;
- content digest;
- client-generated deletion-token hash.

The envelope cannot contain extension fields. Unknown fields fail validation. The complete export file is rendered for final review before the user leaves the local environment.

## 9. Explicit web contribution

Uploading is a separate web action, not a CLI side effect:

1. The user visits the Pattern Commons contribution page.
2. The page explains that the selected derived items will leave the machine and links the exact data-use policy.
3. The user authenticates only to prove contributor distinctness and rate limits.
4. The user selects the previously exported package and sees its decoded items again.
5. The service validates the package and asks for one final batch approval.
6. The service returns a receipt containing accepted/rejected item IDs and withdrawal instructions.

The service must not ask for log-folder access, browser filesystem scanning, a Git repository token, or permission to read the user's repositories. It must not retain uploaded files after validation.

## 10. Distinctness and k-anonymity

No phrase or workflow pattern can be published, downloaded, used by Ditto, exposed to moderators, or included in aggregate statistics until it has support from at least **five distinct contributors (`k = 5`)**.

Distinctness uses an authenticated account only to derive a server-side keyed pseudonymous contributor ID. The service stores no provider username, email, avatar, access token, or profile. The pseudonymous ID is stored only in a membership record used for distinct counting, abuse controls, and withdrawal.

One contributor counts once per canonical candidate regardless of repeated uploads or devices. Rate limits and account-age/risk checks reduce simple Sybil attacks. A candidate supported by fewer than five contributors remains encrypted and inaccessible to human moderators. Its canonical keyed digest is used only to match future equivalent submissions.

Low-k candidates expire after 30 days. At expiry, encrypted content and membership records are deleted. Safety takes priority over coverage; rare-language or niche patterns that cannot reach `k = 5` do not enter the community pack.

## 11. Server-side handling

The contribution service processes an accepted item as follows:

1. Validate the fixed schema and content digest while treating all client input as untrusted.
2. Run independent secret, identifier, code, and policy filters.
3. Normalize with the same versioned rules used locally.
4. Reject conflicting category claims for the same phrase until reviewed after threshold.
5. Encrypt the candidate value and store a keyed canonical digest.
6. Add an opaque contributor membership only if it is distinct.
7. Keep staff access disabled while support is below `k = 5`.
8. At threshold, decrypt the aggregate candidate for trained safety moderation.
9. Promote only a safe, non-identifying, correctly categorized aggregate into a signed candidate pack.

Request bodies, decoded items, auth tokens, and contribution values must be excluded from application, proxy, analytics, and error logs. Operational logs may contain only request ID, status class, schema version, byte count, and coarse timing.

## 12. Moderation and poisoning resistance

K-anonymity reduces traceability but does not prove quality. Every threshold-qualified candidate must also pass:

- automated secret/PII/code scanning;
- canonicalization and duplicate review;
- category consistency checks;
- human safety and usefulness review;
- poisoning and coordinated-submission checks;
- license/data-use validation;
- a contextuality check that prevents a niche phrase from becoming a universal rule.

Moderators see only candidates that reached `k = 5`, never individual contributors or low-k content. Accepted entries are versioned, attributable to an aggregate contributor count, reversible, and covered by a public changelog. A disputed candidate is removed before release. A disputed entry that already shipped requires a signed patch release and public advisory; there is no remote kill switch or silent mutation of local packs.

## 13. How aggregates may improve Ditto

The approved community pack is a low-trust recognition aid. It may:

- expand candidate phrase detection;
- suggest a possible intent category for local evidence;
- help the miner distinguish vibe-coder slang from generic filler;
- improve workflow-shape candidate recall;
- provide contextual labels for later local evidence validation.

It may not:

- count as a receipt or supporting session;
- satisfy the evidence threshold for a profile rule;
- override a user's wording, register, contradiction, or rejection;
- add a trait that the user's own history does not support;
- lower existing validation, contradiction, or distinct-session gates;
- directly modify an active profile;
- dynamically download during mining.

Community hints must be marked as hints until the user's private local evidence independently supports them. If community hints increase false positives or weaken profile specificity, the pack fails calibration and does not ship.

## 14. Distribution of the community pack

Accepted aggregates are reviewed into a versioned, signed, human-readable pack in the Ditto repository. The pack ships only through a normal reviewed Ditto release with exact hashes and a changelog. Normal mining does not contact the contribution service or fetch a mutable remote pack.

The release notes disclose:

- pack version and hash;
- number of accepted phrase and workflow entries;
- minimum contributor threshold;
- removals, category changes, and safety incidents;
- calibration results and known language/coverage gaps.

The user can disable the bundled community pack locally. Disabling it does not disable Ditto or the user's private profile.

## 15. Governance and data use

Before any public pilot, Ditto publishes a plain-language data-use policy that states:

- exactly which derived fields are accepted;
- raw logs, excerpts, profiles, receipts, and code are prohibited;
- contributions may improve open-source and paid Ditto features but are not sold or licensed as a dataset;
- contributions are not used to train a general-purpose model;
- auth identity is converted to a pseudonymous distinctness identifier and raw account details are not stored;
- retention periods for low-k candidates, membership records, security logs, and backups;
- the withdrawal and deletion process and service-level target;
- subprocessors and hosting regions;
- the current policy version and material-change notification process.

Material policy expansion requires fresh consent. Previous consent cannot authorize new data types, new uses, model training, resale, or third-party access.

## 16. Withdrawal and deletion

The contributor keeps a private deletion token for each accepted item. Withdrawal can be requested without revealing the contributor's public identity.

On valid withdrawal:

- the membership is removed within 30 days;
- an unpromoted candidate with no members is deleted immediately;
- a promoted candidate whose distinct count falls below five is disabled and removed from the next pack;
- a promoted candidate that remains at or above five may remain because its aggregate support no longer depends on the withdrawn contribution;
- backups expire under the published retention schedule;
- the service returns a deletion receipt without exposing the remaining aggregate membership.

Security or privacy incidents trigger an emergency signed patch release and public advisory. Existing local installations are never changed remotely; users retain control over whether and when they update or disable the pack.

## 17. Third-party content boundary

Uploader consent does not cover clients, coworkers, repositories, or other people represented in a log. The design addresses this by never contributing excerpts and by restricting free-form content to a short operator-authored phrase.

Even then, an item is rejected if it contains or resembles:

- a person, company, product, repository, branch, file, or customer name;
- code, a command with project-specific arguments, a URL, issue ID, ticket ID, or commit hash;
- a quotation attributed to another person;
- confidential business terminology or a rare phrase with clear organizational meaning;
- personal, health, financial, legal, authentication, or contact data.

When uncertainty remains, the item stays local. There is no override button for a blocked privacy class.

## 18. Failure behavior

- Local candidate generation failure leaves mining and the active profile unchanged.
- Validation failure produces a local explanation and no export item.
- Upload or service failure never retries in the background.
- A policy-version mismatch requires the user to review the current policy and export again.
- A contribution rejected by the server remains rejected; it is not silently relaxed or rewritten.
- A community-pack signature, schema, or calibration failure disables the pack and continues with private-evidence-only mining.
- Contribution-service downtime has no effect on install, mining, updates, MCP, profiles, or benchmarks.

## 19. Verification requirements

Any future implementation must prove:

- default-off behavior and zero contribution network traffic in every normal Ditto command;
- the core runtime performs no upload;
- the exact reviewed export equals the uploaded envelope byte for byte;
- unknown fields and forbidden content fail closed;
- raw logs, excerpts, receipts, profiles, paths, code, and seeded canaries cannot enter an export;
- each item requires a separate affirmative selection;
- declining contribution has no product penalty;
- one contributor cannot increment the same candidate twice;
- low-k content is inaccessible and expires on schedule;
- promotion cannot occur below five distinct contributors;
- withdrawal decrements membership and disables below-threshold aggregates;
- poisoned, conflicting, or miscategorized candidates cannot ship automatically;
- community hints never satisfy personal evidence gates;
- disabling or corrupting the community pack falls back to private-evidence-only behavior;
- UTF-8, Hebrew, mixed-language text, and Windows paths behave safely;
- existing Ditto mining, Antigravity support, profiles, CLI, plugins, MCP, and tests do not regress.

Independent privacy and security review is required before any real upload pilot.

## 20. Phased evaluation

### Phase 0: design and threat review

Review this specification, data-use language, legal assumptions, and the threat model. No code, endpoint, collection, or recruitment occurs.

### Phase 1: local-only export prototype

Build candidate derivation, exact payload review, fixed schema, canary tests, and export generation using synthetic fixtures only. There is no server and no upload. The prototype must demonstrate that useful derived items can be produced without excerpts or identifiers.

### Phase 2: closed opt-in pilot

Only after independent review, deploy the separate upload service for a small invited cohort. Participants have no promotional obligation. The pilot measures rejection rates, usability, false positives, withdrawal, low-k expiry, and whether any candidate safely reaches threshold. No aggregate affects production Ditto during the pilot.

### Phase 3: signed pack calibration

Build a candidate aggregate pack and run a separate frozen calibration against private held-out fixtures. It must improve recognition recall without increasing unsupported profile rules, false positives, or privacy failures. Failed calibration blocks the pack.

### Phase 4: separate public release

Ship the contribution flow and first community pack only after a dedicated ship review. Messaging explains that contribution is optional and separate, while normal Ditto remains local-first and network-free.

## 21. Success and stop criteria

The idea advances beyond design only if:

- useful contribution items can be derived without excerpts;
- users understand exactly what leaves the machine;
- the system can enforce `k = 5`, withdrawal, expiry, and moderator isolation;
- the aggregate pack improves held-out recognition without weakening personal-evidence gates;
- independent review finds no unresolved high-risk privacy or security issue;
- the contribution story strengthens rather than confuses Ditto's local-first positioning.

The work stops if meaningful quality improvement requires raw logs, low-k inspection, background upload, weaker evidence gates, or misleading privacy copy. Growth, community size, or revenue pressure cannot override these stop criteria.

## 22. Relationship to community and revenue goals

Pattern Commons can give contributors a meaningful product role and create a defensible, versioned vocabulary layer. It is not a growth hack and does not ask contributors to promote Ditto. Contribution counts are not social proof unless independently verified and contextualized.

The aggregate pack may support free and paid Ditto features, but access to the user's own local profile remains independent of contribution. Team pilots, hosted profile distribution, and billing remain separate product decisions. No contributor data is sold, and no paid tier receives permission to bypass privacy, k-anonymity, moderation, or evidence gates.

## 23. Explicit non-goals

- No raw-log upload mode.
- No excerpt or receipt donation.
- No public dataset of individual contributions.
- No community-authored personal profiles.
- No dynamic community model that learns during a user's mining run.
- No benchmark integration.
- No implementation on the benchmark branch.
- No changes to `ditto.py`, README, SECURITY, manifests, or release surfaces during this design phase.
- No public recruitment, upload endpoint, or data collection before a separately approved implementation plan and privacy review.
