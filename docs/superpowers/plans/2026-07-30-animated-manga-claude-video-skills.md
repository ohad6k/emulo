# Animated Manga Claude Video Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify a 25–30 second 9:16 animated manga Reel that uses Ohad's cloned voice, teases two unnamed Claude video skills, proves the claim with real BiosRios footage, and ends with a `Comment "SKILL"` CTA.

**Architecture:** Create a new HyperFrames project at `videos/short-video-skills-manga` so the failed clean-editorial attempts remain untouched. One deterministic master composition contains seven timed manga scenes driven by a single word-level voice ledger. Small Python tools generate the timeline, captions, audio cue plan, name-leak report, contact sheet, and verification report; the composition reads those generated artifacts.

**Tech Stack:** HyperFrames 0.7.78, deterministic HTML/CSS/SVG, GSAP 3.14.2, Python 3.11, Chatterbox TTS, Whisper, FFmpeg/FFprobe, pytest, PowerShell.

**Resolution decision:** Render the delivery master at 1080 × 1920 because the retained proof footage is 1080 × 1920 and the approved character art is 1254 × 1254. A 2160 × 3840 encode would only upscale those sources. Manga borders, ink, type, halftone, hatching, and arrows remain vector/CSS so the drawing itself stays crisp.

---

## File Map

Create this project without modifying `videos/short-videoskill` or `videos/short-motionskill`.

```text
videos/short-video-skills-manga/
├── BRIEF.md                         # Automation brief and accepted creative decisions
├── DESIGN.md                        # Visual truth: palette, type, panel, and character rules
├── STORYBOARD.md                    # Seven exact scene dispatch blocks
├── script.md                        # Eight cloned-voice lines
├── hyperframes.json                 # HyperFrames asset/component paths
├── package.json                     # Pinned HyperFrames commands
├── index.html.tpl                   # Authored deterministic composition
├── index.html                       # Generated composition with measured timings injected
├── captions.html                    # Generated kinetic-caption clips
├── assets/
│   ├── manifest.json                # Provenance and role for every retained asset
│   ├── timeline.json                # Voice, scene, word, and total timing ledger
│   ├── cue-plan.json                # Audio events bound to visible DOM anchors
│   ├── final_mix.wav                # VO, fresh score, and causal SFX
│   ├── characters/                  # Adopted polished BiosRios poses
│   ├── fonts/                       # Archivo Black and Consolas
│   ├── proof/                       # Real moving BiosRios output
│   ├── sfx/                         # Real impact, paper, ink, UI, and notification sounds
│   ├── vo/                          # Selected cloned-voice lines and metadata
│   ├── vo-takes/                    # Auditable generated takes and transcripts
│   ├── vref/clean_calm.wav          # Existing Ohad voice reference
│   └── wordts/                      # Whisper word timings per line
├── tools/
│   ├── gen_voice.py                 # Clone generation and clarity selection
│   ├── timeline.py                  # Build timing ledger from selected VO
│   ├── capsync.py                   # Add Whisper word offsets to the ledger
│   ├── gen_captions.py              # Build phrase captions
│   ├── events.py                    # Single source for picture and SFX events
│   ├── inject.py                    # Resolve measured timing tokens into index.html
│   ├── gen_score.py                 # Fresh prompt-driven score
│   ├── assemble_mix.py              # Duck music and attach SFX to visible causes
│   ├── leak_scan.py                 # Reject hidden skill-name leaks
│   ├── contact.py                   # Render scene-midpoint contact sheet
│   ├── verify.py                    # Container, duration, loudness, sync, freeze, CTA gates
│   └── render.ps1                   # D-drive-safe render and mux
├── tests/
│   ├── test_timeline.py
│   ├── test_leak_scan.py
│   ├── test_composition_contract.py
│   └── test_events.py
├── qa/
│   ├── contact-sheet.jpg
│   ├── scene-midpoints/
│   └── verification.json
└── renders/
    └── biosrios-video-skills-manga-1080x1920.mp4
```

### Task 1: Scaffold the isolated HyperFrames project

**Files:**

- Create: `videos/short-video-skills-manga/BRIEF.md`
- Create: `videos/short-video-skills-manga/DESIGN.md`
- Create: `videos/short-video-skills-manga/STORYBOARD.md`
- Create: `videos/short-video-skills-manga/hyperframes.json`
- Create: `videos/short-video-skills-manga/package.json`
- Create directories listed in the file map

- [ ] **Step 1: Confirm the source projects and design checkpoint exist**

Run:

```powershell
Test-Path 'docs/superpowers/specs/2026-07-30-animated-manga-claude-video-skills-design.md'
Test-Path 'videos/short-motionskill/assets/vref/clean_calm.wav'
Test-Path 'videos/short-motionskill/assets/footage-finished.mp4'
Test-Path 'videos/_brand/character/polished/pointing.png'
```

Expected: four `True` values.

- [ ] **Step 2: Update the required video workflow skills**

Run:

```powershell
npx hyperframes skills update hyperframes
npx hyperframes skills update general-video
```

Expected: both commands exit 0. Stop and report the exact update error if either fails.

- [ ] **Step 3: Scaffold the project**

Run:

```powershell
npx hyperframes init 'videos/short-video-skills-manga' --non-interactive --example=blank --skill=general-video
```

Expected: `videos/short-video-skills-manga/hyperframes.json` exists and no file outside that directory changes.

- [ ] **Step 4: Write the accepted brief**

Create `BRIEF.md` with these exact decisions:

```markdown
---
title: Claude video skills, animated manga
workflow: general-video
flow: automation
storyboard: no
canvas: 1080x1920
fps: 60
duration: voice-led, 25-30 seconds
---

# Goal

Tease two unnamed Claude video skills through a cinematic moving-comic Reel.

# Required

- Ohad cloned voice
- full-reel animated manga language
- real BiosRios moving footage as proof
- polished white BiosRios character
- CTA: Comment "SKILL" and I'll send you the exact setup.
- never show or say the two skill names

# Excluded

- face clone
- fake product UI
- purple, glass, 3D emoji, glossy gradients
- generic wipes or static slideshow cards
```

- [ ] **Step 5: Write the visual truth**

Create `DESIGN.md`:

```markdown
# Animated Manga Visual Truth

- Ground: warm paper `#F5F1E8`
- Ink: near-black `#151515`
- Accent: BiosRios coral `#F06449`
- Secondary ink: `#6A6761`
- Display: Archivo Black
- Code: Consolas
- Primary device: hand-drawn panel borders and controlled halftone
- Motion: panel travel, ink draw-on, match cut, camera push, page split
- Character: existing polished white BiosRios set only
- Proof: real moving footage remains full-color and readable inside ink frames
- Caption: two to five words, high contrast, never over a face or proof object
```

- [ ] **Step 6: Write seven storyboard dispatch blocks**

Create `STORYBOARD.md` with `## Frame s01` through `## Frame s07`. Each block must declare:

```markdown
## Frame s01
status: outline
src: compositions/s01.html
timing: V01
motion: ink reveal + three proof cuts + camera push
beat: CLAUDE MADE THIS
```

Use these remaining exact mappings:

```text
s02 -> V02 -> character paper-break + mystery-card orbit -> THE RIGHT SKILLS
s03 -> V03 -> code-to-motion morph + three sequential panels -> FRAME PERFECT MOTION
s04 -> V04,V05 -> continuous production-line camera travel -> SCRIPT TO FINAL RENDER
s05 -> tail V05 -> moving proof triptych + border break -> REAL OUTPUT
s06 -> V06,V07 -> pull back into self-referential timeline -> YOU'RE WATCHING THE PROOF
s07 -> V08 -> coral impact page + character + speech-bubble draw -> COMMENT "SKILL"
```

- [ ] **Step 7: Pin the local render commands**

Create `package.json`:

```json
{
  "name": "biosrios-video-skills-manga",
  "private": true,
  "type": "module",
  "scripts": {
    "check": "npx --yes hyperframes@0.7.78 check",
    "preview": "npx --yes hyperframes@0.7.78 preview",
    "render": "powershell -ExecutionPolicy Bypass -File tools/render.ps1",
    "test": "python -m pytest tests -q"
  }
}
```

- [ ] **Step 8: Commit the scaffold**

```powershell
git add -- 'videos/short-video-skills-manga/BRIEF.md' 'videos/short-video-skills-manga/DESIGN.md' 'videos/short-video-skills-manga/STORYBOARD.md' 'videos/short-video-skills-manga/hyperframes.json' 'videos/short-video-skills-manga/package.json'
git commit -m 'feat(video): scaffold animated manga reel'
```

Expected: the commit contains only the five project files.

### Task 2: Build the voice-led timeline with TDD

**Files:**

- Create: `videos/short-video-skills-manga/tests/test_timeline.py`
- Create: `videos/short-video-skills-manga/script.md`
- Create: `videos/short-video-skills-manga/tools/timeline.py`
- Generate: `videos/short-video-skills-manga/assets/timeline.json`

- [ ] **Step 1: Write the failing timeline tests**

Create `tests/test_timeline.py`:

```python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def timeline():
    return json.loads((ROOT / "assets/timeline.json").read_text(encoding="utf-8"))


def test_timeline_is_vertical_reel_length():
    data = timeline()
    assert 25.0 <= data["total"] <= 30.0
    assert list(data["lines"]) == [f"V{i:02d}" for i in range(1, 9)]


def test_voice_lines_do_not_overlap():
    rows = list(timeline()["lines"].values())
    for current, following in zip(rows, rows[1:]):
        assert current["start"] + current["dur"] <= following["start"]


def test_cta_has_readable_tail():
    data = timeline()
    cta = data["lines"]["V08"]
    assert data["total"] - (cta["start"] + cta["dur"]) >= 1.2
```

- [ ] **Step 2: Run the tests and confirm the expected failure**

Run:

```powershell
python -m pytest 'videos/short-video-skills-manga/tests/test_timeline.py' -q
```

Expected: FAIL because `assets/timeline.json` does not exist.

- [ ] **Step 3: Write the final eight-line script**

Create `script.md`:

```markdown
# Voiceover

VO V01: Claude can make videos like this.
VO V02: But it needs the right skills.
VO V03: One turns code into frame-perfect animation.
VO V04: The other makes Claude direct the whole thing.
VO V05: Script, storyboard, motion, captions, sound, and the final render.
VO V06: I used both to make this.
VO V07: You're watching the proof right now.
VO V08: Comment skill and I'll send you the exact setup.
```

- [ ] **Step 4: Add the timeline generator**

Create `tools/timeline.py`:

```python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "assets/vo/meta.json"
OUT = ROOT / "assets/timeline.json"
ORDER = [f"V{i:02d}" for i in range(1, 9)]
GAPS = {"V01": 0.20, "V02": 0.16, "V03": 0.18, "V04": 0.12,
        "V05": 0.12, "V06": 0.16, "V07": 0.18, "V08": 0.00}


def build(meta):
    t = 0.18
    lines = {}
    for line_id in ORDER:
        rec = meta[line_id]
        lines[line_id] = {
            "start": round(t, 3),
            "dur": round(float(rec["dur"]), 3),
            "text": rec["text"],
        }
        t += float(rec["dur"]) + GAPS[line_id]
    return {
        "lines": lines,
        "total": round(t + 1.25, 3),
        "proof_holds": [],
    }


if __name__ == "__main__":
    data = build(json.loads(META.read_text(encoding="utf-8")))
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"timeline: {data['total']:.2f}s")
```

- [ ] **Step 5: Seed only a temporary test metadata file**

Create `assets/vo/meta.json` with measured-shape test durations:

```json
{
  "V01": {"dur": 2.50, "text": "Claude can make videos like this."},
  "V02": {"dur": 2.25, "text": "But it needs the right skills."},
  "V03": {"dur": 3.20, "text": "One turns code into frame-perfect animation."},
  "V04": {"dur": 2.95, "text": "The other makes Claude direct the whole thing."},
  "V05": {"dur": 4.00, "text": "Script, storyboard, motion, captions, sound, and the final render."},
  "V06": {"dur": 2.30, "text": "I used both to make this."},
  "V07": {"dur": 2.65, "text": "You're watching the proof right now."},
  "V08": {"dur": 3.00, "text": "Comment skill and I'll send you the exact setup."}
}
```

Run:

```powershell
python 'videos/short-video-skills-manga/tools/timeline.py'
python -m pytest 'videos/short-video-skills-manga/tests/test_timeline.py' -q
```

Expected: `3 passed`. The temporary metadata is replaced by real generated voice metadata in Task 4.

- [ ] **Step 6: Commit the timeline contract**

```powershell
git add -- 'videos/short-video-skills-manga/script.md' 'videos/short-video-skills-manga/tools/timeline.py' 'videos/short-video-skills-manga/tests/test_timeline.py'
git commit -m 'test(video): lock voice-led reel timing'
```

Do not commit generated voice or temporary metadata.

### Task 3: Add a hard name-leak gate

**Files:**

- Create: `videos/short-video-skills-manga/tests/test_leak_scan.py`
- Create: `videos/short-video-skills-manga/tools/leak_scan.py`

- [ ] **Step 1: Write the failing leak tests**

Create `tests/test_leak_scan.py`:

```python
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from leak_scan import scan_text


def test_rejects_hidden_skill_names_case_insensitively():
    assert scan_text("Built with REMOTION") == ["remotion"]
    assert scan_text("hyperFrames project") == ["hyperframes"]


def test_allows_public_script():
    text = (ROOT / "script.md").read_text(encoding="utf-8")
    assert scan_text(text) == []
```

- [ ] **Step 2: Run the test and confirm the expected failure**

Run:

```powershell
python -m pytest 'videos/short-video-skills-manga/tests/test_leak_scan.py' -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'leak_scan'`.

- [ ] **Step 3: Implement the scanner**

Create `tools/leak_scan.py`:

```python
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANNED = ("remotion", "hyperframes")
VISIBLE = (
    ROOT / "script.md",
    ROOT / "index.html",
    ROOT / "captions.html",
    ROOT / "assets/timeline.json",
)
VISIBLE_ASSET_SUFFIXES = {".svg", ".vtt", ".srt", ".txt"}


def scan_text(text):
    lowered = text.lower()
    return [word for word in BANNED if re.search(rf"\b{re.escape(word)}\b", lowered)]


def scan_project():
    hits = []
    candidates = [path for path in VISIBLE if path.exists()]
    candidates += [
        path for path in (ROOT / "assets").rglob("*")
        if path.is_file() and path.suffix.lower() in VISIBLE_ASSET_SUFFIXES
    ]
    for path in candidates:
        found = scan_text(path.read_text(encoding="utf-8", errors="ignore"))
        if found:
            hits.append({"path": str(path.relative_to(ROOT)), "words": found})
    return hits


if __name__ == "__main__":
    hits = scan_project()
    print(json.dumps({"hits": hits}, indent=2))
    raise SystemExit(1 if hits else 0)
```

- [ ] **Step 4: Run the gate**

Run:

```powershell
python -m pytest 'videos/short-video-skills-manga/tests/test_leak_scan.py' -q
python 'videos/short-video-skills-manga/tools/leak_scan.py'
```

Expected: tests pass and scanner prints `"hits": []`.

- [ ] **Step 5: Commit the leak gate**

```powershell
git add -- 'videos/short-video-skills-manga/tests/test_leak_scan.py' 'videos/short-video-skills-manga/tools/leak_scan.py'
git commit -m 'test(video): block skill-name leaks'
```

### Task 4: Generate and clarity-gate Ohad's cloned voice

**Files:**

- Create: `videos/short-video-skills-manga/tools/gen_voice.py`
- Copy: `videos/short-video-skills-manga/assets/vref/clean_calm.wav`
- Generate: `videos/short-video-skills-manga/assets/vo/*.wav`
- Generate: `videos/short-video-skills-manga/assets/vo/meta.json`
- Generate: `videos/short-video-skills-manga/assets/wordts/*.json`

- [ ] **Step 1: Adopt the existing voice reference**

Run:

```powershell
Copy-Item -LiteralPath 'videos/short-motionskill/assets/vref/clean_calm.wav' -Destination 'videos/short-video-skills-manga/assets/vref/clean_calm.wav'
```

Expected: the copied file has the same SHA-256 as the source.

- [ ] **Step 2: Reuse the proven generator and change only project-specific energy IDs**

Copy:

```powershell
Copy-Item -LiteralPath 'videos/short-motionskill/tools/gen_voice.py' -Destination 'videos/short-video-skills-manga/tools/gen_voice.py'
```

In the copied file set:

```python
HIGH_ENERGY = {"V01", "V08"}
MID_LIFT = {"V03", "V05", "V07"}
```

Keep root-relative paths, Chatterbox selection, `atempo=1.06`, and Whisper clarity scoring unchanged.

- [ ] **Step 3: Generate real takes**

Run:

```powershell
& 'D:\ditto\.voice-venv\Scripts\python.exe' 'videos/short-video-skills-manga/tools/gen_voice.py'
```

Expected:

- eight selected WAV files;
- every selected line has clarity `>= 0.88`;
- `V01` and `V08` have clarity `>= 0.95`;
- no line is missing from `assets/vo/meta.json`.

- [ ] **Step 4: Rebuild the real timeline**

Run:

```powershell
python 'videos/short-video-skills-manga/tools/timeline.py'
python -m pytest 'videos/short-video-skills-manga/tests/test_timeline.py' -q
```

Expected: timeline tests pass with actual duration between 25 and 30 seconds. If it is outside range, tighten script wording or voice tempo and regenerate affected lines; do not falsify durations in JSON.

- [ ] **Step 5: Add word timings**

Copy the root-relative `capsync.py` from `videos/short-motionskill/tools/capsync.py`, then run:

```powershell
python 'videos/short-video-skills-manga/tools/capsync.py'
```

Expected: every timeline line contains a non-empty `words` array and `assets/wordts/V01.json` through `V08.json` exist.

- [ ] **Step 6: Listen to all selected lines**

Play `V01.wav`, `V03.wav`, `V05.wav`, and `V08.wav` in full. Then inspect the remaining four. Reject any take that changes the meaning, swallows `Claude`, `frame-perfect`, or `skill`, or sounds unlike Ohad even if the automated clarity score passes.

- [ ] **Step 7: Commit the reproducible voice tooling**

```powershell
git add -- 'videos/short-video-skills-manga/tools/gen_voice.py' 'videos/short-video-skills-manga/tools/capsync.py'
git commit -m 'feat(video): add cloned voice pipeline'
```

Do not commit generated takes until the final retained-asset cleanup.

### Task 5: Stage real proof and manga production assets

**Files:**

- Create: `videos/short-video-skills-manga/assets/manifest.json`
- Populate: `assets/characters`, `assets/fonts`, `assets/proof`, `assets/sfx`
- Create: `videos/short-video-skills-manga/tests/test_asset_manifest.py`

- [ ] **Step 1: Write the failing manifest test**

Create `tests/test_asset_manifest.py`:

```python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_every_manifest_asset_exists_and_has_a_role():
    data = json.loads((ROOT / "assets/manifest.json").read_text(encoding="utf-8"))
    assert len(data["assets"]) >= 14
    for item in data["assets"]:
        assert item["role"]
        assert (ROOT / item["path"]).is_file(), item["path"]


def test_proof_is_moving_video_not_a_poster():
    data = json.loads((ROOT / "assets/manifest.json").read_text(encoding="utf-8"))
    proof = [x for x in data["assets"] if x["role"] == "moving-proof"]
    assert proof and all(Path(x["path"]).suffix.lower() == ".mp4" for x in proof)
```

- [ ] **Step 2: Run the test and confirm the expected failure**

Run:

```powershell
python -m pytest 'videos/short-video-skills-manga/tests/test_asset_manifest.py' -q
```

Expected: FAIL because `assets/manifest.json` is missing.

- [ ] **Step 3: Adopt the approved character poses**

Copy these exact files from `videos/_brand/character/polished/`:

```text
pointing.png
mindblown.png
typing.png
thinking.png
thumbsup.png
hero.png
```

Preserve alpha. Record each source path and SHA-256 in `assets/manifest.json`.

- [ ] **Step 4: Adopt fonts, proof footage, and SFX**

Copy:

```text
videos/biosrios-claude-vs-codex-shorts/assets/fonts/ArchivoBlack-Regular.ttf
videos/biosrios-claude-vs-codex-shorts/assets/fonts/Consolas-Regular.ttf
videos/short-motionskill/assets/footage-finished.mp4
videos/short-motionskill/assets/screens/contact-sheet.png
videos/short-motionskill/assets/sfx/air.wav
videos/short-motionskill/assets/sfx/boom.wav
videos/short-motionskill/assets/sfx/hit2.wav
videos/short-motionskill/assets/sfx/keys.wav
videos/short-motionskill/assets/sfx/revsw.wav
videos/short-motionskill/assets/sfx/sw2.wav
videos/short-motionskill/assets/sfx/thud.wav
videos/short-motionskill/assets/sfx/tick2.wav
```

Roles:

```text
footage-finished.mp4 -> moving-proof
contact-sheet.png -> proof-index
character PNGs -> character
fonts -> font
SFX -> causal-sfx
```

- [ ] **Step 5: Create the manifest**

Generate the manifest from the staged files so every hash is real:

```powershell
$projectRoot = (Resolve-Path 'videos/short-video-skills-manga').Path
$roles = @{'.mp4'='moving-proof';'.png'='character';'.ttf'='font';'.wav'='causal-sfx'}
$files = @(
  Get-ChildItem -LiteralPath (Join-Path $projectRoot 'assets/characters') -File
  Get-ChildItem -LiteralPath (Join-Path $projectRoot 'assets/fonts') -File
  Get-ChildItem -LiteralPath (Join-Path $projectRoot 'assets/proof') -File
  Get-ChildItem -LiteralPath (Join-Path $projectRoot 'assets/sfx') -File
)
$assets = foreach($file in $files) {
  $relative = $file.FullName.Substring($projectRoot.Length + 1).Replace('\','/')
  $role = if($file.Name -eq 'contact-sheet.png') {'proof-index'} else {$roles[$file.Extension.ToLowerInvariant()]}
  [ordered]@{
    path=$relative
    source='adopted-local'
    role=$role
    sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
  }
}
[ordered]@{assets=@($assets)} | ConvertTo-Json -Depth 5 |
  Set-Content -LiteralPath (Join-Path $projectRoot 'assets/manifest.json') -Encoding utf8
```

- [ ] **Step 6: Run asset tests and inspect the character sheet**

Run:

```powershell
python -m pytest 'videos/short-video-skills-manga/tests/test_asset_manifest.py' -q
magick montage 'videos/short-video-skills-manga/assets/characters/*.png' -tile 3x2 -geometry '420x420+12+12' 'videos/short-video-skills-manga/qa/character-sheet.png'
```

Expected: tests pass; all six poses show the same character with intact transparency and no soft upscaling.

- [ ] **Step 7: Commit the manifest and retained source assets**

```powershell
git add -- 'videos/short-video-skills-manga/assets/manifest.json' 'videos/short-video-skills-manga/assets/characters' 'videos/short-video-skills-manga/assets/fonts' 'videos/short-video-skills-manga/tests/test_asset_manifest.py'
git commit -m 'feat(video): stage manga character and proof assets'
```

Do not commit large proof video or generated QA sheets until cleanup decides the retained set.

### Task 6: Build the deterministic seven-scene manga composition

**Files:**

- Create: `videos/short-video-skills-manga/tests/test_composition_contract.py`
- Create: `videos/short-video-skills-manga/index.html.tpl`
- Create: `videos/short-video-skills-manga/tools/inject.py`
- Create: `videos/short-video-skills-manga/captions.html`
- Generate: `videos/short-video-skills-manga/index.html`

- [ ] **Step 1: Write the failing composition contract**

Create `tests/test_composition_contract.py`:

```python
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source():
    return (ROOT / "index.html").read_text(encoding="utf-8")


def test_composition_has_seven_timed_scenes():
    html = source()
    scenes = re.findall(r'id="scene-s0[1-7]" class="clip scene(?: [^"]*)?"', html)
    assert len(scenes) == 7


def test_composition_registers_one_paused_timeline():
    html = source()
    assert 'gsap.timeline({ paused: true })' in html
    assert 'window.__timelines["video-skills-manga"] = tl' in html


def test_real_proof_is_a_video_element():
    html = source()
    assert '<video id="proof-video"' in html
    assert 'assets/proof/footage-finished.mp4' in html


def test_character_is_not_bottom_locked():
    html = source()
    assert 'id="character-pointing"' in html
    assert 'id="character-cta"' in html
    assert 'data-position="left"' in html
    assert 'data-position="right"' in html
```

- [ ] **Step 2: Run the test and confirm the expected failure**

Run:

```powershell
python -m pytest 'videos/short-video-skills-manga/tests/test_composition_contract.py' -q
```

Expected: FAIL because `index.html` is missing.

- [ ] **Step 3: Author the root composition contract**

In `index.html.tpl`, use this exact root and scene structure:

```html
<div id="root"
     data-composition-id="video-skills-manga"
     data-start="0"
     data-duration="{{TOTAL}}"
     data-width="1080"
     data-height="1920"
     data-fps="60">
  <video id="proof-video" src="assets/proof/footage-finished.mp4" muted></video>
  <section id="scene-s01" class="clip scene manga-paper" data-start="{{S01}}" data-duration="{{D01}}" data-track-index="1">
    <svg id="s01-ink" class="ink-overlay" viewBox="0 0 1080 1920"><path d="M70 310 C260 160 760 210 1010 90 M40 1540 C350 1700 710 1650 1050 1820"/></svg>
    <div class="proof-strip">
      <div id="s01-proof-a" class="proof-panel"></div>
      <div id="s01-proof-b" class="proof-panel"></div>
      <div id="s01-proof-c" class="proof-panel"></div>
    </div>
    <h1>CLAUDE MADE <em>THIS</em></h1>
  </section>
  <section id="scene-s02" class="clip scene manga-paper" data-start="{{S02}}" data-duration="{{D02}}" data-track-index="2">
    <img id="character-pointing" data-position="left" class="character" src="assets/characters/pointing.png" alt="">
    <div id="mystery-card-a" class="mystery-card">01</div>
    <div id="mystery-card-b" class="mystery-card">02</div>
    <h2>THE RIGHT<br>SKILLS</h2>
  </section>
  <section id="scene-s03" class="clip scene manga-paper" data-start="{{S03}}" data-duration="{{D03}}" data-track-index="3">
    <div id="s03-code" class="code-panel"><div id="s03-code-mask">scene({ motion: "frame-perfect" })</div></div>
    <div id="s03-panel-a" class="motion-panel">CODE</div>
    <div id="s03-motion" class="motion-panel coral">MOTION</div>
    <img class="character character-small" src="assets/characters/typing.png" alt="">
  </section>
  <section id="scene-s04" class="clip scene manga-paper" data-start="{{S04}}" data-duration="{{D04}}" data-track-index="4">
    <div id="s04-page" class="production-page">
      <article id="s04-script">SCRIPT</article><article id="s04-storyboard">STORYBOARD</article>
      <article id="s04-motion">MOTION</article><article id="s04-captions">CAPTIONS</article>
      <article id="s04-waveform">SOUND</article><article id="s04-render">FINAL RENDER</article>
    </div>
  </section>
  <section id="scene-s05" class="clip scene manga-paper" data-start="{{S05}}" data-duration="{{D05}}" data-track-index="5">
    <div id="proof-video-frame" class="triptych-frame"></div>
    <svg class="ink-arrow" viewBox="0 0 500 220"><path d="M20 180 Q210 10 470 100"/><path d="M430 65 L470 100 L420 120"/></svg>
    <b>REAL OUTPUT</b>
  </section>
  <section id="scene-s06" class="clip scene manga-paper" data-start="{{S06}}" data-duration="{{D06}}" data-track-index="6">
    <div id="s06-camera" class="meta-camera">
      <div class="manga-timeline"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
      <div id="s06-playhead" class="playhead"></div>
      <h2>YOU'RE WATCHING<br>THE PROOF</h2>
    </div>
  </section>
  <section id="scene-s07" class="clip scene coral-page" data-start="{{S07}}" data-duration="{{D07}}" data-track-index="7">
    <img id="character-cta" data-position="right" class="character" src="assets/characters/thumbsup.png" alt="">
    <svg id="cta-ink" class="speech-bubble" viewBox="0 0 720 520"><path d="M30 40 H690 V410 H250 L145 495 L170 410 H30 Z"/></svg>
    <div class="cta-copy">COMMENT<br><strong id="cta-keyword">"SKILL"</strong><small>I'LL SEND BOTH</small></div>
  </section>
</div>
```

Root and all relevant ancestors must be explicitly sized to `1080px × 1920px`. Every timed element must use `class="clip"`.

- [ ] **Step 4: Implement the seven final visual states**

Use these exact focal elements:

```text
s01: three torn proof panels + CLAUDE MADE THIS + coral ink slash
s02: pointing character on left + two mystery cards on right + THE RIGHT SKILLS
s03: typed code panel left -> motion poses right + FRAME PERFECT MOTION
s04: oversized horizontal production page with script, storyboard, motion, captions, waveform, render
s05: proof-video in a moving triptych + REAL OUTPUT + hand-drawn arrows
s06: self-referential manga timeline + moving playhead + YOU'RE WATCHING THE PROOF
s07: coral page + right-side thumbs-up character + speech bubble COMMENT "SKILL"
```

Use CSS/SVG for panel borders, halftone, hatching, ink masks, arrows, speed lines, and speech bubbles. Do not rasterize text or draw fake product UI.

Add this deterministic base to the document `<style>` and extend only with scene-specific coordinates:

```css
@font-face{font-family:Archivo;src:url("assets/fonts/ArchivoBlack-Regular.ttf")}
@font-face{font-family:Code;src:url("assets/fonts/Consolas-Regular.ttf")}
*{box-sizing:border-box}
html,body,#root{width:1080px;height:1920px;margin:0;overflow:hidden}
#root{position:relative;background:#f5f1e8;color:#151515;font-family:Archivo,sans-serif}
.scene{position:absolute;inset:0;overflow:hidden}
.manga-paper{background-color:#f5f1e8;background-image:radial-gradient(#6a6761 1px,transparent 1.3px);background-size:14px 14px}
.coral-page{background:#f06449}
.character{position:absolute;width:720px;filter:drop-shadow(15px 18px 0 rgba(21,21,21,.18))}
.character-small{width:470px}
.proof-strip{position:absolute;inset:280px 60px 360px;display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.proof-panel,.motion-panel,.mystery-card,.production-page article{border:6px solid #151515;background:#fffdf8;box-shadow:14px 14px 0 #151515}
.production-page{position:absolute;left:0;top:270px;width:4320px;height:1260px;display:grid;grid-template-columns:repeat(6,620px);gap:70px;padding:90px}
.production-page article{display:grid;place-items:center;font-size:62px}
#proof-video{position:absolute;z-index:3;left:90px;top:270px;width:900px;height:1250px;object-fit:cover;visibility:hidden}
.triptych-frame{position:absolute;z-index:4;left:70px;top:250px;width:940px;height:1290px;border:8px solid #151515;pointer-events:none}
.ink-overlay path,.ink-arrow path,.speech-bubble path{fill:none;stroke:#151515;stroke-width:18;stroke-linecap:round;stroke-linejoin:round}
.ink-overlay path{stroke-dasharray:1600;stroke-dashoffset:1600}
.speech-bubble path{fill:#fffdf8;stroke-dasharray:1300;stroke-dashoffset:1300}
.cta-copy{position:absolute;z-index:5;left:80px;top:370px;width:650px;font-size:104px;line-height:.85}
.cta-copy strong{display:block;font-size:150px}
.cta-copy small{display:block;margin-top:30px;font-size:36px}
```

- [ ] **Step 5: Implement the motion at word anchors**

Create one paused timeline:

```javascript
const tl = gsap.timeline({ paused: true });
tl.fromTo("#s01-ink", { strokeDashoffset: 1600 }, { strokeDashoffset: 0, duration: .32, ease: "power3.out" }, {{W01_CLAUDE}});
tl.fromTo("#s01-proof-a", { scale: 1.28, opacity: 0 }, { scale: 1, opacity: 1, duration: .26, ease: "power4.out" }, {{S01}});
tl.fromTo("#character-pointing", { x: -520, y: 120, scale: .72, rotation: -8 }, { x: 0, y: 0, scale: 1, rotation: 0, duration: .42, ease: "back.out(1.7)" }, {{S02}});
tl.fromTo("#s03-code-mask", { scaleX: 0 }, { scaleX: 1, duration: .6, ease: "steps(12)" }, {{S03}});
tl.to("#s04-page", { x: -3240, duration: {{D04}}, ease: "none" }, {{S04}});
tl.set("#proof-video", { visibility: "visible" }, {{S05}});
tl.fromTo("#proof-video-frame", { scale: 1.16, rotation: -2 }, { scale: 1, rotation: 0, duration: {{D05}}, ease: "power1.out" }, {{S05}});
tl.set("#proof-video", { visibility: "hidden" }, {{S06}});
tl.fromTo("#s06-camera", { scale: 2.2, x: -240, y: 310 }, { scale: 1, x: 0, y: 0, duration: .72, ease: "power3.inOut" }, {{S06}});
tl.fromTo("#character-cta", { x: 520, scale: .72, rotation: 7 }, { x: 0, scale: 1, rotation: 0, duration: .4, ease: "back.out(1.8)" }, {{S07}});
tl.fromTo("#cta-ink", { strokeDashoffset: 1300 }, { strokeDashoffset: 0, duration: .38, ease: "power2.out" }, {{W08_SKILL}});
window.__timelines["video-skills-manga"] = tl;
```

Add at least one meaningful visual response every 0.7–1.3 seconds. Animate real proof media with `tl.set` visibility and continuous playback-safe placement; do not nest the video inside another timed element.

- [ ] **Step 6: Add deterministic timing injection**

Create `tools/inject.py`:

```python
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TL = json.loads((ROOT / "assets/timeline.json").read_text(encoding="utf-8"))
LINES = TL["lines"]
SCENE_FIRST = ["V01", "V02", "V03", "V04", "V05", "V06", "V08"]


def word_time(line_id, wanted):
    for spoken, offset in LINES[line_id]["words"]:
        if spoken == wanted:
            return round(LINES[line_id]["start"] + float(offset), 3)
    raise SystemExit(f"word anchor missing: {line_id}:{wanted}")


tokens = {"TOTAL": TL["total"]}
for index, line_id in enumerate(SCENE_FIRST, start=1):
    start = float(LINES[line_id]["start"])
    next_start = (
        float(LINES[SCENE_FIRST[index]]["start"])
        if index < len(SCENE_FIRST)
        else float(TL["total"])
    )
    tokens[f"S{index:02d}"] = round(start, 3)
    tokens[f"D{index:02d}"] = round(next_start - start, 3)

tokens["W01_CLAUDE"] = word_time("V01", "claude")
tokens["W08_SKILL"] = word_time("V08", "skill")
rendered = (ROOT / "index.html.tpl").read_text(encoding="utf-8")
for key, value in tokens.items():
    rendered = rendered.replace("{{" + key + "}}", str(value))
unresolved = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", rendered)))
if unresolved:
    raise SystemExit(f"unresolved tokens: {unresolved}")
(ROOT / "index.html").write_text(rendered, encoding="utf-8")
print(f"wrote index.html ({TL['total']:.2f}s)")
```

- [ ] **Step 7: Generate and run the contract**

Run:

```powershell
python 'videos/short-video-skills-manga/tools/inject.py'
python -m pytest 'videos/short-video-skills-manga/tests/test_composition_contract.py' -q
python 'videos/short-video-skills-manga/tools/leak_scan.py'
```

Expected: all tests pass and no name leaks.

- [ ] **Step 8: Commit the composition**

```powershell
git add -- 'videos/short-video-skills-manga/index.html.tpl' 'videos/short-video-skills-manga/tools/inject.py' 'videos/short-video-skills-manga/tests/test_composition_contract.py'
git commit -m 'feat(video): build animated manga composition'
```

Do not commit the generated `index.html` until final QA.

### Task 7: Bind kinetic captions and causal sound to the same events

**Files:**

- Create: `videos/short-video-skills-manga/tests/test_events.py`
- Create: `videos/short-video-skills-manga/tools/events.py`
- Create: `videos/short-video-skills-manga/tools/gen_captions.py`
- Create: `videos/short-video-skills-manga/tools/gen_score.py`
- Create: `videos/short-video-skills-manga/tools/assemble_mix.py`
- Generate: `videos/short-video-skills-manga/assets/cue-plan.json`
- Generate: `videos/short-video-skills-manga/assets/music.wav`
- Generate: `videos/short-video-skills-manga/assets/final_mix.wav`

- [ ] **Step 1: Write the failing event tests**

Create `tests/test_events.py`:

```python
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from events import events


def test_event_density_and_anchor_uniqueness():
    rows = events()
    times = [row["time"] for row in rows]
    assert len(rows) >= 16
    assert times == sorted(times)
    assert len({row["anchor"] for row in rows}) == len(rows)


def test_no_designed_cue_hits_first_word():
    rows = events()
    line_starts = [row["time"] for row in rows if row["kind"] == "voice-start"]
    designed = [row["time"] for row in rows if row["kind"] != "voice-start"]
    for cue in designed:
        assert all(not (-0.05 <= cue - start <= 0.28) for start in line_starts)
```

- [ ] **Step 2: Implement the event ledger**

Create `tools/events.py` with:

```python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def events():
    tl = json.loads((ROOT / "assets/timeline.json").read_text(encoding="utf-8"))
    lines = tl["lines"]

    def start(line):
        return lines[line]["start"]

    def word(line, token):
        for spoken, offset in lines[line]["words"]:
            if spoken == token:
                return round(start(line) + offset, 3)
        raise KeyError(f"{line}:{token}")

    rows = [
        {"time": start(line), "kind": "voice-start", "anchor": f"@voice-{line}"}
        for line in lines
    ] + [
        {"time": word("V01", "claude") - .08, "kind": "impact", "anchor": "#s01-ink"},
        {"time": start("V02") - .14, "kind": "sweep", "anchor": "#character-pointing"},
        {"time": word("V02", "skills") - .06, "kind": "impact", "anchor": "#mystery-card-b"},
        {"time": start("V03") - .12, "kind": "sweep", "anchor": "#s03-code"},
        {"time": word("V03", "frame") - .05, "kind": "tick", "anchor": "#s03-panel-a"},
        {"time": word("V03", "animation") - .05, "kind": "impact", "anchor": "#s03-motion"},
        {"time": start("V04") - .12, "kind": "sweep", "anchor": "#s04-page"},
        {"time": start("V05") - .08, "kind": "tick", "anchor": "#s04-script"},
        {"time": word("V05", "storyboard") - .05, "kind": "tick", "anchor": "#s04-storyboard"},
        {"time": word("V05", "motion") - .05, "kind": "tick", "anchor": "#s04-motion"},
        {"time": word("V05", "sound") - .05, "kind": "tick", "anchor": "#s04-waveform"},
        {"time": word("V05", "render") - .06, "kind": "impact", "anchor": "#proof-video-frame"},
        {"time": start("V06") - .12, "kind": "sweep", "anchor": "#scene-s06"},
        {"time": start("V07") - .08, "kind": "tick", "anchor": "#s06-playhead"},
        {"time": start("V08") - .18, "kind": "impact", "anchor": "#scene-s07"},
        {"time": word("V08", "skill") - .06, "kind": "impact", "anchor": "#cta-keyword"}
    ]
    return sorted(rows, key=lambda row: row["time"])
```

Before finalizing, adjust Whisper token spellings only to the actual measured `words` arrays. Do not invent offsets.

- [ ] **Step 3: Run the event tests**

Run:

```powershell
python -m pytest 'videos/short-video-skills-manga/tests/test_events.py' -q
```

Expected: tests pass after all events are moved clear of voice starts.

- [ ] **Step 4: Generate phrase captions**

Copy the root-relative caption generator from `videos/short-motionskill/tools/gen_captions.py`. Replace its phrase map with:

```python
PHRASES = {
    "V01": ["CLAUDE", "VIDEOS LIKE THIS"],
    "V02": ["THE RIGHT", "SKILLS"],
    "V03": ["CODE", "FRAME PERFECT", "MOTION"],
    "V04": ["CLAUDE", "DIRECTS IT"],
    "V05": ["SCRIPT", "STORYBOARD", "MOTION", "CAPTIONS", "SOUND", "FINAL RENDER"],
    "V06": ["I USED BOTH"],
    "V07": ["YOU'RE WATCHING", "THE PROOF"],
    "V08": [],
}
```

Caption positions alternate high, mid, and low according to the proof object. `V08` is owned by the CTA scene and must not create a second overlapping caption.

- [ ] **Step 5: Generate a fresh score**

Copy `tools/gen_score.py` from `videos/short-motionskill`, then run:

```powershell
& 'D:\ditto\.voice-venv\Scripts\python.exe' 'videos/short-video-skills-manga/tools/gen_score.py' 'clean modern comic pulse, crisp paper percussion, restrained bass, fast confident build'
```

Expected: a new `assets/music.wav`; its SHA-256 must differ from `videos/short-motionskill/assets/music.wav`.

- [ ] **Step 6: Assemble the mix from the event ledger**

Copy `assemble_mix.py` from `videos/short-motionskill`. Replace its hard-coded event assumptions with `events()` from this project. Preserve:

- rotating SFX pools;
- no identical adjacent sample;
- sidechain ducking under VO;
- a 0.7-second music hole before V08;
- final target `-14.2 LUFS`, `-1.5 dBTP`, `LRA 3`;
- post-normalization pad/trim to exact timeline duration.

Run:

```powershell
python 'videos/short-video-skills-manga/tools/assemble_mix.py'
```

Expected: `assets/final_mix.wav` duration matches `assets/timeline.json` within 0.05 seconds.

- [ ] **Step 7: Commit event and audio tooling**

```powershell
git add -- 'videos/short-video-skills-manga/tools/events.py' 'videos/short-video-skills-manga/tools/gen_captions.py' 'videos/short-video-skills-manga/tools/gen_score.py' 'videos/short-video-skills-manga/tools/assemble_mix.py' 'videos/short-video-skills-manga/tests/test_events.py'
git commit -m 'feat(video): sync manga motion captions and sound'
```

### Task 8: Check, snapshot, render, and verify

**Files:**

- Create: `videos/short-video-skills-manga/tools/render.ps1`
- Create: `videos/short-video-skills-manga/tools/contact.py`
- Create: `videos/short-video-skills-manga/tools/verify.py`
- Generate: `videos/short-video-skills-manga/qa/*`
- Generate: `videos/short-video-skills-manga/renders/biosrios-video-skills-manga-1080x1920.mp4`

- [ ] **Step 1: Add a D-drive-safe render script**

Create `tools/render.ps1`:

```powershell
param(
  [int]$Workers = 4,
  [string]$Output = 'renders/biosrios-video-skills-manga-1080x1920.mp4'
)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
$scratch = 'D:\ditto\.scratch\hf-video-skills-manga'
$npmCache = 'D:\ditto\.cache\npm'
$pptr = 'D:\ditto\.cache\puppeteer'
$outputPath = [IO.Path]::GetFullPath((Join-Path $project $Output))
$rawPath = Join-Path (Split-Path -Parent $outputPath) '.raw-video.mp4'
$audioPath = Join-Path $project 'assets/final_mix.wav'
if (-not $outputPath.StartsWith($project, [StringComparison]::OrdinalIgnoreCase)) {
  throw 'Output escaped project root.'
}
New-Item -ItemType Directory -Force -Path $scratch,$npmCache,$pptr,(Split-Path -Parent $outputPath) | Out-Null
$env:TEMP=$scratch; $env:TMP=$scratch; $env:TMPDIR=$scratch
$env:npm_config_cache=$npmCache; $env:PUPPETEER_CACHE_DIR=$pptr
Push-Location $project
try {
  & npx --yes hyperframes@0.7.78 render . --output $rawPath --fps 60 --quality high --video-bitrate 14M --workers $Workers
  if ($LASTEXITCODE -ne 0) { throw "HyperFrames render failed: $LASTEXITCODE" }
  & ffmpeg -hide_banner -y -i $rawPath -i $audioPath -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 -movflags +faststart -shortest $outputPath
  if ($LASTEXITCODE -ne 0) { throw "Mux failed: $LASTEXITCODE" }
  Remove-Item -LiteralPath $rawPath -Force
} finally {
  Pop-Location
}
Get-Item -LiteralPath $outputPath
```

- [ ] **Step 2: Run all structural gates**

Run:

```powershell
Set-Location 'videos/short-video-skills-manga'
python -m pytest tests -q
python tools/leak_scan.py
npx --yes hyperframes@0.7.78 check .
```

Expected:

- all pytest tests pass;
- leak scan has zero hits;
- HyperFrames check passes with zero errors.

- [ ] **Step 3: Render scene-midpoint snapshots**

Use timeline midpoints for all seven scenes:

```powershell
npx --yes hyperframes@0.7.78 snapshot . --at 1.2,4.2,7.3,12.8,17.8,21.7,25.1 --output qa/scene-midpoints
```

Expected: seven readable vertical frames. Inspect each at phone size and full size.

- [ ] **Step 4: Fix visual QA defects before rendering**

Reject and fix:

- any fake or unreadable proof UI;
- caption collisions;
- character covering proof;
- low-resolution character scaling;
- identical panel composition in adjacent scenes;
- generic fade/wipe transitions;
- still proof video;
- more than one focal element fighting for the center;
- CTA readable for less than 1.2 seconds.

After each fix rerun `hyperframes check` and only the affected snapshots.

- [ ] **Step 5: Render the MP4**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File tools/render.ps1
```

Expected: `renders/biosrios-video-skills-manga-1080x1920.mp4`.

- [ ] **Step 6: Add contact-sheet and verification tools**

Copy root-relative `contact.py` and `verify.py` from `videos/short-motionskill`. Update verification expectations:

```text
resolution: 1080x1920
fps: 60
duration: 25-30 seconds and within 0.5 seconds of timeline
loudness: -14.2 LUFS ±1.0
CTA tail: >=1.2 seconds
name leak: zero
voice/timeline mismatch: <=0.12 seconds per line
undeclared freeze >=0.7 seconds: zero
sync probes: V01, V05, V08 each >=60% word overlap
```

Write machine-readable results to `qa/verification.json`.

- [ ] **Step 7: Run final verification and watch the full render**

Run:

```powershell
python tools/contact.py 'renders/biosrios-video-skills-manga-1080x1920.mp4'
python tools/verify.py 'renders/biosrios-video-skills-manga-1080x1920.mp4'
```

Expected: `ALL GATES PASSED`.

Then watch the entire MP4 with sound. Mechanical gates are floors. Reject the render if it is technically valid but feels slow, cluttered, repetitive, or visually cheap.

- [ ] **Step 8: Commit the verified build**

Stage exact project files only:

```powershell
git add -- 'videos/short-video-skills-manga'
git status --short
git commit -m 'feat(video): render animated manga Claude skills reel'
```

Before committing, remove raw render scratch, unused voice takes, `_score_raw.wav`, redundant render versions, and any asset that is not listed in `assets/manifest.json`.

### Task 9: Independent final review

**Files:**

- Review only; modify only when a concrete issue is found

- [ ] **Step 1: Spec-compliance review**

Compare the finished render and retained project against every requirement in:

```text
docs/superpowers/specs/2026-07-30-animated-manga-claude-video-skills-design.md
```

Return `APPROVED` or exact issues with file/timestamp references.

- [ ] **Step 2: Code-quality review**

Only after spec approval, inspect:

- deterministic timeline registration;
- no unresolved timing tokens;
- no duplicated cue ledgers;
- no C-drive render scratch;
- no dead assets;
- no unrelated changes;
- UTF-8 punctuation round trip in script and CTA.

Return `APPROVED` or exact file/line issues.

- [ ] **Step 3: Fix and re-verify**

For every issue:

1. add or tighten a regression test;
2. confirm it fails;
3. make the smallest fix;
4. rerun affected tests;
5. rerun `hyperframes check`;
6. rerender if picture or sound changed;
7. rerun final verification;
8. repeat both reviews.

- [ ] **Step 4: Handoff**

Report:

- clickable MP4 path;
- actual duration, resolution, FPS, loudness, and CTA hold;
- verification result;
- exact commit;
- whether the face clone was excluded;
- whether the hidden names were absent from the final render.
