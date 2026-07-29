# BiosRios Premium Reels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the three existing Claude-versus-Codex Shorts into premium, resource-driven BiosRios Reels with high-end visual editing, deliberate sound design, verified proof, and `Comment "WORD"` conversion beats.

**Architecture:** Preserve the three independent HyperFrames compositions and their verified cloned-voice tracks. Add a shared premium visual stylesheet, three original generated editorial assets, a five-effect sound palette, resource-delivery files, and a deterministic PowerShell acceptance validator. The current batch uses the BiosRios character instead of exposing mismatched real-face speech; matching real footage or paid avatar footage can replace those character beats later without changing the proof scenes.

**Tech Stack:** HyperFrames 0.7.78+, HTML/CSS, GSAP 3.14.2, PowerShell, ffmpeg/ffprobe, Agent Media OS, image generation, Markdown.

**Execution workspace:** Use `D:\ditto`, not a fresh worktree. The HyperFrames media ledgers and reference videos are intentionally local/ignored assets and would be absent from a clean worktree. Stage only the exact text/code files named by each commit step; never stage `.media` binaries, reference videos, caches, or unrelated existing changes.

---

## File map

### Create

- `videos/refnces/REFERENCE-STYLE-AUDIT-2026-07-29.md`

  Records transferable editing patterns from the seven newest reference videos.
- `videos/biosrios-claude-vs-codex/resources/TEST-fair-agent-benchmark-checklist.md`

  Resource promised by Short 01.
- `videos/biosrios-claude-vs-codex/resources/PREFLIGHT-agent-run-checklist.md`

  Resource promised by Short 02.
- `videos/biosrios-claude-vs-codex/resources/REMATCH-transparent-scoring-sheet.md`

  Resource promised by Short 03.
- `videos/biosrios-claude-vs-codex/resources/REEL-METRICS-TEMPLATE.md`

  Per-platform 24-hour and 7-day measurement sheet.
- `videos/biosrios-claude-vs-codex/REEL-RESOURCE-DELIVERY.md`

  Keyword, local payload, caption opener, and pinned-comment map.
- `videos/biosrios-claude-vs-codex/validate_premium_reels.ps1`

  Deterministic acceptance checker.
- `videos/biosrios-claude-vs-codex-shorts/assets/styles/premium-reel.css`

  Shared layout, gradient, depth, caption, character, proof-card, and CTA primitives.
- `videos/biosrios-claude-vs-codex-shorts/assets/generated/s01-broken-equality.png`

  Original tactile broken-equality editorial visual.
- `videos/biosrios-claude-vs-codex-shorts/assets/generated/s02-token-lock.png`

  Original token-and-policy-lock editorial visual.
- `videos/biosrios-claude-vs-codex-shorts/assets/generated/s03-rematch-board.png`

  Original neutral-rematch editorial visual.
- `videos/biosrios-claude-vs-codex-shorts/SOUND-MAP.md`

  Frozen effect IDs, timing, and mix intent.
- `videos/biosrios-claude-vs-codex-shorts/build_premium_preview_sheet.cjs`

  Deterministic 27-frame approval-sheet builder.

### Modify

- `videos/refnces/BIOSRIOS-RESEARCH-AND-CONTENT-BLUEPRINT.md`
- `videos/biosrios-claude-vs-codex-shorts/compositions/s01/index.html`
- `videos/biosrios-claude-vs-codex-shorts/compositions/s02/index.html`
- `videos/biosrios-claude-vs-codex-shorts/compositions/s03/index.html`
- `videos/biosrios-claude-vs-codex-shorts/index.html`
- `videos/biosrios-claude-vs-codex-shorts/BRIEF.md`
- `videos/biosrios-claude-vs-codex-shorts/STORYBOARD.md`
- `videos/biosrios-claude-vs-codex-shorts/ANIMATION-MAP.md`
- `videos/biosrios-claude-vs-codex-shorts/DESIGN-ADHERENCE.md`
- `videos/biosrios-claude-vs-codex-shorts/PREVIEW-STATUS.md`
- `videos/biosrios-claude-vs-codex-shorts/.media/index.md`
- `videos/biosrios-claude-vs-codex-shorts/.media/manifest.jsonl`

### Generated verification outputs

- `videos/biosrios-claude-vs-codex-shorts/snapshots-premium-s01/`
- `videos/biosrios-claude-vs-codex-shorts/snapshots-premium-s02/`
- `videos/biosrios-claude-vs-codex-shorts/snapshots-premium-s03/`
- `videos/biosrios-claude-vs-codex-shorts/SHORTS-PREVIEW-CONTACT-SHEET-PREMIUM.jpg`

## Locked creative decisions from the new references

The four files added on 2026-07-29 are:

- `Video-93872.mp4`
- `Video-19740.mp4`
- `Video-57484.mp4`
- `Video-48261.mp4`

Transfer these patterns:

- Warm cream/peach gradient fields with large areas of negative space.
- Tactile 3D objects used as one visual metaphor, not decoration.
- Real product screens floating in a clean editorial field.
- Short black caption pills and minimal text per frame.
- Purposeful drop shadows and depth.
- A darker proof-dense variant when source receipts are the story.
- A final folder/resource visual paired with `Comment "WORD"`.

Do not transfer their branding, type treatment verbatim, exact 3D objects,
unverified claims, or unattributed source identity.

---

### Task 1: Freeze the expanded reference audit

**Files:**
- Create: `videos/refnces/REFERENCE-STYLE-AUDIT-2026-07-29.md`
- Modify: `videos/refnces/BIOSRIOS-RESEARCH-AND-CONTENT-BLUEPRINT.md`

- [ ] **Step 1: Write the seven-file audit**

Create the audit with this exact structure and conclusions:

```markdown
# BiosRios short-form reference style audit

Date: 2026-07-29

## Evidence boundary

These local downloads prove visual and editing patterns only. Creator handles,
source URLs, and public performance are not attributed unless independently
verified. No performance claim is inferred from a filename.

## Video-268.mp4

- Pattern: real host for the first two seconds, then clean interface cards.
- Transfer: immediate human anchor, large promise, screen crop, one CTA phrase.
- Reject: generic recommendation without a verified resource.

## Video-27458.mp4

- Pattern: split-screen host and product demo with rapid reframing.
- Transfer: face-to-proof handoff, deliberate close-up, clean neutral field.
- Reject: holding the face after the screen becomes the stronger visual.

## Video-73925.mp4

- Pattern: tutorial steps, bold caption phrases, phone UI mockups, constant
  background variation.
- Transfer: one instruction per beat and a visible pointer to the exact control.
- Reject: unrelated art backgrounds that compete with the technical lesson.

## Video-93872.mp4

- Pattern: warm peach field, floating Claude screens, sparse caption pills,
  sculptural object opener, dimensional end card.
- Transfer: premium negative space, screen depth, small caption pills, tactile
  CTA object.
- Reject: using a 3D object without a story function.

## Video-19740.mp4

- Pattern: minimalist gradient, isolated 3D symbols, screen demonstration,
  dark signature close.
- Transfer: one metaphor per section, restrained copy, tonal close.
- Reject: small low-contrast text over pale gradients.

## Video-57484.mp4

- Pattern: dark purple proof field, benchmark charts, source posts, product
  footage, highlighted claims.
- Transfer: proof-dense dark mode and fast evidence escalation.
- Reject: treating a social post as primary evidence.

## Video-48261.mp4

- Pattern: bright 3D keyword object, product screen, three-step diagram,
  exact `Comment "Interview"` resource CTA.
- Transfer: direct resource promise, physical folder metaphor, green emphasis,
  calm premium motion.
- Reject: copying its color identity or exact folder design.

## BiosRios synthesis

Use a warm cream/peach editorial field for hooks and explanations, then switch
to near-black proof cards for receipts. Use one original tactile object per
Short, the BiosRios character only at trust and reaction beats, and one direct
comment keyword after the lesson is complete.
```

- [ ] **Step 2: Update the main blueprint**

In `BIOSRIOS-RESEARCH-AND-CONTENT-BLUEPRINT.md`:

- Change the local short-form evidence count from eight to fifteen.
- Add `REFERENCE-STYLE-AUDIT-2026-07-29.md` to the local evidence list.
- Add the synthesis paragraph above under `Short-form video`.
- Preserve all existing evidence boundaries.

- [ ] **Step 3: Verify the audit has no unsupported attribution**

Run:

```powershell
rg -n "@|https?://|views|followers" videos/refnces/REFERENCE-STYLE-AUDIT-2026-07-29.md
```

Expected: only the evidence-boundary wording; no creator handle, URL, view
count, or performance claim.

- [ ] **Step 4: Commit the audit**

```powershell
git add -f -- videos/refnces/REFERENCE-STYLE-AUDIT-2026-07-29.md videos/refnces/BIOSRIOS-RESEARCH-AND-CONTENT-BLUEPRINT.md
git commit -m "docs: expand BiosRios reel reference audit"
```

---

### Task 2: Create the three promised resources and delivery map

**Files:**
- Create: `videos/biosrios-claude-vs-codex/resources/TEST-fair-agent-benchmark-checklist.md`
- Create: `videos/biosrios-claude-vs-codex/resources/PREFLIGHT-agent-run-checklist.md`
- Create: `videos/biosrios-claude-vs-codex/resources/REMATCH-transparent-scoring-sheet.md`
- Create: `videos/biosrios-claude-vs-codex/resources/REEL-METRICS-TEMPLATE.md`
- Create: `videos/biosrios-claude-vs-codex/REEL-RESOURCE-DELIVERY.md`

- [ ] **Step 1: Create the TEST checklist**

Use this complete payload:

```markdown
# TEST: Fair AI-agent benchmark checklist

1. Freeze one committed repository snapshot.
2. Give both agents the identical task text and acceptance criteria.
3. Authenticate both agents before timing begins.
4. Equalize tools, permissions, sandbox mode, and approval policy.
5. Give each agent a separate working copy from the same commit.
6. Lock the time, token, and intervention budgets before either run.
7. Save transcripts, commands, errors, diffs, tests, cost, and elapsed time.
8. Score both outputs with the same independent evaluator.

Stop and restart the comparison if authentication, write access, test access,
or evaluator access differs.
```

- [ ] **Step 2: Create the PREFLIGHT checklist**

Use this complete payload:

```markdown
# PREFLIGHT: Agent-run checklist

## Authentication

- Confirm the model/provider session is authenticated.
- Run one harmless model turn before the measured task.

## Repository

- Record the commit hash.
- Confirm the working tree is clean.
- Create a disposable file and remove it.

## Permissions

- Confirm the agent can read the target files.
- Confirm the agent can write inside the intended workspace.
- Record sandbox and approval modes.

## Verification

- Run the public test command before the measured task.
- Confirm the evaluator can inspect the final diff and test output.

If any check fails, stop. Do not score the run.
```

- [ ] **Step 3: Create the REMATCH rubric**

Use this complete payload:

```markdown
# REMATCH: Transparent scoring sheet

| Category | Weight | Claude | Codex | Evidence |
|---|---:|---:|---:|---|
| Requested outcome completed | 35 |  |  |  |
| Correctness and regressions | 25 |  |  |  |
| Verification quality | 15 |  |  |  |
| Scope discipline | 10 |  |  |  |
| Time and measured cost | 10 |  |  |  |
| Handoff clarity | 5 |  |  |  |
| **Total** | **100** |  |  |  |

## Required run metadata

- Repository commit:
- Task text:
- Tool versions:
- Authentication state:
- Sandbox and approvals:
- Time budget:
- Token budget:
- Human interventions:
- Independent evaluator:

Do not name a winner when either run failed preflight or did not produce a
comparable attempt.
```

- [ ] **Step 4: Create the delivery map**

Use this exact mapping:

```markdown
# BiosRios Reel resource delivery

| Short | Keyword | Local resource | Caption opener | Pinned comment |
|---|---|---|---|---|
| S01 | TEST | `resources/TEST-fair-agent-benchmark-checklist.md` | Comment **TEST** and I’ll send you the fair AI-agent benchmark checklist. | Same prompt is not enough. TEST includes the eight checks I use before comparing agents. |
| S02 | PREFLIGHT | `resources/PREFLIGHT-agent-run-checklist.md` | Comment **PREFLIGHT** and I’ll send you the agent-run checklist. | Run these checks before spending tokens. If one fails, stop the benchmark. |
| S03 | REMATCH | `resources/REMATCH-transparent-scoring-sheet.md` | Comment **REMATCH** and I’ll send you the transparent scoring sheet. | No winner without comparable runs. REMATCH includes the 100-point rubric and run metadata. |

These are local handoff paths. Ohad selects the public delivery URLs before
posting. No auto-DM or posting action is included.
```

- [ ] **Step 5: Create the metrics template**

Use:

```markdown
# BiosRios Reel measurement template

| Field | Instagram | YouTube Shorts |
|---|---:|---:|
| Publish date/time |  |  |
| Views at 24 hours |  |  |
| Views at 7 days |  |  |
| Three-second hold |  |  |
| Average watch time |  |  |
| Completion rate |  |  |
| Replays |  |  |
| Saves |  |  |
| Shares |  |  |
| Total comments |  |  |
| Keyword comments |  |  |
| Keyword comments per 1,000 views |  |  |
| Profile visits |  |  |
| Follows/subscribers gained |  |  |

Record only platform-reported values. Do not estimate missing metrics.
```

- [ ] **Step 6: Verify every promised resource exists**

Run:

```powershell
$root = 'videos/biosrios-claude-vs-codex'
$required = @(
  "$root/resources/TEST-fair-agent-benchmark-checklist.md",
  "$root/resources/PREFLIGHT-agent-run-checklist.md",
  "$root/resources/REMATCH-transparent-scoring-sheet.md",
  "$root/resources/REEL-METRICS-TEMPLATE.md",
  "$root/REEL-RESOURCE-DELIVERY.md"
)
$required | ForEach-Object { if (-not (Test-Path -LiteralPath $_)) { throw "Missing $_" } }
```

Expected: exit 0 with no output.

- [ ] **Step 7: Commit the resources**

```powershell
git add -f -- videos/biosrios-claude-vs-codex/resources videos/biosrios-claude-vs-codex/REEL-RESOURCE-DELIVERY.md
git commit -m "content: add BiosRios reel resource pack"
```

---

### Task 3: Add a failing premium-Reel acceptance validator

**Files:**
- Create: `videos/biosrios-claude-vs-codex/validate_premium_reels.ps1`

- [ ] **Step 1: Write the validator**

Use this complete script:

```powershell
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$pack = Split-Path -Parent $MyInvocation.MyCommand.Path
$project = Join-Path (Split-Path -Parent $pack) 'biosrios-claude-vs-codex-shorts'

$resources = @{
  TEST = Join-Path $pack 'resources\TEST-fair-agent-benchmark-checklist.md'
  PREFLIGHT = Join-Path $pack 'resources\PREFLIGHT-agent-run-checklist.md'
  REMATCH = Join-Path $pack 'resources\REMATCH-transparent-scoring-sheet.md'
}

$compositions = @(
  @{ Id = 'S01'; Keyword = 'TEST'; Path = Join-Path $project 'compositions\s01\index.html' },
  @{ Id = 'S02'; Keyword = 'PREFLIGHT'; Path = Join-Path $project 'compositions\s02\index.html' },
  @{ Id = 'S03'; Keyword = 'REMATCH'; Path = Join-Path $project 'compositions\s03\index.html' }
)

$requiredMedia = @(
  '.media\audio\sfx\sfx_006.wav',
  '.media\audio\sfx\sfx_007.wav',
  '.media\audio\sfx\sfx_008.wav',
  '.media\audio\sfx\sfx_009.wav',
  '.media\audio\sfx\sfx_010.wav',
  '.media\images\image_008.png',
  '.media\images\image_009.png',
  '.media\images\image_010.png'
)

$errors = [System.Collections.Generic.List[string]]::new()

foreach ($entry in $resources.GetEnumerator()) {
  if (-not (Test-Path -LiteralPath $entry.Value)) {
    $errors.Add("Missing resource for $($entry.Key): $($entry.Value)")
  }
}

foreach ($relative in $requiredMedia) {
  $path = Join-Path $project $relative
  if (-not (Test-Path -LiteralPath $path)) {
    $errors.Add("Missing media: $relative")
  }
}

foreach ($item in $compositions) {
  if (-not (Test-Path -LiteralPath $item.Path)) {
    $errors.Add("Missing composition: $($item.Path)")
    continue
  }

  $html = Get-Content -Raw -LiteralPath $item.Path
  $checks = @{
    'premium stylesheet' = 'premium-reel\.css'
    'keyword data attribute' = "data-cta-keyword=`"$($item.Keyword)`""
    'visible comment CTA' = "(?s)Comment.*$($item.Keyword)"
    'verified evidence label' = 'VERIFIED LOCAL EXCERPT'
    'bottom safe CTA' = 'resource-cta'
    'signature CTA sound' = 'sfx_010\.wav'
  }

  foreach ($check in $checks.GetEnumerator()) {
    if ($html -notmatch $check.Value) {
      $errors.Add("$($item.Id) missing $($check.Key)")
    }
  }

  if ($html -match 'FACE-CLONE PREVIEW FALLBACK') {
    $errors.Add("$($item.Id) still contains preview fallback copy")
  }
}

$s01 = Get-Content -Raw -LiteralPath (Join-Path $project 'compositions\s01\index.html')
$root = Get-Content -Raw -LiteralPath (Join-Path $project 'index.html')
if ($s01 -ne $root) {
  $errors.Add('Short 01 root mirror differs from compositions\s01\index.html')
}

if ($errors.Count -gt 0) {
  $errors | ForEach-Object { Write-Error $_ }
  throw "$($errors.Count) premium Reel validation error(s)"
}

Write-Host 'Premium Reel validator PASS: resources, media, CTAs, proof labels, and S01 mirror are complete.'
```

- [ ] **Step 2: Run the validator and confirm it fails**

Run:

```powershell
& 'videos/biosrios-claude-vs-codex/validate_premium_reels.ps1'
```

Expected: FAIL because the premium stylesheet, five sound effects, three
generated images, resource CTAs, and new data attributes do not exist yet.

- [ ] **Step 3: Commit the failing validator**

```powershell
git add -f -- videos/biosrios-claude-vs-codex/validate_premium_reels.ps1
git commit -m "test: define premium Reel acceptance contract"
```

---

### Task 4: Generate and freeze the premium visual and sound assets

**Files:**
- Create: `videos/biosrios-claude-vs-codex-shorts/assets/generated/s01-broken-equality.png`
- Create: `videos/biosrios-claude-vs-codex-shorts/assets/generated/s02-token-lock.png`
- Create: `videos/biosrios-claude-vs-codex-shorts/assets/generated/s03-rematch-board.png`
- Create: `videos/biosrios-claude-vs-codex-shorts/SOUND-MAP.md`
- Modify: `.media/index.md`
- Modify: `.media/manifest.jsonl`

- [ ] **Step 1: Generate the S01 editorial asset**

Use the image-generation skill with:

```text
Create an original premium vertical editorial still, 1080x1920. Warm cream and
soft peach gradient background with generous negative space. In the center,
two tactile sculptural tiles form a broken equality symbol: the left tile is
matte Claude orange, the right tile is restrained Codex blue, separated by a
thin red fracture. Soft studio lighting, realistic cast shadows, elegant 3D
product-photography finish. No words, no logos, no UI, no watermark, no people.
```

Save the selected result as
`assets/generated/s01-broken-equality.png`.

- [ ] **Step 2: Generate the S02 editorial asset**

Use:

```text
Create an original premium vertical editorial still, 1080x1920. Warm cream and
soft peach gradient background. A transparent glass token cylinder contains a
dense stack of small luminous blue counters, but a precise red mechanical lock
blocks the output slot. Tactile 3D product-photography style, soft realistic
shadows, clean negative space, sophisticated and minimal. No words, no logos,
no UI, no watermark, no people.
```

Save as `assets/generated/s02-token-lock.png`.

- [ ] **Step 3: Generate the S03 editorial asset**

Use:

```text
Create an original premium vertical editorial still, 1080x1920. Warm cream and
soft peach gradient background. A tactile 3D referee clipboard stands upright
with two equal blank columns, a centered balance marker, and a small neutral
rematch arrow below. Soft studio lighting, elegant shadows, premium editorial
product render, ample negative space. No readable words, no brand logos, no
winner symbol, no watermark, no people.
```

Save as `assets/generated/s03-rematch-board.png`.

- [ ] **Step 4: Normalize all three generated images to 1080x1920**

Run:

```powershell
$assets = @(
  'assets/generated/s01-broken-equality.png',
  'assets/generated/s02-token-lock.png',
  'assets/generated/s03-rematch-board.png'
)
foreach ($asset in $assets) {
  $normalized = "$asset.normalized.png"
  ffmpeg -y -v error -i $asset -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" -frames:v 1 $normalized
  Move-Item -Force -LiteralPath $normalized -Destination $asset
}
```

- [ ] **Step 5: Adopt the three images in deterministic order**

Run from the Shorts project:

```powershell
node 'C:\Users\ohad1\.agents\skills\media-use\scripts\resolve.mjs' --type image --from 'assets/generated/s01-broken-equality.png' --intent 'S01 premium broken equality editorial hero' --project .
node 'C:\Users\ohad1\.agents\skills\media-use\scripts\resolve.mjs' --type image --from 'assets/generated/s02-token-lock.png' --intent 'S02 premium token lock editorial hero' --project .
node 'C:\Users\ohad1\.agents\skills\media-use\scripts\resolve.mjs' --type image --from 'assets/generated/s03-rematch-board.png' --intent 'S03 premium neutral rematch editorial hero' --project .
```

Expected IDs in this order: `image_008`, `image_009`, `image_010`.

- [ ] **Step 6: Resolve the five-effect sound palette**

Run in this order:

```powershell
node 'C:\Users\ohad1\.agents\skills\media-use\scripts\resolve.mjs' --type sfx --intent 'short soft premium card whoosh, clean and restrained, under 1 second' --project .
node 'C:\Users\ohad1\.agents\skills\media-use\scripts\resolve.mjs' --type sfx --intent 'precise modern UI click for checklist verification, dry and short' --project .
node 'C:\Users\ohad1\.agents\skills\media-use\scripts\resolve.mjs' --type sfx --intent 'low controlled editorial impact for a major number reveal, no cinematic boom tail' --project .
node 'C:\Users\ohad1\.agents\skills\media-use\scripts\resolve.mjs' --type sfx --intent 'subtle one second riser into a technical reversal, clean and modern' --project .
node 'C:\Users\ohad1\.agents\skills\media-use\scripts\resolve.mjs' --type sfx --intent 'short premium signature hit for a comment keyword CTA, confident not aggressive' --project .
```

The resolver's first pass created `sfx_001` through `sfx_005` as MP3
candidate history. Those files are retained but are not used. The final
ledger-safe 48 kHz stereo WAV palette is adopted as `sfx_006` through
`sfx_010` in the same functional order.

- [ ] **Step 7: Create the sound map**

Use:

```markdown
# BiosRios premium Reel sound map

| ID | Function | Default volume |
|---|---|---:|
| `sfx_006` | Card/screen transition whoosh | 0.22 |
| `sfx_007` | Checklist/UI verification click | 0.18 |
| `sfx_008` | Number or verdict impact | 0.24 |
| `sfx_009` | Reversal riser | 0.16 |
| `sfx_010` | Comment-keyword signature hit | 0.24 |

Speech stays at 1.0. The existing music bed is reduced from 0.045 to 0.035.
No effect may overlap a spoken numerical claim at full level.
```

- [ ] **Step 8: Verify media dimensions and audio readability**

Run:

```powershell
ffprobe -v error -show_entries stream=width,height -of csv=p=0 .media/images/image_008.png
ffprobe -v error -show_entries stream=width,height -of csv=p=0 .media/images/image_009.png
ffprobe -v error -show_entries stream=width,height -of csv=p=0 .media/images/image_010.png
Get-ChildItem .media/audio/sfx/sfx_00*.wav | Select-Object Name,Length
```

Expected: each image is 1080x1920; five non-empty WAV files exist.

---

### Task 5: Add shared premium visual primitives

**Files:**
- Create: `videos/biosrios-claude-vs-codex-shorts/assets/styles/premium-reel.css`

- [ ] **Step 1: Write the shared stylesheet**

Use these exact primitives:

```css
:root {
  --ink: #171714;
  --cream: #f7f2e8;
  --peach: #f4b47c;
  --orange: #d86f32;
  --blue: #2f80ed;
  --red: #ed3f35;
  --green: #28bf63;
  --proof: #11110f;
  --muted: #746f67;
  --shadow: 0 34px 70px rgba(55, 35, 17, 0.22);
}

.premium-field {
  background:
    radial-gradient(circle at 84% 10%, rgba(244, 180, 124, .72), transparent 34%),
    radial-gradient(circle at 12% 82%, rgba(255, 255, 255, .92), transparent 38%),
    linear-gradient(145deg, #fffdf8 0%, var(--cream) 48%, #f8cda7 100%);
}

.premium-field::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: .16;
  background-image:
    linear-gradient(rgba(23, 23, 20, .06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(23, 23, 20, .06) 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: linear-gradient(to bottom, transparent, black 24%, black 76%, transparent);
}

.caption-pill {
  display: inline-flex;
  align-items: center;
  max-width: 820px;
  padding: 13px 21px;
  border-radius: 13px;
  color: white;
  background: var(--ink);
  box-shadow: 0 12px 28px rgba(0, 0, 0, .2);
  font: 700 34px/1.05 "Evidence Mono", monospace;
}

.editorial-art {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.character-anchor {
  position: absolute;
  right: -54px;
  bottom: 250px;
  width: 520px;
  filter: drop-shadow(0 28px 36px rgba(23, 23, 20, .25));
  transform-origin: 70% 100%;
}

.proof-card {
  border: 1px solid rgba(255, 255, 255, .12);
  border-radius: 30px;
  background: var(--proof);
  color: var(--cream);
  box-shadow: var(--shadow);
  overflow: hidden;
}

.proof-card .verified {
  color: #ff9a62;
  font: 700 24px/1 "Evidence Mono", monospace;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.resource-cta {
  position: absolute;
  left: 64px;
  right: 64px;
  bottom: 340px;
  display: grid;
  gap: 18px;
  padding: 38px 42px;
  border-radius: 32px;
  background: var(--ink);
  color: white;
  box-shadow: 0 30px 72px rgba(23, 23, 20, .34);
  text-align: center;
}

.resource-cta .comment {
  font: 400 44px/1.05 "Evidence Mono", monospace;
}

.resource-cta .keyword {
  color: #9cf1b4;
  font: 400 104px/.9 "Archivo Black", sans-serif;
  letter-spacing: -.04em;
}

.resource-cta .reward {
  color: #ddd6ca;
  font: 700 28px/1.2 "Evidence Mono", monospace;
}

.proof-source {
  position: absolute;
  left: 64px;
  right: 64px;
  bottom: 108px;
  color: var(--muted);
  font: 700 21px/1.25 "Evidence Mono", monospace;
}
```

- [ ] **Step 2: Verify the stylesheet has no unsupported filters**

Run:

```powershell
rg -n "backdrop-filter|mix-blend-mode|url\\(https?://|random|animation:" assets/styles/premium-reel.css
```

Expected: no matches.

---

### Task 6: Upgrade Short 01 to the premium TEST funnel

**Files:**
- Modify: `videos/biosrios-claude-vs-codex-shorts/compositions/s01/index.html`
- Modify: `videos/biosrios-claude-vs-codex-shorts/index.html`

- [ ] **Step 1: Add premium styling and media**

Add:

```html
<link rel="stylesheet" href="assets/styles/premium-reel.css" />
```

Keep the 42-second timing and all three cloned-voice tracks. Reduce
`#s01-music` to `data-volume="0.035"`.

Use `image_008.png` as the editorial field for the opening and `image_003.png`
as the pointing BiosRios character. Remove both
`FACE-CLONE PREVIEW FALLBACK` labels.

- [ ] **Step 2: Use these locked visual beats**

| Time | Visual |
|---:|---|
| 0.0-1.2 | Full-frame `image_008`; impact on the broken equality |
| 1.2-6.2 | Pointing character enters; caption pill `EXACT SAME TASK` |
| 6.2-11.4 | Three tactile input cards enter one at a time |
| 11.4-17.8 | Claude proof card, orange authentication highlight |
| 17.8-24.8 | Codex proof card, blue token count, red zero-files result |
| 24.8-32.8 | Claude/Codex tiles separate; AUTH, TOOLS, PERMISSIONS, RUNTIME assemble between them |
| 32.8-37.2 | Conclusion: `SAME PROMPT ≠ SAME TEST` |
| 37.2-42.0 | CTA with `data-cta-keyword="TEST"` |

The CTA markup must be:

```html
<div class="resource-cta" data-cta-keyword="TEST">
  <div class="comment">Comment</div>
  <div class="keyword">"TEST"</div>
  <div class="reward">Get the fair AI-agent benchmark checklist</div>
</div>
```

Every designed proof panel must contain the visible label
`VERIFIED LOCAL EXCERPT`.

- [ ] **Step 3: Add deterministic sound clips**

Add timed audio elements:

```html
<audio class="clip" src=".media/audio/sfx/sfx_008.wav" data-start="0.15" data-duration="1.0" data-track-index="30" data-volume="0.24"></audio>
<audio class="clip" src=".media/audio/sfx/sfx_006.wav" data-start="6.15" data-duration="1.0" data-track-index="31" data-volume="0.22"></audio>
<audio class="clip" src=".media/audio/sfx/sfx_006.wav" data-start="11.35" data-duration="1.0" data-track-index="31" data-volume="0.22"></audio>
<audio class="clip" src=".media/audio/sfx/sfx_006.wav" data-start="17.75" data-duration="1.0" data-track-index="31" data-volume="0.22"></audio>
<audio class="clip" src=".media/audio/sfx/sfx_009.wav" data-start="31.9" data-duration="1.0" data-track-index="32" data-volume="0.16"></audio>
<audio class="clip" src=".media/audio/sfx/sfx_010.wav" data-start="37.25" data-duration="1.0" data-track-index="33" data-volume="0.24"></audio>
```

- [ ] **Step 4: Add the CTA timeline**

Add:

```js
tl.fromTo(
  "#s01-host-close .resource-cta",
  { y: 90, scale: .94, opacity: 0 },
  { y: 0, scale: 1, opacity: 1, duration: .52, ease: "power4.out" },
  37.2
);
```

Fade the conclusion copy to 0.18 opacity from 37.1 to 37.4 so the CTA becomes
the only dominant element.

- [ ] **Step 5: Keep the S01 root mirror exact**

Copy the completed `compositions/s01/index.html` byte-for-byte to `index.html`.

- [ ] **Step 6: Run the focused S01 checks**

Run:

```powershell
npx --yes hyperframes@0.7.78 snapshot --at 0.5,3.5,7.5,12.5,19.5,26.5,34,38.5,41 --no-end --output snapshots-premium-s01 --describe false
& '..\biosrios-claude-vs-codex\validate_premium_reels.ps1'
```

Expected snapshot result: nine readable frames. The validator should still fail
only for incomplete S02/S03 or missing shared assets, not S01.

---

### Task 7: Upgrade Short 02 to the premium PREFLIGHT funnel

**Files:**
- Modify: `videos/biosrios-claude-vs-codex-shorts/compositions/s02/index.html`

- [ ] **Step 1: Add premium styling and replace the fallback host**

Link `assets/styles/premium-reel.css`. Keep the 38-second timing and
cloned voice. Reduce music to `0.035`.

Use `image_009.png` for the opening metaphor and `image_002.png` for the
shocked BiosRios character. Remove all fallback labels.

- [ ] **Step 2: Use these locked visual beats**

| Time | Visual |
|---:|---|
| 0.0-1.1 | Token cylinder and red lock; `160,649 TOKENS` |
| 1.1-7.3 | Character enters; caption pill `ZERO FILES` |
| 7.3-13.5 | Count-up and real usage receipt |
| 13.5-19.5 | Public test command; red policy lock |
| 19.5-25.3 | Patch attempt; zero-files stamp |
| 25.3-32.4 | `TOKEN COUNT ≠ PRODUCTIVITY` plus three preflight cards |
| 32.4-35.4 | Conclusion: `PREFLIGHT FIRST` |
| 35.4-38.0 | CTA with `data-cta-keyword="PREFLIGHT"` |

Use:

```html
<div class="resource-cta" data-cta-keyword="PREFLIGHT">
  <div class="comment">Comment</div>
  <div class="keyword" style="font-size:72px">"PREFLIGHT"</div>
  <div class="reward">Get the authentication, permissions, repo, and test checklist</div>
</div>
```

- [ ] **Step 3: Add deterministic S02 sound clips**

Use `sfx_008` at 0.15, `sfx_006` at 7.25/13.45/19.45, `sfx_007` at
27.2/28.0/28.8 for the three checklist confirmations, `sfx_009` at 24.9, and
`sfx_010` at 35.45. Keep volumes from `SOUND-MAP.md`.

- [ ] **Step 4: Add the CTA animation**

Use the same resource-CTA entrance as S01 at 35.4. Fade the conclusion and
checklist to 0.18 opacity during the 35.3-35.6 handoff.

- [ ] **Step 5: Run focused S02 checks**

Run:

```powershell
npx --yes hyperframes@0.7.78 snapshot --at 0.5,3.5,8.5,14.5,20.5,26.5,33,36,37.5 --no-end --output snapshots-premium-s02 --describe false
& '..\biosrios-claude-vs-codex\validate_premium_reels.ps1'
```

Expected: nine readable frames. The validator should now fail only for S03 if
all assets have been frozen.

---

### Task 8: Upgrade Short 03 to the premium REMATCH funnel

**Files:**
- Modify: `videos/biosrios-claude-vs-codex-shorts/compositions/s03/index.html`

- [ ] **Step 1: Add premium styling and neutral-rematch art**

Link `assets/styles/premium-reel.css`. Keep the 40-second timing and
cloned voice. Reduce music to `0.035`.

Use `image_010.png` for the opening and `image_006.png` for the thinking
BiosRios character. Remove fallback labels.

- [ ] **Step 2: Use these locked visual beats**

| Time | Visual |
|---:|---|
| 0.0-1.2 | Neutral referee board; `I REFUSED A WINNER` |
| 1.2-6.5 | Character enters and points to two equal blank columns |
| 6.5-12.5 | Claude auth proof |
| 12.5-18.8 | Codex policy proof |
| 18.8-25.0 | `CLAUDE LOSER` and `CODEX LOSER` claims crossed out |
| 25.0-31.0 | `NO VALID RESULT` with unchanged-repo explanation |
| 31.0-35.8 | Neutral rematch choice |
| 35.8-40.0 | CTA with `data-cta-keyword="REMATCH"` |

Use:

```html
<div class="resource-cta" data-cta-keyword="REMATCH">
  <div class="comment">Comment</div>
  <div class="keyword">"REMATCH"</div>
  <div class="reward">Get the transparent 100-point scoring sheet</div>
</div>
```

- [ ] **Step 3: Add deterministic S03 sound clips**

Use `sfx_008` at 0.15 and 25.2, `sfx_006` at 6.45/12.45, `sfx_007` at
19.7/20.95 for the crossouts, `sfx_009` at 24.3, and `sfx_010` at 35.85.

- [ ] **Step 4: Add the CTA animation**

Enter the CTA at 35.8 and fade the rematch choices to 0.18 opacity by 36.1.

- [ ] **Step 5: Run focused S03 and full acceptance checks**

Run:

```powershell
npx --yes hyperframes@0.7.78 snapshot --at 0.5,3.5,7.5,13.5,19.5,25.8,32,36.5,39 --no-end --output snapshots-premium-s03 --describe false
& '..\biosrios-claude-vs-codex\validate_premium_reels.ps1'
```

Expected:

```text
Premium Reel validator PASS: resources, media, CTAs, proof labels, and S01 mirror are complete.
```

---

### Task 9: Update production documentation and preview sheet

**Files:**
- Modify: `BRIEF.md`
- Modify: `STORYBOARD.md`
- Modify: `ANIMATION-MAP.md`
- Modify: `DESIGN-ADHERENCE.md`
- Modify: `PREVIEW-STATUS.md`
- Create: `build_premium_preview_sheet.cjs`
- Create: `SHORTS-PREVIEW-CONTACT-SHEET-PREMIUM.jpg`

- [ ] **Step 1: Update the project docs**

Record:

- Premium hybrid style is implemented.
- The 2026-07-29 reference audit informed gradient, 3D metaphor, proof-card,
  caption-pill, depth, and keyword-CTA choices.
- Current batch uses BiosRios character anchors because matching real-face
  speech is unavailable.
- Keywords are TEST, PREFLIGHT, and REMATCH.
- Resource paths are the three local Markdown files.
- Paid HeyGen remains optional and unused.
- Final rendering remains user-gated.

- [ ] **Step 2: Write the deterministic premium contact-sheet builder**

Create `build_premium_preview_sheet.cjs`:

```js
const path = require("node:path");
const sharp = require("C:/Users/ohad1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp");

const root = __dirname;
const frameTimes = {
  s01: ["0.5", "3.5", "7.5", "12.5", "19.5", "26.5", "34", "38.5", "41"],
  s02: ["0.5", "3.5", "8.5", "14.5", "20.5", "26.5", "33", "36", "37.5"],
  s03: ["0.5", "3.5", "7.5", "13.5", "19.5", "25.8", "32", "36.5", "39"],
};

const inputs = [];
for (let row = 0; row < 9; row += 1) {
  for (const id of ["s01", "s02", "s03"]) {
    const time = frameTimes[id][row];
    inputs.push(
      path.join(
        root,
        `snapshots-premium-${id}`,
        `frame-${String(row).padStart(2, "0")}-at-${time}s.png`,
      ),
    );
  }
}

async function build() {
  const tileWidth = 360;
  const tileHeight = 640;
  const composites = [];

  for (let index = 0; index < inputs.length; index += 1) {
    const tile = await sharp(inputs[index])
      .resize(tileWidth - 8, tileHeight - 8, { fit: "cover" })
      .jpeg({ quality: 90, chromaSubsampling: "4:4:4" })
      .toBuffer();

    composites.push({
      input: tile,
      left: (index % 3) * tileWidth + 4,
      top: Math.floor(index / 3) * tileHeight + 4,
    });
  }

  await sharp({
    create: {
      width: tileWidth * 3,
      height: tileHeight * 9,
      channels: 3,
      background: "#171714",
    },
  })
    .composite(composites)
    .jpeg({ quality: 92, chromaSubsampling: "4:4:4" })
    .toFile(path.join(root, "SHORTS-PREVIEW-CONTACT-SHEET-PREMIUM.jpg"));
}

build().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
```

- [ ] **Step 3: Build the premium contact sheet**

Run:

```powershell
node build_premium_preview_sheet.cjs
```

Expected: a 1080x5760 JPEG. Each row shows the same narrative stage across S01,
S02, and S03.

- [ ] **Step 4: Visually review the contact sheet**

Reject and fix:

- Blank or washed-out transition frames.
- Caption pills below the 320 px lower safe zone.
- Character art covering proof.
- Generated art containing readable fake UI or invented claims.
- Evidence cards without source labels.
- CTA keywords smaller than their reward copy.
- Any visual held longer than its information requires.

---

### Task 10: Run the complete verification gate

**Files:**
- No source file changes unless a check exposes a defect.

- [ ] **Step 1: Probe the pinned HyperFrames version**

Run:

```powershell
npx hyperframes@latest upgrade --project . --check
```

If the project is behind, run:

```powershell
npx hyperframes@latest upgrade --project .
npx hyperframes check
```

If the upgrade check fails, restore only `package.json` to its prior
HyperFrames pin and continue on 0.7.78. Record the retained or upgraded version
in `PREVIEW-STATUS.md`.

- [ ] **Step 2: Run the full project check**

Run:

```powershell
npm run check
```

Expected:

```text
0 error(s)
Check passed
```

Review every warning. Do not accept contrast, overflow, blank-media, runtime,
or unsafe-zone warnings in the hook or CTA beats.

- [ ] **Step 3: Run both deterministic validators**

Run:

```powershell
& '..\biosrios-claude-vs-codex\validate_premium_reels.ps1'
& '..\biosrios-claude-vs-codex\validate_host_clips.ps1'
```

Expected:

- Premium Reel validator: PASS.
- Host-clip validator: L01-L03 pass; the nine HeyGen-quota-dependent clips
  remain reported missing. That known long-form/avatar limitation does not
  block these character-led premium Short previews.

- [ ] **Step 4: Confirm no final render exists**

Run:

```powershell
rg --files . -g '*.mp4' | rg 'render|output|final'
```

Expected: no premium final MP4. Rendering is still waiting for Ohad's preview
approval.

- [ ] **Step 5: Commit the text/code implementation**

Stage only:

```powershell
git add -f -- `
  videos/biosrios-claude-vs-codex-shorts/assets/styles/premium-reel.css `
  videos/biosrios-claude-vs-codex-shorts/compositions/s01/index.html `
  videos/biosrios-claude-vs-codex-shorts/compositions/s02/index.html `
  videos/biosrios-claude-vs-codex-shorts/compositions/s03/index.html `
  videos/biosrios-claude-vs-codex-shorts/index.html `
  videos/biosrios-claude-vs-codex-shorts/BRIEF.md `
  videos/biosrios-claude-vs-codex-shorts/STORYBOARD.md `
  videos/biosrios-claude-vs-codex-shorts/ANIMATION-MAP.md `
  videos/biosrios-claude-vs-codex-shorts/DESIGN-ADHERENCE.md `
  videos/biosrios-claude-vs-codex-shorts/PREVIEW-STATUS.md `
  videos/biosrios-claude-vs-codex-shorts/SOUND-MAP.md `
  videos/biosrios-claude-vs-codex-shorts/build_premium_preview_sheet.cjs
git commit -m "feat: upgrade BiosRios Shorts to premium resource funnels"
```

Do not stage `.media`, generated binaries, snapshot folders, contact sheets,
reference downloads, caches, or unrelated workspace files.

---

### Task 11: Present the approval package

**Files:**
- Read-only handoff.

- [ ] **Step 1: Present the preview evidence**

Provide clickable links to:

- `SHORTS-PREVIEW-CONTACT-SHEET-PREMIUM.jpg`
- `snapshots-premium-s01/contact-sheet.jpg`
- `snapshots-premium-s02/contact-sheet.jpg`
- `snapshots-premium-s03/contact-sheet.jpg`
- `REEL-RESOURCE-DELIVERY.md`
- `resources/REEL-METRICS-TEMPLATE.md`
- `REFERENCE-STYLE-AUDIT-2026-07-29.md`

- [ ] **Step 2: State the exact remaining limitations**

State:

- No final MP4 has been rendered.
- No video has been posted.
- No comment or DM automation has been configured.
- Public resource URLs still require Ohad's selected delivery destination.
- HeyGen Free remains exhausted, but this premium character-led batch no longer
  depends on it.

- [ ] **Step 3: Ask for one approval**

Ask:

`Approve these premium Reel previews for final render?`

Only after explicit approval may the render task run.
