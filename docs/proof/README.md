# Ditto Proof v1 operator runbook

Ditto Proof v1 is an unexecuted benchmark methodology. At this point no public result exists. The committed example is synthetic, non-scored, and non-comparable. It is a packaging example, not evidence that either condition performs better.

## Frozen claim boundary

The scored release is a complete-system comparison: the selected agent host as configured, once cold and once with the frozen Ditto profile installed. It is not a comparison of underlying models. The contract is:

- Ditto `v0.3.7`, commit `5f4008b0c0df40dcadb92c8fd1ba4dcf3aee40d0`.
- Two observed live systems, one Codex-host and one Claude-host. Provider commands and current labels come from observed provider interfaces; unavailable systems are not substituted.
- Three families (`work`, `design`, `write`), two variants (`primary`, `held-out`), two trials, and two conditions. This produces 24 pairs and **48 isolated cell executions**.
- Every cell is a **clean-host cold start** with host persistent context absent. Ditto is installed only inside the Ditto condition's isolated home.
- Public interpretation is **small-n, directional only** with raw denominators and Wilson 95% intervals. No significance, model-quality, traffic, star, or revenue claim follows from this benchmark.
- The run stops on a mixed version, contaminated home, fixture mismatch, missing system, or changed policy.

The private profile rubric is mechanism-only. It can confirm whether the intended context was installed; it cannot be a headline outcome. Objective task checks and eligible blind pair verdicts are outcomes.

## Authority gates

There are two different approval digests:

1. **Explicit cost approval.** Before any provider process, record the observed menu label, provider/host version, quota snapshot, exact argv, timeout/turn budget, and expected maximum cost for both systems. Freeze the manifest. Ohad approves its SHA-256. `execute-cell` accepts only that exact manifest hash together with `--execute`.
2. **explicit ship approval.** After execution, review, invalidation, and privacy scanning, recalculate the publication from the complete evidence. Ohad approves the separate evidence digest. A manifest approval never authorizes publication.

No credential belongs in an approval record. If a provider attempt fails before meaningful output, one documented retry may be authorized; **both attempts are retained**. Model behavior, a bad answer, timeout after meaningful output, or a hard failure is a result and is not rerun.

## Private fixture authoring

Create the **private run root outside the repository**. For example:

```powershell
$RunRoot = 'D:\ditto-proof-runs\v1-live'
New-Item -ItemType Directory -Path $RunRoot
```

The six required private task IDs are:

```text
work-primary       work-held-out
design-primary     design-held-out
write-primary      write-held-out
```

Each directory contains `brief.md`, `policy.json`, `checks.json`, all starting files, and deterministic success commands. `brief.md` states the bounded task without naming a preferred condition. `policy.json` freezes allowed paths, tools, permissions, and budgets. `checks.json` defines machine-verifiable success and hard failures. Design tasks also freeze a viewport, screenshot path, and accessibility-report path. Writing tasks include a fictional or sealed fact packet and a machine-readable claim map.

Do not store scored fixture content in Git before execution. Author and commit each fixture in a separate private Git repository, seal its clean commit using `proof.fixtures.seal_fixture`, and retain only its task ID, commit, and hashes in the benchmark manifest. Both primary and held-out variants must be frozen before the non-scored pilot. Never tune a task after seeing an output.

```powershell
python -c "from proof.fixtures import seal_fixture; seal_fixture(r'D:\private-fixtures\work-primary', r'D:\ditto-proof-runs\v1-live', 'work-primary')"
```

Repeat the sealing call for all six IDs. A changed, dirty, linked, or in-repository fixture fails closed.

## Capture and freeze the two live systems

Capture screenshots and quota/cost receipts first. Use argv tokens, not a shell command string. One representative freeze command is:

```powershell
python -m proof.cli freeze-system --host codex --menu-label '<observed label>' --model-id '<observed ID or omit this option>' --host-version '<observed version>' --run-argv codex --run-argv exec --ditto-install-argv python --ditto-install-argv '<frozen installer>' --screenshot-sha256 '<64 hex>' --tool-policy-sha256 '<64 hex>' --permission-policy-sha256 '<64 hex>' --quota-snapshot '<dated receipt reference>' --expected-cost '<maximum expected cost>'
```

Run the equivalent command for Claude. Save both exact JSON outputs. Build the 24 pairs with `proof.manifest.build_pairs`, then `proof.manifest.build_manifest`; do not hand-edit the resulting manifest.

```powershell
python -m proof.cli validate --manifest 'D:\ditto-proof-runs\v1-live\manifest.json'
```

The returned `manifest_sha256` is the only token that can satisfy the execution gate. Ohad reviews the systems, fixtures, budgets, quota, and expected cost, then supplies that exact digest as the explicit cost approval.

The frozen `profile_manifest_sha256` is the exact tree hash of the dedicated home after the v0.3.7 installer finishes, including every skill, profile, instruction adapter, and version receipt expected there. A no-op installer, a missing file, a changed byte, or any extra persistent-context file fails before the provider command starts. Each sealed task's `brief.md` must also hash to its frozen `instruction_sha256` after reset.

## Non-scored pilot

Before any scored cell, load `proof/fixtures/pilot/registry.json`, build six cells with `proof.pilot.build_pilot_plan`, and simulate/capture the evidence lifecycle. The pilot must remain labelled `pilot`, `non-scored`, and `non-comparable`. Its job is to detect isolation, reset, review, and redaction failures. It cannot be merged into the v1 matrix or quoted as a product result.

## Prepare and execute cells

Preparation is safe and does not start a provider:

```powershell
python -m proof.cli prepare-cell --manifest 'D:\ditto-proof-runs\v1-live\manifest.json' --cell-id '<frozen cell ID>' --run-root 'D:\ditto-proof-runs\v1-live'
```

Execution is intentionally noisy and gated:

```powershell
python -m proof.cli execute-cell --manifest 'D:\ditto-proof-runs\v1-live\manifest.json' --cell-id '<frozen cell ID>' --run-root 'D:\ditto-proof-runs\v1-live' --execute --approval '<exact manifest_sha256 approved by Ohad>'
```

For every attempt, append stdout/stderr hashes, artifact hashes, workspace hash, clean-home audit, installed-context hash, exit state, usage/duration when comparable, and meaningful-output state with `proof.store.EvidenceStore`. Never overwrite an attempt or evaluation.

Evaluate the family-specific objective contract:

```powershell
python -m proof.cli evaluate --record 'D:\ditto-proof-runs\v1-live\record.json' --policy 'D:\ditto-proof-runs\v1-live\policy.json'
```

## Independent blind review

Pair review is performed by an **independent third party** who consented, was not involved in building Ditto or the harness, and cannot see condition labels. For writing, the reviewer must also be unfamiliar with Ohad's voice. **Ohad cannot cast a blind verdict**; recognizing the operator or condition ends the review and records an invalid verdict.

Valid anonymous review record:

```json
{
  "schema": "ditto-proof-review/1",
  "review_id": "review-opaque",
  "pair_id": "pair-opaque",
  "family": "write",
  "reviewer_role": "independent",
  "consent_reference": "consent-receipt-sha256",
  "eligibility_attestation": "not involved; no conflict",
  "unfamiliar_with_operator_voice": true,
  "blinding_confirmed": true,
  "verdict": "left",
  "left_review_id": "review-left-opaque",
  "right_review_id": "review-right-opaque",
  "invalidation_reason": "",
  "created_at": "2026-07-15T00:00:00Z"
}
```

Invalidated review example:

```json
{
  "schema": "ditto-proof-review/1",
  "review_id": "review-opaque",
  "pair_id": "pair-opaque",
  "family": "write",
  "reviewer_role": "independent",
  "consent_reference": "consent-receipt-sha256",
  "eligibility_attestation": "not involved; no conflict",
  "unfamiliar_with_operator_voice": false,
  "blinding_confirmed": false,
  "verdict": null,
  "left_review_id": "review-left-opaque",
  "right_review_id": "review-right-opaque",
  "invalidation_reason": "reviewer recognized operator voice",
  "created_at": "2026-07-15T00:00:00Z"
}
```

Only the anonymous verdict and its eligibility state enter the public aggregate. Consent details remain private.

## Package and ship

Recalculate, never copy numbers into prose. The records file contains eligible cell summaries plus retained exclusions/invalidations. Compute the digest with `proof.publish.publication_approval_digest`, then ask Ohad for the exact, separate ship approval:

```powershell
python -m proof.cli package --manifest 'D:\ditto-proof-runs\v1-live\manifest.json' --records 'D:\ditto-proof-runs\v1-live\public-records.json' --evidence-root 'D:\ditto-proof-runs\v1-live' --destination 'D:\ditto-proof-runs\v1-live\candidate-publication' --ship-approval '<exact evidence digest approved by Ohad>' --privacy-inputs 'D:\ditto-proof-runs\v1-live\privacy-inputs.json' --manual-review-approved
```

The private `privacy-inputs.json` has exactly `canaries` (a name-to-marker string map) and `private_roots` (a nonempty list containing the evidence and fixture roots). `package` resolves every attempt, final evaluation, and independent review hash from the append-only evidence root before recalculating. It refuses to write unless the manual-review flag, real canaries, private roots, exact evidence digest, and all 48 frozen identities agree. It then runs `proof.privacy.scan_public_tree(..., manual_review_approved=True)`. Every seeded canary, private root, secret pattern, local user path, raw profile, transcript, receipt, hidden file, symlink/reparse point, or unknown file type blocks shipping.

Real evidence, clips, README claims, website changes, launch copy, and a benchmark GitHub release require all 48 cells, passing objective checks, eligible review or disclosed invalidations, recomputed denominators, complete limitations, privacy approval, and Ohad's evidence-digest approval. Any partial run must use an explicitly non-v1 label. Media must trace to exact cell and artifact hashes and cannot hide losses, ties, exclusions, or unavailable systems.
