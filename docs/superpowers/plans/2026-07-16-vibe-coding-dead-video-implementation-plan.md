# Vibe Coding Is Dead Video Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce and verify a 3–5 minute, 1080p60 BiosRios YouTube essay at the editorial level of the supplied Coding Sloth reference, using Ohad’s existing character and approved voice clone.

**Architecture:** A fresh HyperFrames `general-video` project owns a deterministic HTML composition driven by a scene manifest and selected voice-line timings. Separate scripts validate sources, generate clarity-gated voice lines, build timing/captions, verify source and rendered output, create a contact sheet, and safely clean bounded scratch data. External references and shared BiosRios assets are read in place rather than copied.

**Tech Stack:** HyperFrames 0.7.x, HTML/CSS/JavaScript, GSAP seek-safe timelines, Node.js verification scripts, Python 3.10 with Chatterbox/Whisper, FFmpeg/FFprobe, JSON/JSONL manifests.

---

## File Map

- `videos/vibe-coding-dead/BRIEF.md`: approved intent, route, run shape, voice, storage, and evidence rules.
- `videos/vibe-coding-dead/README.md`: build, preview, render, verify, and cleanup commands.
- `videos/vibe-coding-dead/package.json`: stable command surface pinned to the installed HyperFrames version.
- `videos/vibe-coding-dead/hyperframes.json`: composition and asset paths.
- `videos/vibe-coding-dead/script.md`: final sourced narration and visual direction by line.
- `videos/vibe-coding-dead/index.html`: semantic scene DOM and HyperFrames timing attributes.
- `videos/vibe-coding-dead/styles.css`: BiosRios editorial design system and scene layouts.
- `videos/vibe-coding-dead/timeline.js`: one paused, seek-safe master animation timeline.
- `videos/vibe-coding-dead/assets/sources.jsonl`: URL, license/context, local path, and editorial purpose for every external asset.
- `videos/vibe-coding-dead/assets/timing.json`: selected voice duration, start, end, and scene mapping.
- `videos/vibe-coding-dead/assets/vo/*.wav`: selected voice lines only.
- `videos/vibe-coding-dead/assets/captures/`: compressed real evidence and demonstration captures.
- `videos/vibe-coding-dead/assets/editorial/`: short sourced stills and original diagrams.
- `videos/vibe-coding-dead/tools/gen_voice.py`: Chatterbox generation plus Whisper clarity gate.
- `videos/vibe-coding-dead/tools/build_timing.py`: narration assembly, timing JSON, transcript, and SRT.
- `videos/vibe-coding-dead/tools/verify.mjs`: source, media, render, source-manifest, duration, and storage checks.
- `videos/vibe-coding-dead/tools/contact-sheet.ps1`: full-timeline visual QA sheet.
- `videos/vibe-coding-dead/tools/cleanup.ps1`: dry-run-first removal of episode-local scratch and rejected takes.
- `videos/vibe-coding-dead/renders/vibe-coding-is-dead-1080p60.mp4`: final upload master.
- `videos/vibe-coding-dead/renders/vibe-coding-is-dead.srt`: final captions.
- `videos/vibe-coding-dead/renders/qa-contact-sheet.jpg`: full-timeline QA evidence.

### Task 1: Scaffold the Isolated HyperFrames Episode

**Files:**
- Create: `videos/vibe-coding-dead/BRIEF.md`
- Create: `videos/vibe-coding-dead/README.md`
- Create: `videos/vibe-coding-dead/package.json`
- Create: `videos/vibe-coding-dead/hyperframes.json`
- Create: `videos/vibe-coding-dead/tools/verify.mjs`

- [ ] **Step 1: Install the selected workflow and initialize the project**

Run from `D:/ditto`:

```powershell
npx hyperframes skills update general-video
npx --yes hyperframes@0.7.42 init videos/vibe-coding-dead
```

Expected: `videos/vibe-coding-dead/` contains a runnable HyperFrames project and no render output.

- [ ] **Step 2: Write the failing source-contract verifier**

Create `tools/verify.mjs` with checks for required files, no remote media URLs in composition source, exactly six editorial visual modes in the scene manifest, 210–300 second duration, 1920×1080 output, 60 fps, source-manifest coverage, selected voice files only, and retained size under 750 MB. Add a `--video` branch that reads FFprobe JSON and requires H.264, AAC stereo, 48 kHz, 1920×1080, 60 fps, 210–300 seconds, and a file size no greater than 500 MB.

The verifier must print one `PASS` or `FAIL` line per contract and exit nonzero if any contract fails.

- [ ] **Step 3: Run the verifier and confirm the empty scaffold fails**

Run:

```powershell
node tools/verify.mjs
```

Expected: nonzero exit with missing `BRIEF.md`, `script.md`, `assets/sources.jsonl`, `assets/timing.json`, and composition files.

- [ ] **Step 4: Add the approved brief and stable command surface**

Write `BRIEF.md` with these canonical values:

```yaml
---
workflow: general-video
flow: automation
storyboard: no
mode: autonomous
aspect: 16:9
resolution: 1920x1080
fps: 60
duration: 210-300
language: English
---
```

Record the title, thesis, no-marketing constraint, Coding Sloth editorial reference, BiosRios host, `clean_calm.wav` voice reference, real before/after requirement, internet-media source logging, and storage contract from the design spec.

Write `package.json` with scripts:

```json
{
  "name": "vibe-coding-dead-video",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "npx --yes hyperframes@0.7.42 preview",
    "check": "npx --yes hyperframes@0.7.42 lint && npx --yes hyperframes@0.7.42 validate && npx --yes hyperframes@0.7.42 inspect && node tools/verify.mjs",
    "render": "npx --yes hyperframes@0.7.42 render",
    "verify:video": "node tools/verify.mjs --video renders/vibe-coding-is-dead-1080p60.mp4",
    "qa:sheet": "powershell -ExecutionPolicy Bypass -File tools/contact-sheet.ps1",
    "cleanup:dry": "powershell -ExecutionPolicy Bypass -File tools/cleanup.ps1",
    "cleanup": "powershell -ExecutionPolicy Bypass -File tools/cleanup.ps1 -Apply"
  }
}
```

- [ ] **Step 5: Commit the scaffold**

```powershell
git add -- videos/vibe-coding-dead
git commit -m "chore: scaffold vibe coding video"
```

### Task 2: Research and Lock the Sourced Script

**Files:**
- Create: `videos/vibe-coding-dead/script.md`
- Create: `videos/vibe-coding-dead/assets/sources.jsonl`
- Create: `videos/vibe-coding-dead/assets/scene-manifest.json`

- [ ] **Step 1: Collect primary evidence**

Use first-party or research sources for the meaning of vibe coding, current agentic-coding adoption, persistent value of expertise, context preservation, and verification. Capture only the visible passages used in the video. The minimum source set is Karpathy’s original framing or a faithful primary citation, Anthropic’s 2026 agentic-coding research, OpenAI’s 2026 agents-at-work report, and one published study of verification behavior.

- [ ] **Step 2: Write the source manifest before downloading media**

Each JSONL row must use this exact schema:

```json
{"id":"source-short-name","url":"https://example.com/page","kind":"documentation|research|community|meme|capture","local":"assets/captures/source-short-name.webp","purpose":"The exact claim or joke supported on screen","rights":"first-party capture|public domain|permissive|transformative commentary","accessed":"2026-07-16"}
```

Run `node tools/verify.mjs` and expect source-schema checks to pass while later composition checks still fail.

- [ ] **Step 3: Write the final narration**

Write 560–680 spoken words across 46–58 short voice lines. Use this beat allocation:

- 45–60 words: celebration-and-collapse cold open;
- 80–100 words: fair definition and appeal of vibe coding;
- 130–160 words: three escalating failure modes;
- 150–180 words: agentic-engineering replacement;
- 90–120 words: real before/after demonstration;
- 55–75 words: four-rule recap and character closer.

Every factual line receives a footnote to a source-manifest ID. Every joke or opinion line is labeled `editorial` in its line metadata. Do not mention Ditto or ask for stars.

- [ ] **Step 4: Build the scene manifest**

Create 28–36 scenes. Each scene object must contain:

```json
{
  "id": "s01-collapse",
  "chapter": "cold-open",
  "voice": ["V01", "V02"],
  "mode": "character|screen|diagram|kinetic|meme|evidence",
  "purpose": "One sentence describing what the viewer learns or feels",
  "assets": ["assets/captures/example.webp"],
  "targetSeconds": 6
}
```

All six visual modes must appear, no mode may repeat more than three scenes consecutively, and character scenes must cover 35–50% of estimated runtime.

- [ ] **Step 5: Verify and commit the editorial lock**

Run:

```powershell
node tools/verify.mjs
```

Expected: script word-count, source-schema, scene-count, visual-mode, and no-marketing checks pass.

Commit:

```powershell
git add -- videos/vibe-coding-dead/script.md videos/vibe-coding-dead/assets/sources.jsonl videos/vibe-coding-dead/assets/scene-manifest.json
git commit -m "docs: lock sourced vibe coding script"
```

### Task 3: Produce the Real Before-and-After Demonstration

**Files:**
- Create: `videos/vibe-coding-dead/demo/fixture/`
- Create: `videos/vibe-coding-dead/demo/vibes-request.md`
- Create: `videos/vibe-coding-dead/demo/system-request.md`
- Create: `videos/vibe-coding-dead/demo/run-demo.ps1`
- Create: `videos/vibe-coding-dead/demo/results.json`
- Create: `videos/vibe-coding-dead/assets/captures/demo-*.webp`

- [ ] **Step 1: Create a deterministic small-app fixture**

Use a local static task-list app with a hidden acceptance contract: adding dark mode must preserve keyboard focus, localStorage migration, and the existing delete-item test. The fixture includes a deliberately brittle theme toggle and runnable tests.

- [ ] **Step 2: Write the two requests**

`vibes-request.md` contains only:

```text
Add a beautiful dark mode to this app. Make it feel modern and polished.
```

`system-request.md` names the same outcome plus bounded files, preserved behaviors, acceptance commands, and a requirement to report evidence without changing unrelated surfaces.

- [ ] **Step 3: Run both modes from identical fixture copies**

`run-demo.ps1` creates episode-local copies under `.scratch/demo-vibes` and `.scratch/demo-system`, runs the two requests using the available coding agent, captures terminal output, runs the same tests, records changed-file counts, and writes `results.json`. The script must never modify the source fixture after copying it.

- [ ] **Step 4: Capture only observed differences**

Create compressed WebP captures of the prompt, changed files, test output, and final UI for both runs. Update `sources.jsonl` with `kind: capture` rows pointing to the local demonstration.

- [ ] **Step 5: Commit the reproducible demonstration**

```powershell
git add -- videos/vibe-coding-dead/demo videos/vibe-coding-dead/assets/captures/demo-*.webp videos/vibe-coding-dead/assets/sources.jsonl
git commit -m "test: capture agentic engineering comparison"
```

### Task 4: Generate and Verify the BiosRios Voice Track

**Files:**
- Create: `videos/vibe-coding-dead/tools/gen_voice.py`
- Create: `videos/vibe-coding-dead/tools/build_timing.py`
- Create: `videos/vibe-coding-dead/assets/vo/*.wav`
- Create: `videos/vibe-coding-dead/assets/timing.json`
- Create: `videos/vibe-coding-dead/transcript.txt`
- Create: `videos/vibe-coding-dead/renders/vibe-coding-is-dead.srt`

- [ ] **Step 1: Port the approved voice settings without copying outputs**

Use `D:/ditto/videos/long-claude-code/assets/vref/clean_calm.wav` directly. Preserve Chatterbox CPU generation, seeds `21 + take * 11`, temperature `0.45`, calm settings near exaggeration `0.42–0.50` and CFG `0.68–0.70`, and hook/reveal settings near exaggeration `0.55–0.60` and CFG `0.65–0.66`.

- [ ] **Step 2: Add a failing clarity and file-retention check**

`gen_voice.py --check` must fail if any selected line is missing, Whisper similarity is below 0.90 without a manual-approval receipt, or a rejected `take-*` file exists outside `.scratch/voice-rejects`.

- [ ] **Step 3: Generate up to three takes per line**

Generate lines into `.scratch/voice-takes`, select the clearest take, copy only the selected file to `assets/vo/VNN.wav`, and store duration, similarity, transcript, seed, exaggeration, and CFG in `assets/vo/meta.json`.

- [ ] **Step 4: Build narration, timing, transcript, and captions**

`build_timing.py` inserts authored pauses, writes `assets/timing.json`, concatenates selected lines into `assets/narration.wav`, writes `transcript.txt`, and creates a line-level SRT whose cues never overlap.

- [ ] **Step 5: Verify duration and commit selected audio**

Run:

```powershell
python tools/gen_voice.py --check
python tools/build_timing.py --check
ffprobe -v error -show_entries format=duration -of default=nw=1 assets/narration.wav
```

Expected: every line passes or has a manual receipt, captions do not overlap, and narration plus authored pauses falls between 210 and 300 seconds.

Commit selected outputs only:

```powershell
git add -- videos/vibe-coding-dead/tools videos/vibe-coding-dead/assets/vo videos/vibe-coding-dead/assets/timing.json videos/vibe-coding-dead/assets/narration.wav videos/vibe-coding-dead/transcript.txt videos/vibe-coding-dead/renders/vibe-coding-is-dead.srt
git commit -m "feat: generate biosrios narration"
```

### Task 5: Build the Static Mixed-Media Composition

**Files:**
- Create: `videos/vibe-coding-dead/index.html`
- Create: `videos/vibe-coding-dead/styles.css`
- Create: `videos/vibe-coding-dead/assets/editorial/*.webp`
- Modify: `videos/vibe-coding-dead/assets/sources.jsonl`

- [ ] **Step 1: Create the semantic scene DOM**

Build one composition root at 1920×1080 and one section per scene-manifest entry. Each scene uses timing attributes derived from `assets/timing.json`, semantic `data-scene`, `data-mode`, and `aria-label` values, local media paths only, and no autoplay-owned media.

- [ ] **Step 2: Implement the BiosRios editorial design system**

Use charcoal/black foundations, off-white marker lines, one warm orange and one warning red for meaning, readable source cards, rough diagram strokes, punch-line typography, and native-color screenshots. Character poses reference `../long-claude-code/assets/cast/*.png` in place.

- [ ] **Step 3: Create original or transformed editorial assets**

Prefer original recreations for meme structures and hand-drawn diagrams. Compress screenshots and stills to WebP at the smallest dimensions that survive their maximum crop. Add every external asset to `sources.jsonl` before it appears in HTML.

- [ ] **Step 4: Run static checks and snapshot representative frames**

Run `npm run check`, then snapshot at least the cold open, each failure mode, the agentic workflow diagram, before/after comparison, and final recap. Inspect at 1920×1080 for readable evidence and safe margins.

- [ ] **Step 5: Commit static composition**

```powershell
git add -- videos/vibe-coding-dead/index.html videos/vibe-coding-dead/styles.css videos/vibe-coding-dead/assets/editorial videos/vibe-coding-dead/assets/sources.jsonl
git commit -m "feat: compose vibe coding video layouts"
```

### Task 6: Animate the YouTube Editorial Rhythm

**Files:**
- Create: `videos/vibe-coding-dead/timeline.js`
- Modify: `videos/vibe-coding-dead/index.html`
- Modify: `videos/vibe-coding-dead/styles.css`

- [ ] **Step 1: Create one deterministic paused GSAP timeline**

Register a single master timeline controlled only by HyperFrames time. All randomness uses fixed values derived from scene IDs. No `setTimeout`, unbounded CSS animation, wall-clock access, or independent media playback is allowed.

- [ ] **Step 2: Animate by editorial function**

Use hard cuts and punch-ins for jokes, draw-on paths for explanations, restrained parallax on evidence, character squash-and-settle for reactions, and short kinetic text bursts. Do not apply the same entrance to every scene.

- [ ] **Step 3: Enforce pacing constraints**

Visual changes occur every 2–6 seconds by default; holds up to 9 seconds must contain internal motion or evidence highlighting. No visual mode repeats more than three scenes, and fast montages are followed by quieter explanation frames.

- [ ] **Step 4: Run seek-safety diagnostics**

Run HyperFrames lint, validate, inspect, and keyframe diagnostics at scene boundaries plus random seeks. Expected: identical frames for repeated seeks and no late media loads.

- [ ] **Step 5: Commit animation**

```powershell
git add -- videos/vibe-coding-dead/timeline.js videos/vibe-coding-dead/index.html videos/vibe-coding-dead/styles.css
git commit -m "feat: animate youtube editorial cut"
```

### Task 7: Mix Narration, Music, and Sound Effects

**Files:**
- Create: `videos/vibe-coding-dead/assets/audio/music.wav`
- Create: `videos/vibe-coding-dead/assets/audio/sfx-*.wav`
- Create: `videos/vibe-coding-dead/assets/final-mix.wav`
- Create: `videos/vibe-coding-dead/tools/mix_audio.py`
- Modify: `videos/vibe-coding-dead/index.html`

- [ ] **Step 1: Select a restrained music bed and sparse effects**

Use licensed or generated audio with provenance recorded in `sources.jsonl`. Music supports pacing without competing with speech. Effects are reserved for the collapse, failure escalation, diagram reveal, before/after switch, and closing joke.

- [ ] **Step 2: Implement deterministic mixing**

`mix_audio.py` aligns narration, music, and effects to `timing.json`, ducks music under speech, includes deliberate music dropouts, and renders 48 kHz stereo WAV.

- [ ] **Step 3: Normalize and verify audio**

Use FFmpeg EBU R128 analysis. Adjust until integrated loudness is approximately -14 LUFS and true peak is no higher than -1 dBTP. Record the final values in `renders/audio-qa.txt`.

- [ ] **Step 4: Attach the final mix as the composition’s single audio track**

HyperFrames owns playback. Do not add separate autonomous `<audio>` elements for voice, music, or effects.

- [ ] **Step 5: Commit audio**

```powershell
git add -- videos/vibe-coding-dead/assets/audio videos/vibe-coding-dead/assets/final-mix.wav videos/vibe-coding-dead/tools/mix_audio.py videos/vibe-coding-dead/index.html videos/vibe-coding-dead/assets/sources.jsonl videos/vibe-coding-dead/renders/audio-qa.txt
git commit -m "feat: mix vibe coding video audio"
```

### Task 8: Render, Inspect, Revise, and Verify

**Files:**
- Create: `videos/vibe-coding-dead/tools/contact-sheet.ps1`
- Create: `videos/vibe-coding-dead/renders/vibe-coding-is-dead-1080p60.mp4`
- Create: `videos/vibe-coding-dead/renders/qa-contact-sheet.jpg`
- Modify: composition files as QA requires

- [ ] **Step 1: Run all source checks**

```powershell
npm run check
python tools/gen_voice.py --check
python tools/build_timing.py --check
```

Expected: all checks pass before rendering.

- [ ] **Step 2: Render the 1080p60 upload master**

Render through HyperFrames to `.scratch/render/`, then encode the selected master as H.264/AAC at a visually sufficient bitrate under the 500 MB cap.

- [ ] **Step 3: Generate the contact sheet**

`contact-sheet.ps1` samples the full timeline at 5-second intervals, labels each frame with timestamp and scene ID, and tiles them into `renders/qa-contact-sheet.jpg`.

- [ ] **Step 4: Perform the side-by-side editorial audit**

Compare the final cut with both supplied references. Record pass/fail evidence for mixed-media variety, comedic interruption, character identity, explanatory clarity, readable evidence, fast/quiet contrast, and absence of copied visual identity. Revise any failing scene and rerender.

- [ ] **Step 5: Verify the rendered artifact**

```powershell
npm run verify:video
ffmpeg -v error -i renders/vibe-coding-is-dead-1080p60.mp4 -filter_complex ebur128=peak=true -f null NUL
```

Expected: H.264, AAC stereo 48 kHz, 1920×1080, 60 fps, 210–300 seconds, ≤500 MB, no clipping, and target loudness.

- [ ] **Step 6: Commit the verified deliverables**

```powershell
git add -- videos/vibe-coding-dead
git commit -m "feat: render vibe coding youtube video"
```

### Task 9: Clean Scratch Data and Prove Retained Size

**Files:**
- Create: `videos/vibe-coding-dead/tools/cleanup.ps1`
- Modify: `videos/vibe-coding-dead/README.md`
- Create: `videos/vibe-coding-dead/renders/storage-qa.txt`

- [ ] **Step 1: Implement a safe dry-run cleanup**

`cleanup.ps1` resolves every candidate path and refuses any path outside `videos/vibe-coding-dead/.scratch`, `assets/vo/rejected`, or explicitly named episode-local browser cache directories. Default mode prints absolute candidates and total bytes without deleting.

- [ ] **Step 2: Verify the dry run**

```powershell
npm run cleanup:dry
```

Expected: only episode-local scratch, rejected takes, extracted frames, duplicate renders, and browser caches are listed. Shared `videos/long-claude-code/assets/cast` and `assets/vref` paths never appear.

- [ ] **Step 3: Apply cleanup and verify retained size**

```powershell
npm run cleanup
node tools/verify.mjs
```

Expected: retained directory is 750 MB or less, or `storage-qa.txt` identifies the single required artifact responsible for the overage.

- [ ] **Step 4: Document the reusable workflow**

`README.md` lists exact commands for research/source logging, demo capture, voice generation, preview, check, render, contact sheet, video verification, dry cleanup, and applied cleanup. It also states which BiosRios assets are shared in place.

- [ ] **Step 5: Commit cleanup proof**

```powershell
git add -- videos/vibe-coding-dead/tools/cleanup.ps1 videos/vibe-coding-dead/README.md videos/vibe-coding-dead/renders/storage-qa.txt
git commit -m "chore: bound video production storage"
```

## Final Completion Audit

Before marking the goal complete, verify each design-spec deliverable exists and inspect the actual current artifact:

```powershell
npm run check
npm run verify:video
npm run qa:sheet
npm run cleanup:dry
git status --short
```

Open the final MP4, SRT, transcript, source manifest, contact sheet, audio QA, and storage QA. Confirm that the video is 3–5 minutes, uses the BiosRios character and approved voice clone, includes real evidence, feels like a mixed-media YouTube essay rather than marketing, and survives direct comparison with the Coding Sloth reference.
