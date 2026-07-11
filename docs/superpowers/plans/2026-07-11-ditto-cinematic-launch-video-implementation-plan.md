# Ditto Cinematic Launch Video Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, score, render, and verify a 20-second 60fps Ditto launch film that plays as a continuous Roman human/mechanical-mirror trailer rather than animated slides.

**Architecture:** Replace the current root composition with a single continuous HyperFrames timeline split into 15 full-frame shots. A small source verifier enforces duration, shot count, text limits, and the absence of voice tracks before render; the same verifier uses FFprobe to gate the final MP4. The existing Ditto engraving remains the identity anchor, while a minimal set of locally frozen scene plates, procedural ink layers, deterministic GSAP camera moves, and a mixed music/SFX master create the cinematic world.

**Tech Stack:** HyperFrames 0.7.42, HTML/CSS, GSAP, Node.js, FFmpeg/FFprobe, media-use asset resolution, image generation only for frozen engraving plates.

---

## File Map

- `videos/ditto-launch/index.html`: root 20-second composition and 15 shot containers.
- `videos/ditto-launch/cinematic.css`: materials, camera stage, characters, atmosphere, titles, and shot-specific framing.
- `videos/ditto-launch/cinematic.js`: the single paused seek-safe GSAP timeline and shot choreography.
- `videos/ditto-launch/scripts/verify-cinematic.mjs`: source and rendered-output acceptance checks.
- `videos/ditto-launch/audio_request-cinematic.json`: no-voice music and SFX request.
- `videos/ditto-launch/assets/cinema/`: frozen character and scene plates plus resolved audio.
- `videos/ditto-launch/package.json`: source verification, render verification, and 60fps render scripts.
- `videos/ditto-launch/renders/ditto-cinematic-20s.mp4`: final deliverable.
- `videos/ditto-launch/renders/cinematic-contact-sheet.jpg`: full-timeline QA sheet.

### Task 1: Add the cinematic source contract

**Files:**
- Create: `videos/ditto-launch/scripts/verify-cinematic.mjs`
- Modify: `videos/ditto-launch/package.json`

- [ ] **Step 1: Write the source verifier before changing the composition**

Create `verify-cinematic.mjs` with source checks for `data-duration="20"`, exactly 15 `data-shot` nodes, the three approved message beats, no `voice-*.wav`, no `.card`/`.folio`/`.scroll` class usage, one registered `main` timeline, and local-only media URLs. Add a `--video` branch that calls FFprobe and checks 1920×1080, 60 fps, H.264, AAC stereo, and 19.9–20.1 seconds.

```js
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

const root = path.resolve(import.meta.dirname, "..");
const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
const css = fs.readFileSync(path.join(root, "cinematic.css"), "utf8");
const js = fs.readFileSync(path.join(root, "cinematic.js"), "utf8");
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

check(/data-duration="20(?:\.0+)?"/.test(html), "root duration must be 20 seconds");
check((html.match(/data-shot=/g) || []).length === 15, "composition must contain 15 shots");
check(html.includes("YOUR AI FORGETS YOU"), "opening text beat missing");
check(html.includes("YOUR HISTORY DOESN'T"), "history text beat missing");
check(html.includes("STOP STARTING FROM ZERO"), "CTA text beat missing");
check(!/voice-\d+\.wav/i.test(html), "voiceover track is forbidden");
check(!/class="[^"]*\b(card|folio|scroll)\b/.test(html), "slide-layout classes are forbidden");
check(/window\.__timelines\["main"\]\s*=\s*tl/.test(js), "main seek-safe timeline missing");
check(!/(https?:)?\/\//.test(html.replace(/<!doctype html>/i, "")), "composition must not fetch remote media");
check(css.includes(".camera-stage"), "camera stage CSS missing");

const videoFlag = process.argv.indexOf("--video");
if (videoFlag >= 0) {
  const video = path.resolve(process.argv[videoFlag + 1]);
  const probe = JSON.parse(execFileSync("ffprobe", [
    "-v", "error", "-show_streams", "-show_format", "-of", "json", video
  ], { encoding: "utf8" }));
  const v = probe.streams.find((stream) => stream.codec_type === "video");
  const a = probe.streams.find((stream) => stream.codec_type === "audio");
  const fps = v ? Number(v.r_frame_rate.split("/")[0]) / Number(v.r_frame_rate.split("/")[1]) : 0;
  const duration = Number(probe.format.duration);
  check(v?.codec_name === "h264", "video codec must be H.264");
  check(v?.width === 1920 && v?.height === 1080, "video must be 1920x1080");
  check(Math.abs(fps - 60) < 0.01, "video must be 60 fps");
  check(a?.codec_name === "aac" && Number(a?.channels) === 2, "audio must be AAC stereo");
  check(duration >= 19.9 && duration <= 20.1, "duration must be 19.9-20.1 seconds");
}

if (failures.length) {
  console.error(failures.map((failure) => `FAIL: ${failure}`).join("\n"));
  process.exit(1);
}
console.log("cinematic verification passed");
```

- [ ] **Step 2: Add verification scripts**

Add these scripts to `package.json` while preserving existing commands:

```json
"verify:source": "node scripts/verify-cinematic.mjs",
"verify:video": "node scripts/verify-cinematic.mjs --video renders/ditto-cinematic-20s.mp4"
```

- [ ] **Step 3: Run the source verifier and confirm the old composition fails**

Run: `npm run verify:source`

Expected: FAIL for duration, shot count, approved message beats, voiceover tracks, slide-layout classes, and missing camera-stage CSS.

- [ ] **Step 4: Commit the failing contract**

```powershell
git add -- videos/ditto-launch/scripts/verify-cinematic.mjs videos/ditto-launch/package.json
git commit -m "test: define Ditto cinematic video contract"
```

### Task 2: Freeze the Roman human and mechanical twin assets

**Files:**
- Create: `videos/ditto-launch/assets/cinema/master-roman-twin.png`
- Create: `videos/ditto-launch/assets/cinema/mirror-chamber.png`
- Create: `videos/ditto-launch/assets/cinema/hand-contact.png`
- Create: `videos/ditto-launch/assets/cinema/archive-storm.png`
- Create: `videos/ditto-launch/assets/cinema/activation.png`
- Create: `videos/ditto-launch/assets/cinema/asset-notes.md`

- [ ] **Step 1: Inspect the existing identity plate at original resolution**

Run `view_image` on `videos/ditto-launch/assets/ditto-engraving.png` and record the stable identity features: paired profile silhouette, human hair mass, circular ear mechanism, machine cranial rings, and centered shoulder crop.

- [ ] **Step 2: Resolve one master character plate**

Use the existing engraving as the reference and generate a 1920×1080 copperplate scene with one Roman-era human facing a mirrored bronze mechanical twin. Require parchment, black ink, aged bronze, obsidian reflection, dark-red seal accent, consistent side profiles, and no text, columns, eagles, armor spectacle, holograms, or neon.

- [ ] **Step 3: Derive four scene plates from the same master reference**

Generate the mirror chamber wide, fingertip contact macro, manuscript archive storm, and activated synchronized twin as edits from the master rather than independent prompts. Freeze each output under the exact paths above.

- [ ] **Step 4: Inspect every plate and reject continuity failures**

Create `asset-notes.md` containing a pass/fail row for face, hair, profile, ear mechanism, palette, text contamination, and composition room for camera motion. Regenerate any plate with a failed identity field.

- [ ] **Step 5: Register the frozen plates in the media ledger**

Run `media-use resolve --from` for each exact file so `.media/manifest.jsonl` records the final local assets.

- [ ] **Step 6: Commit the approved asset set**

```powershell
git add -- videos/ditto-launch/assets/cinema videos/ditto-launch/.media
git commit -m "art: add Ditto Roman mirror scene plates"
```

### Task 3: Build the 15-shot continuous composition

**Files:**
- Replace: `videos/ditto-launch/index.html`
- Create: `videos/ditto-launch/cinematic.css`
- Create: `videos/ditto-launch/cinematic.js`

- [ ] **Step 1: Write the 20-second root and 15 full-frame shot nodes**

Use one root composition and a continuous camera stage. Every shot must be a `.clip.shot` with `data-start`, `data-duration`, `data-track-index="1"`, and `data-shot`. The timings are:

```js
const SHOTS = [
  ["eye-machine", 0.0, 0.8], ["eye-human", 0.8, 0.9],
  ["chamber-reveal", 1.7, 1.1], ["delayed-reflection", 2.8, 1.2],
  ["hand-raise", 4.0, 1.0], ["mirror-contact", 5.0, 0.8],
  ["archive-dive", 5.8, 1.2], ["noise-burn", 7.0, 1.0],
  ["history-orbit", 8.0, 1.0], ["trait-mint", 9.0, 1.4],
  ["ink-fold", 10.4, 1.4], ["you-md", 11.8, 1.2],
  ["artifact-insert", 13.0, 1.3], ["synchronized-turn", 14.3, 1.5],
  ["brand-lockup", 15.8, 4.2]
];
```

- [ ] **Step 2: Build full-frame cinematic materials**

Create CSS for `.camera-stage`, `.plate-layer`, `.ink-atmosphere`, `.torch-light`, `.obsidian`, `.film-grain`, `.vignette`, `.inscription`, `.trait-strike`, and `.brand-lockup`. Do not define or use card, folio, scroll, grid, dashboard, or UI component classes.

- [ ] **Step 3: Add the deterministic timeline skeleton**

Register a paused GSAP timeline and expose a render-time setter:

```js
window.__timelines = window.__timelines || {};
const tl = gsap.timeline({ paused: true, defaults: { ease: "power3.out" } });
gsap.set(".shot", { autoAlpha: 0 });
SHOTS.forEach(([id, start, duration]) => {
  tl.set(`#${id}`, { autoAlpha: 1 }, start);
  tl.set(`#${id}`, { autoAlpha: 0 }, start + duration);
});
tl.to({}, { duration: 20 }, 0);
window.__timelines["main"] = tl;
window.setRenderTime = (seconds) => {
  tl.seek(Math.max(0, Math.min(20, Number(seconds) || 0)), false);
  return true;
};
```

- [ ] **Step 4: Run the source verifier**

Run: `npm run verify:source`

Expected: PASS.

- [ ] **Step 5: Run HyperFrames checks**

Run: `npm run check`

Expected: lint, validate, and inspect exit 0; review and resolve every warning that affects timing, clipping, media, or determinism.

- [ ] **Step 6: Commit the composition skeleton**

```powershell
git add -- videos/ditto-launch/index.html videos/ditto-launch/cinematic.css videos/ditto-launch/cinematic.js
git commit -m "feat: rebuild Ditto as continuous cinematic composition"
```

### Task 4: Animate the empty copy and buried history

**Files:**
- Modify: `videos/ditto-launch/cinematic.css`
- Modify: `videos/ditto-launch/cinematic.js`

- [ ] **Step 1: Animate shots 1–4 as macro-to-wide cinema**

Use 120–170 percent plate scale for eye macros, a 3D pullback into the chamber wide, torch-light sweeps, and a delayed mechanical reflection. Reveal `YOUR AI FORGETS YOU` as an environmental inscription between 3.05 and 3.85 seconds.

- [ ] **Step 2: Animate shots 5–9 as one mirror fracture transition**

Orbit with the raised hand, snap into the contact macro, expand concentric fracture rings, push the camera through them, accelerate manuscript strips past the lens, bleach tool noise, retain black user-word ribbons, and curve those ribbons around the twin. Reveal `YOUR HISTORY DOESN'T` between 8.2 and 8.9 seconds.

- [ ] **Step 3: Capture diagnostic frames**

Capture 0.35, 1.25, 2.3, 3.45, 4.55, 5.35, 6.35, 7.5, and 8.55 seconds. Review at full resolution for repeated framing, flat layers, clipped faces, illegible text, or slide-like compositions.

- [ ] **Step 4: Run checks and commit**

Run: `npm run verify:source && npm run check`

```powershell
git add -- videos/ditto-launch/cinematic.css videos/ditto-launch/cinematic.js
git commit -m "feat: animate Ditto mirror and archive movements"
```

### Task 5: Animate learning, synchronization, and the brand lockup

**Files:**
- Modify: `videos/ditto-launch/cinematic.css`
- Modify: `videos/ditto-launch/cinematic.js`

- [ ] **Step 1: Animate trait minting and ink folding**

Strike `proof`, `taste`, `scope`, and `done` into bronze on separate percussion-ready frames. Make one-off fragments fall behind the focal plane. Follow one continuous ink ribbon as it folds into the `you.md` sheet.

- [ ] **Step 2: Animate artifact insertion and synchronized turn**

Compress `you.md` into a brass-and-ink artifact, insert it into the twin's chest, send light through engraved pathways, and match cut to the chamber. The human and twin must turn together on one frame-accurate event at 15.1 seconds.

- [ ] **Step 3: Animate the 4.2-second hero lockup**

Morph the two profiles into the existing Ditto engraving. Hit `Ditto` at 17.2 seconds, reveal `STOP STARTING FROM ZERO` and `github.com/ohad6k/ditto` at 18.2 seconds, and hold through 20.0 seconds.

- [ ] **Step 4: Capture diagnostic frames**

Capture 9.4, 10.9, 12.2, 13.5, 14.9, 16.4, 17.5, 18.6, and 19.8 seconds. Review continuity, type fit, final hold length, and the absence of panel layouts.

- [ ] **Step 5: Run checks and commit**

Run: `npm run verify:source && npm run check`

```powershell
git add -- videos/ditto-launch/cinematic.css videos/ditto-launch/cinematic.js
git commit -m "feat: complete Ditto learning and final lockup"
```

### Task 6: Produce the music and sound-design master

**Files:**
- Create: `videos/ditto-launch/audio_request-cinematic.json`
- Create: `videos/ditto-launch/assets/cinema/audio/bgm.wav`
- Create: `videos/ditto-launch/assets/cinema/audio/sfx-*.wav`
- Create: `videos/ditto-launch/assets/cinema/audio/ditto-cinematic-mix.wav`
- Modify: `videos/ditto-launch/index.html`

- [ ] **Step 1: Write the no-voice audio request**

Use this request shape:

```json
{
  "provider": "auto",
  "lines": [],
  "bgm": {
    "mode": "retrieve",
    "query": "dark cinematic Roman artifact trailer, 150 BPM, industrial percussion, low strings, bronze impacts, no vocals"
  }
}
```

- [ ] **Step 2: Check reusable candidates, then resolve music and SFX**

Check project and global candidates first. Resolve fresh unless the description, duration, tempo, and mood clearly fit. Resolve eye aperture, low impact, torch whoosh, mirror fracture, paper rush, ink whip, four minting strikes, brass insertion, synchronization click, and final seal impact.

- [ ] **Step 3: Build the 20-second mix**

Cut the BGM to four movements at 0.0, 4.0, 9.0, and 15.8 seconds. Place SFX on the exact visual impact frames. Use FFmpeg to mix, high-pass non-bass SFX where needed, and loudness-normalize to approximately -14 LUFS integrated and -1 dBTP true peak.

- [ ] **Step 4: Integrate one audio master**

Add a single local audio element to `index.html`:

```html
<audio src="assets/cinema/audio/ditto-cinematic-mix.wav"
  data-start="0" data-duration="20" data-track-index="10" data-volume="1"></audio>
```

- [ ] **Step 5: Verify loudness and commit**

Run FFmpeg `loudnorm` analysis and save the output in the task log. Confirm no voice track or vocal content is present.

```powershell
git add -- videos/ditto-launch/audio_request-cinematic.json videos/ditto-launch/assets/cinema/audio videos/ditto-launch/index.html videos/ditto-launch/.media
git commit -m "feat: score and sound-design Ditto cinematic film"
```

### Task 7: Render, assemble, and verify the 60fps master

**Files:**
- Create: `videos/ditto-launch/renders/ditto-cinematic-20s.mp4`
- Create: `videos/ditto-launch/renders/cinematic-contact-sheet.jpg`

- [ ] **Step 1: Run all source checks**

Run: `npm run verify:source && npm run check`

Expected: all commands exit 0.

- [ ] **Step 2: Render at 1920×1080 and 60 fps**

Use the installed HyperFrames render command if it exposes 60fps output. If it does not, render lossless PNG frames for seconds 0–20 at 60fps and assemble them with FFmpeg using H.264 High Profile, yuv420p, AAC stereo, and `-movflags +faststart`.

- [ ] **Step 3: Run the rendered-video verifier**

Run: `npm run verify:video`

Expected: `cinematic verification passed`.

- [ ] **Step 4: Generate the full contact sheet**

```powershell
ffmpeg -y -v error -i renders/ditto-cinematic-20s.mp4 -vf "fps=1,scale=480:-1,tile=5x4:padding=4:margin=4" -frames:v 1 renders/cinematic-contact-sheet.jpg
```

- [ ] **Step 5: Inspect the video and contact sheet**

Review the opening hook, all 15 shots, both message beats, `you.md`, synchronized turn, final lockup, mobile-size text, motion continuity, and sound synchronization. Any frozen, repeated, flat, or slide-like segment returns to Tasks 4–6 for correction.

- [ ] **Step 6: Commit the verified deliverable**

```powershell
git add -- videos/ditto-launch/renders/ditto-cinematic-20s.mp4 videos/ditto-launch/renders/cinematic-contact-sheet.jpg
git commit -m "render: deliver Ditto 20-second cinematic launch film"
```

### Task 8: Final acceptance audit

**Files:**
- Modify: `docs/superpowers/plans/2026-07-11-ditto-cinematic-launch-video-implementation-plan.md`

- [ ] **Step 1: Re-read the design acceptance section**

Map each requirement to direct evidence: source verifier output, HyperFrames check output, FFprobe data, loudness output, contact sheet, and full-playback review.

- [ ] **Step 2: Confirm the actual deliverable path and file size**

Run `Get-Item renders/ditto-cinematic-20s.mp4` and ensure the file is non-empty and recent.

- [ ] **Step 3: Mark plan checkboxes complete only after evidence exists**

Do not mark generated art, music, render, or QA steps complete based on source files alone.

- [ ] **Step 4: Commit the completed plan state**

```powershell
git add -- docs/superpowers/plans/2026-07-11-ditto-cinematic-launch-video-implementation-plan.md
git commit -m "docs: complete Ditto cinematic launch audit"
```
