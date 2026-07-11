# Ditto Plugin Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first Ditto Plugin release with full-history mining as the quality default, bounded cached mining as an explicitly labeled quick preview, durable private profiles, `ditto:mine`, `ditto:work`, `ditto:design`, and `ditto:write`, a preserved cross-agent npx bootstrap, safe legacy migration, and an independently publishable GitHub Release.

**Architecture:** Keep `ditto.py` as the canonical stdlib-only, single-file mining runtime. Add a backward-compatible `python ditto.py plugin` command family that owns deterministic extraction, stable segments, caches, report validation, profile activation, migration, and loader lookup; static plugin skills orchestrate model work but never store private profiles inside plugin caches. The no-flag plugin flow plans the full-history quality profile and waits for cost approval before model work; `--preview` selects a bounded starter profile and states that limitation in every surface. Keep the existing skills.sh `ditto` bootstrap outside native plugin discovery and give it a small hash-verifying installer for the exact release runtime. This plan stops after the Plugin release (Workstreams 0-8); benchmark Workstreams 9-10 remain a separate later plan.

**Tech Stack:** Python 3 stdlib, `unittest`, JSON/Markdown skill files, skills.sh CLI, Codex and conditional Claude plugin manifests, local filesystem state under `DITTO_HOME`, Git/GitHub release tooling.

---

## Scope and source of truth

Implement only Workstreams 0-8 from:

- `docs/superpowers/specs/2026-07-10-ditto-plugin-design.md`
- `docs/superpowers/plans/2026-07-10-ditto-plugin-architecture-plan.md`

Do not create the benchmark runner, execute benchmark models, build the leaderboard, or produce benchmark videos. Do not publish a tag or GitHub Release without Ohad's explicit ship approval at Task 19.

At plan-writing time, the repository's latest tag is `v0.1.2`, the Codex CLI exposes native `plugin marketplace`/`plugin add` commands, and no `claude` executable is available on `PATH`. Commit `04b9fbf` already publishes `npx skills add ohad6k/ditto`; live checks confirmed the current repository exposes one `ditto` skill, `owner/repo@skill` selects it directly, selected installs copy only that skill directory, and companion files inside the directory are preserved. Workstream 0 must preserve this surface while rechecking both native hosts. Codex failure stops the plugin architecture. Claude unavailability or failure keeps the skills.sh/direct Claude path and removes native Claude claims from this release.

## Execution prerequisite

Before Task 1, use `superpowers:using-git-worktrees` to create an isolated worktree on branch `codex/ditto-plugin-release`. Confirm the worktree does not contain or stage the unrelated `.superpowers/`, `ditto-out/`, `chunks/`, or `videos/` directories from the main checkout.

Baseline command:

```powershell
python -m unittest discover -s tests -v
```

Expected: `Ran 9 tests` and `OK` before the first product edit.

## File map

### Runtime and tests

- Modify `ditto.py` — preserve legacy CLI/card/direct installs; add deterministic plugin runtime, caches, profile store, migration, and internal plugin subcommands.
- Modify `tests/test_ditto.py` — add current-defect regressions without weakening the existing nine tests.
- Create `tests/test_plugin_runtime.py` — session records, segmentation, selection, preflight, report caches, and plugin CLI integration.
- Create `tests/test_profile_store.py` — report/profile validation, atomic activation, reduction cache, migration, and rollback.
- Create `tests/test_plugin_manifests.py` — manifest shape, skill frontmatter/routing, plugin-private-state separation.
- Create `tests/test_bootstrap.py` — skills.sh companion runtime install, pinning, hash mismatch, and pointer preservation.
- Create `tests/fixtures/plugin-spike-home/spike.txt` — harmless `DITTO_SPIKE_OK` proof fixture.

### Plugin surfaces

- Create `.agents/plugins/marketplace.json` — local Codex development marketplace.
- Move `skills/ditto/SKILL.md` to `.agents/skills/ditto/SKILL.md` — preserve Claude's verified skills.sh bootstrap outside native plugin discovery.
- Create `.agents/skills/ditto/scripts/bootstrap.py` and `.agents/skills/ditto/runtime.json` — deterministic pinned-runtime installation for copied npx skills.
- Create `.codex-plugin/plugin.json` — Codex plugin manifest.
- Conditionally create `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` only if native Claude passes Workstream 0.
- Create `skills/mine/SKILL.md`, `skills/work/SKILL.md`, `skills/design/SKILL.md`, and `skills/write/SKILL.md` — final namespaced plugin skills.
- Modify `MINING_PROMPT.md` — one structured evidence report per selected segment plus one three-profile reducer contract.

### Product truth and release

- Modify `README.md`, `SECURITY.md`, and `ROADMAP.md` — simple user flow, exact cost/privacy boundaries, current support matrix, and release scope.
- Create `CHANGELOG.md` — Plugin release entry only; no benchmark scores or placeholders.
- Create `docs/release/plugin-viability.md` — actual per-host Workstream 0 evidence.
- Create `docs/release/plugin-dogfood.md` — non-private calibration and fresh-task proof summary.
- Create `docs/release/plugin-release-draft.md` — exact local release-note draft for final approval.

## Fixed runtime interfaces

All later tasks use these names. Do not silently rename them mid-plan.

```python
EXTRACTION_SCHEMA_VERSION = "1"
SEGMENT_SCHEMA_VERSION = "1"
REPORT_SCHEMA_VERSION = "1"
PROMPT_SCHEMA_VERSION = "1"
REDUCER_SCHEMA_VERSION = "1"

STARTER_CANDIDATES = (
    {"segments": 4, "segment_tokens": 25_000},
    {"segments": 6, "segment_tokens": 20_000},
    {"segments": 8, "segment_tokens": 20_000},
)
STARTER_MAX_SOURCE_TOKENS = 160_000
STARTER_MAX_MODEL_CALLS = 9
DEFAULT_CANDIDATE_INDEX = 0  # quick-preview candidate; never the quality default without a 22/22 gate pass
QUALITY_DEFAULT_MODE = "full"
DEEP_SEGMENT_TOKENS = 20_000
MAX_REPORT_BYTES = 8_192
MAX_EVIDENCE_PER_REPORT = 12
MAX_QUOTE_CHARS = 200
```

The internal plugin CLI is:

```text
python ditto.py plugin preflight    [source args] [--preview | --candidate 0|1|2 | --deep | --deepen-domain work|design|write] [--ditto-home PATH]
python ditto.py plugin prepare      [source args] [--preview | --candidate 0|1|2 | --deep | --deepen-domain work|design|write] [--ditto-home PATH]
python ditto.py plugin cache-report --run-id ID --report FILE [--ditto-home PATH]
python ditto.py plugin activate     --run-id ID (--pack DIR | --cached) [--ditto-home PATH]
python ditto.py plugin status       [--ditto-home PATH]
python ditto.py plugin profile-path --domain work|design|write [--ditto-home PATH]
python ditto.py plugin migrate-stage    --target codex|claude [--ditto-home PATH] [--home PATH]
python ditto.py plugin migrate-cutover  --migration-id ID [--ditto-home PATH]
python ditto.py plugin migrate-rollback --migration-id ID [--ditto-home PATH]
python ditto.py plugin migrate-adapter  --target agents|gemini --repo PATH --mode backup-remove|restore [--ditto-home PATH]
```

Every plugin command writes one JSON object to stdout and operational errors to stderr with a nonzero exit. Legacy commands keep their current human-readable output.

Call accounting is deliberately narrow: one uncached segment equals one planned worker pass and one uncached report set equals one planned reducer pass. Hosts may implement those passes as subagents, sequential turns, or a continuing task and may bill system prompts, tool traffic, and orchestration differently. Public output calls these `planned_worker_calls` and `planned_reducer_calls`; it never converts them into a subscription percentage or claims they equal provider billing events.

Core function signatures are fixed as `sync_segments(records, ditto_home, target_tokens, write=True)`, `select_segments(segments, count, max_tokens)`, `build_preflight(result, ditto_home, candidate_index, write=False)`, `validate_report(report, segment)`, `store_report(report, ditto_home, segment)`, `validate_profile_pack(pack_dir, evidence_by_id, run_plan)`, `activate_profile_pack(ditto_home, pack_dir, evidence_by_id, run_plan, fail_after=None)`, and `activate_cached_reduction(ditto_home, report_set_hash)`.

---

### Task 1: Separate and prove the native-plugin and skills.sh surfaces

**Files:**
- Move: `skills/ditto/SKILL.md` → `.agents/skills/ditto/SKILL.md`
- Create: `skills/.gitkeep` (temporary path keeper; delete in Task 12)
- Modify: `README.md` (repository skill link only; full copy rewrite remains Task 15)
- Create: `.agents/plugins/marketplace.json`
- Create: `.codex-plugin/plugin.json`
- Create: `skills/spike/SKILL.md` (temporary; delete before commit)
- Create: `tests/fixtures/plugin-spike-home/spike.txt`
- Conditional create: `.claude-plugin/plugin.json`
- Conditional create: `.claude-plugin/marketplace.json`
- Create: `docs/release/plugin-viability.md` after live proof

- [ ] **Step 1: Move Claude's verified npx bootstrap outside native plugin discovery**

Run:

```powershell
New-Item -ItemType Directory -Force .agents\skills | Out-Null
git mv skills\ditto .agents\skills\ditto
```

Use `apply_patch` to add `skills/.gitkeep` containing `native plugin skills land here in Task 12` and to change the README's repository skill link from `skills/ditto/SKILL.md` to `.agents/skills/ditto/SKILL.md`. Do not rewrite the bootstrap workflow yet; Task 15 makes it bounded after the runtime exists.

Expected: `.agents/skills/ditto/SKILL.md` retains `name: ditto`; no `skills/ditto/SKILL.md` remains for native default discovery.

- [ ] **Step 2: Prove the current one-skill npx selection still works**

Run a list and copy install from the local repository with telemetry disabled:

```powershell
$env:DISABLE_TELEMETRY = "1"
$sourceRoot = (Get-Location).Path
npx -y skills add "$sourceRoot" --list
$auditRoot = Join-Path $env:TEMP ("ditto-npx-audit-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $auditRoot | Out-Null
Push-Location $auditRoot
try {
    npx -y skills add "$sourceRoot" --skill ditto --agent codex --copy --yes
    $installed = Join-Path $auditRoot ".agents\skills\ditto"
    if (-not (Test-Path -LiteralPath (Join-Path $installed "SKILL.md"))) { throw "ditto bootstrap was not copied" }
    $otherSkills = @(Get-ChildItem -LiteralPath (Join-Path $auditRoot ".agents\skills") -Directory | Where-Object Name -ne "ditto")
    if ($otherSkills.Count -ne 0) { throw "npx copied a native-only skill" }
} finally {
    Pop-Location
    $resolved = [IO.Path]::GetFullPath($auditRoot)
    $tempRoot = [IO.Path]::GetFullPath($env:TEMP)
    if (-not $resolved.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) { throw "unsafe npx audit cleanup path" }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
```

Expected: list output includes `ditto`; the selected copy install contains only `.agents/skills/ditto/SKILL.md`. The final public shorthand is tested as `ohad6k/ditto@ditto` after publication in Task 19.

- [ ] **Step 3: Add the harmless spike fixture**

```text
DITTO_SPIKE_OK
```

- [ ] **Step 4: Add the local Codex marketplace**

```json
{
  "name": "ditto",
  "interface": {"displayName": "Ditto development"},
  "plugins": [
    {
      "name": "ditto",
      "source": {"source": "local", "path": "./"},
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
        "products": ["CODEX"]
      },
      "category": "Developer Tools"
    }
  ]
}
```

- [ ] **Step 5: Add the development Codex manifest**

```json
{
  "name": "ditto",
  "version": "0.0.0-dev",
  "description": "Mine real AI coding sessions into a bounded, evidence-backed personal layer.",
  "author": {"name": "Ohad"},
  "homepage": "https://github.com/ohad6k/ditto",
  "repository": "https://github.com/ohad6k/ditto",
  "license": "MIT",
  "keywords": ["personalization", "skills", "session-mining", "agents"],
  "skills": "./skills/",
  "interface": {
    "displayName": "Ditto",
    "shortDescription": "Your agents stop starting from zero",
    "longDescription": "Ditto mines selected evidence from your real local coding-agent sessions into private work, design, and writing profiles.",
    "developerName": "Ohad",
    "category": "Developer Tools",
    "capabilities": ["Interactive", "Read", "Write"],
    "defaultPrompt": ["Run Ditto", "Update my Ditto profile"],
    "websiteURL": "https://github.com/ohad6k/ditto",
    "brandColor": "#141414",
    "composerIcon": "./assets/ditto.svg",
    "logo": "./assets/ditto.png",
    "screenshots": []
  }
}
```

- [ ] **Step 6: Add the temporary spike skill**

```markdown
---
name: spike
description: Use only when explicitly asked to run the Ditto host viability spike.
---

# Ditto host viability spike

Run local Python. Read `$env:DITTO_HOME/spike.txt` on Windows or `$DITTO_HOME/spike.txt` elsewhere. Return only its exact contents. Do not read session logs, run mining, create a profile, or make any benchmark call.
```

- [ ] **Step 7: Validate the Codex manifest and marketplace JSON**

Run:

```powershell
codex --version
python -m json.tool .agents\plugins\marketplace.json > $null
python C:\Users\ohad1\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py .
```

Expected: both exit `0`; the validator reports a valid `ditto` plugin.

- [ ] **Step 8: Install the local Codex marketplace and plugin**

First inspect configured sources:

```powershell
codex plugin marketplace list --json
codex plugin list --json
```

If a marketplace named `ditto` already points at this exact worktree, keep it and skip the marketplace-add command. If `ditto` points anywhere else, stop and resolve the name conflict explicitly; do not remove or overwrite another checkout. If `ditto@ditto` is already installed from this exact worktree, remove only that plugin before reinstalling it.

Then run the applicable commands:

```powershell
codex plugin marketplace add "$PWD" --json
codex plugin add ditto@ditto --json
codex plugin list --marketplace ditto --json
```

Expected: JSON identifies marketplace `ditto`, plugin `ditto`, version `0.0.0-dev`, and installed status. Discovery exposes `ditto:spike` and never exposes the relocated bootstrap as `ditto:ditto`.

- [ ] **Step 9: Run exactly one fresh-task Codex spike**

Run with `DITTO_HOME` pointing only at the committed harmless fixture:

```powershell
$env:DITTO_HOME = "$PWD\tests\fixtures\plugin-spike-home"
codex exec -C "$PWD" "Use ditto:spike. Return only the sentinel value."
```

Expected: final task output is exactly `DITTO_SPIKE_OK`. This is a bounded development proof, not mining and not a benchmark.

If discovery, local Python invocation, isolated `DITTO_HOME` access, or the sentinel result fails, write the actual failure evidence, remove only the development plugin/source installed from this worktree, and stop this implementation plan. Do not continue Tasks 2-19 under an unproven Codex packaging premise.

- [ ] **Step 10: Recheck Claude availability and follow the evidence branch**

Run:

```powershell
Get-Command claude -ErrorAction SilentlyContinue
```

If it returns no executable, record native Claude as `not testable in this environment`, do not commit `.claude-plugin/*`, and keep the direct Claude adapter. If it returns an executable, add these exact files:

`.claude-plugin/plugin.json`:

```json
{
  "name": "ditto",
  "description": "Mine real AI coding sessions into a bounded, evidence-backed personal layer.",
  "version": "0.0.0-dev",
  "author": {"name": "Ohad"},
  "homepage": "https://github.com/ohad6k/ditto",
  "repository": "https://github.com/ohad6k/ditto",
  "license": "MIT",
  "keywords": ["personalization", "skills", "session-mining", "agents"]
}
```

`.claude-plugin/marketplace.json`:

```json
{
  "name": "ditto",
  "description": "Development marketplace for Ditto",
  "owner": {"name": "Ohad"},
  "plugins": [
    {
      "name": "ditto",
      "description": "Bounded personal-profile mining for coding agents",
      "version": "0.0.0-dev",
      "source": "./",
      "author": {"name": "Ohad"}
    }
  ]
}
```

Then run:

```powershell
claude --version
claude plugin marketplace add .
claude plugin install ditto@ditto
$env:DITTO_HOME = "$PWD\tests\fixtures\plugin-spike-home"
claude -p "Use ditto:spike. Return only the sentinel value."
```

Keep native Claude files only if the final command returns exactly `DITTO_SPIKE_OK` and Claude discovery does not expose the relocated skills.sh bootstrap.

- [ ] **Step 11: Remove the temporary spike skill and write the actual evidence record**

Delete `skills/spike/SKILL.md` but retain `skills/.gitkeep`. In `docs/release/plugin-viability.md`, record the observed host/CLI version, commands, installed namespace, sentinel output, the skills.sh selected-install result, and the final native/adapter decision for each host. Include no unfinished marker, assumed pass, user logs, or private paths beyond the harmless fixture.

- [ ] **Step 12: Revalidate and commit the proven packaging premise**

Run:

```powershell
python C:\Users\ohad1\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py .
python -m unittest discover -s tests -v
```

Expected: validator exit `0`; existing tests remain `OK`.

Commit only the retained host files, fixture, and evidence:

```powershell
git add .agents/plugins/marketplace.json .agents/skills/ditto/SKILL.md .codex-plugin/plugin.json skills/.gitkeep README.md tests/fixtures/plugin-spike-home/spike.txt docs/release/plugin-viability.md
git add skills/ditto/SKILL.md
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json  # only when Claude passed
git commit -m "feat: prove Ditto plugin host viability"
```

### Task 2: Fail closed on empty history and exact skill frontmatter

**Files:**
- Modify: `tests/test_ditto.py`
- Modify: `ditto.py:458-465,544-603`

- [ ] **Step 1: Add failing zero-session and malformed-frontmatter tests**

Add these as methods inside the existing `DittoCliTest` class, before its `if __name__ == "__main__"` block:

```python
def test_zero_valid_sessions_fails_without_writing_output(self):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        logs = root / "logs"
        logs.mkdir()
        (logs / "bad.jsonl").write_text("{}\nnot-json\n", encoding="utf-8")
        out = root / "out"
        result = subprocess.run(
            [sys.executable, str(DITTO), "--path", str(logs), "--out", str(out)],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no valid user sessions", result.stderr)
        self.assertFalse(out.exists())

def test_install_rejects_substring_frontmatter_keys(self):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profile = root / "bad.md"
        profile.write_text(
            "---\nnotname: you\nnotdescription: wrong\n---\nbody\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, str(DITTO), "--install", str(profile), "--target", "codex", "--home", str(root / "home")],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact name and description", result.stderr)
```

- [ ] **Step 2: Run the two tests and confirm the current bugs**

Run:

```powershell
python -m unittest tests.test_ditto.DittoCliTest.test_zero_valid_sessions_fails_without_writing_output tests.test_ditto.DittoCliTest.test_install_rejects_substring_frontmatter_keys -v
```

Expected: FAIL because zero sessions currently exits `0` and substring keys currently pass.

- [ ] **Step 3: Add an exact frontmatter parser**

```python
def parse_frontmatter(text):
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0] != "---":
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None
    fields = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            return None
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", key) or not value or key in fields:
            return None
        fields[key] = value
    return fields

def has_skill_frontmatter(text, expected_name=None):
    fields = parse_frontmatter(text)
    if not fields or set(("name", "description")) - set(fields):
        return False
    return expected_name is None or fields["name"] == expected_name
```

Write validation errors to `stderr` and keep `name: you` valid for legacy direct installs.

- [ ] **Step 4: Fail before dry-run or output when no valid sessions remain**

Immediately after `result = mine_files(files, args.no_redact, dedupe=not args.no_dedupe)` in `main()` add:

```python
if result["sessions"] == 0:
    print("no valid user sessions remained after parsing and filtering", file=sys.stderr)
    sys.exit(1)
```

- [ ] **Step 5: Run focused and full tests**

Run:

```powershell
python -m unittest tests.test_ditto.DittoCliTest.test_zero_valid_sessions_fails_without_writing_output tests.test_ditto.DittoCliTest.test_install_rejects_substring_frontmatter_keys -v
python -m unittest discover -s tests -v
```

Expected: focused tests PASS; full suite reports 11 tests and `OK`.

- [ ] **Step 6: Commit**

```powershell
git add ditto.py tests/test_ditto.py
git commit -m "fix: fail closed on empty input and invalid frontmatter"
```

### Task 3: Replace stale chunks and marked blocks atomically

**Files:**
- Modify: `tests/test_ditto.py`
- Modify: `ditto.py:176-202,511-542`

- [ ] **Step 1: Add failing stale-chunk and partial-marker tests**

Add these as methods inside the existing `DittoCliTest` class:

```python
def test_smaller_rerun_removes_stale_chunks(self):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        logs = root / "logs"
        for i in range(12):
            write_jsonl(logs / f"session-{i}.jsonl", [{
                "timestamp": f"2026-07-{i + 1:02d}T10:00:00Z",
                "payload": {"type": "message", "role": "user", "content": [{"text": "x" * 1000 + str(i)}]},
            }])
        out = root / "out"
        subprocess.run([sys.executable, str(DITTO), "--path", str(logs), "--out", str(out), "--chunks", "6"], check=True)
        subprocess.run([sys.executable, str(DITTO), "--path", str(logs), "--out", str(out), "--chunks", "1"], check=True)
        self.assertEqual(["chunk-01.txt"], sorted(p.name for p in (out / "chunks").iterdir()))

def test_partial_marked_block_fails_without_modifying_file(self):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "repo"
        repo.mkdir()
        agents = repo / "AGENTS.md"
        original = "# rules\n\n<!-- ditto profile:start -->\nbroken\n"
        agents.write_text(original, encoding="utf-8")
        profile = root / "you.md"
        profile.write_text("---\nname: you\ndescription: test\n---\nbody\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(DITTO), "--install", str(profile), "--target", "agents", "--repo", str(repo), "--yes"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(original, agents.read_text(encoding="utf-8"))

def test_agents_install_preserves_existing_crlf_style(self):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "repo"
        repo.mkdir()
        agents = repo / "AGENTS.md"
        agents.write_bytes(b"# keep\r\n\r\n")
        profile = root / "you.md"
        profile.write_text("---\nname: you\ndescription: test\n---\nbody\n", encoding="utf-8")
        subprocess.run([sys.executable, str(DITTO), "--install", str(profile), "--target", "agents", "--repo", str(repo)], check=True)
        installed = agents.read_bytes()
        self.assertNotIn(b"\n", installed.replace(b"\r\n", b""))
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```powershell
python -m unittest tests.test_ditto.DittoCliTest.test_smaller_rerun_removes_stale_chunks tests.test_ditto.DittoCliTest.test_partial_marked_block_fails_without_modifying_file -v
```

Expected: both FAIL against the current direct-write behavior.

- [ ] **Step 3: Add same-volume atomic write helpers**

```python
def atomic_write_bytes(path, data):
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    fd, staged = tempfile.mkstemp(prefix=".ditto-", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(staged, path)
    except Exception:
        if os.path.exists(staged):
            os.remove(staged)
        raise

def atomic_write_text(path, text):
    atomic_write_bytes(path, text.encode("utf-8"))

def replace_directory(staged, target):
    backup = target + ".ditto-backup-" + uuid.uuid4().hex
    if os.path.exists(target):
        os.replace(target, backup)
    try:
        os.replace(staged, target)
    except Exception:
        if os.path.exists(backup):
            os.replace(backup, target)
        raise
    if os.path.exists(backup):
        try:
            shutil.rmtree(backup)
        except OSError:
            pass  # inactive backup cleanup is retryable; the new target is already live
```

Add `shutil`, `tempfile`, and `uuid` to the stdlib imports.

- [ ] **Step 4: Stage the complete chunk directory before swapping it**

Write all new `chunk-XX.txt` files under a sibling temporary directory, atomically write `you-corpus.txt` and canonical `stats.json`, then call `replace_directory(staged_chunks, chunks_dir)`. Never write into the live chunk directory, and route `write_stats` through `atomic_write_text` instead of a direct file write.

- [ ] **Step 5: Reject partial marker state and atomically write adapters**

Read existing adapter files with `newline=""`, detect `newline = "\r\n" if "\r\n" in existing else "\n"`, and build the marked block with that separator. Before replacement, add:

```python
has_start = DITTO_START in existing
has_end = DITTO_END in existing
if has_start != has_end:
    print("existing Ditto block is incomplete; refusing to modify it", file=sys.stderr)
    sys.exit(1)
```

Replace direct destination writes in the marked-block, Cursor, Codex, and Claude install branches with `atomic_write_text(dest, updated_or_profile)`.

- [ ] **Step 6: Run focused and full tests**

Run:

```powershell
python -m unittest tests.test_ditto.DittoCliTest.test_smaller_rerun_removes_stale_chunks tests.test_ditto.DittoCliTest.test_partial_marked_block_fails_without_modifying_file -v
python -m unittest discover -s tests -v
```

Expected: 14 tests, all `OK`.

- [ ] **Step 7: Commit**

```powershell
git add ditto.py tests/test_ditto.py
git commit -m "fix: replace Ditto outputs atomically"
```

### Task 4: Make Windows console output Unicode-safe

**Files:**
- Modify: `tests/test_ditto.py`
- Modify: `ditto.py:23-32,544-606`

- [ ] **Step 1: Add the failing cp1252/Hebrew subprocess test**

Add this as a method inside the existing `DittoCliTest` class:

```python
def test_hebrew_install_path_survives_cp1252_console(self):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        profile = root / "you.md"
        profile.write_text("---\nname: you\ndescription: test\n---\nbody\n", encoding="utf-8")
        home = root / "שלום"
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        result = subprocess.run(
            [sys.executable, str(DITTO), "--install", str(profile), "--target", "codex", "--home", str(home), "--yes"],
            capture_output=True,
            env=env,
        )
        self.assertEqual(0, result.returncode, result.stderr.decode("utf-8", errors="replace"))
        self.assertIn("שלום", result.stdout.decode("utf-8"))
        self.assertTrue((home / ".codex" / "skills" / "you" / "SKILL.md").exists())
```

Add `import os` to the test module.

- [ ] **Step 2: Run the test and confirm `UnicodeEncodeError`**

Run:

```powershell
python -m unittest tests.test_ditto.DittoCliTest.test_hebrew_install_path_survives_cp1252_console -v
```

Expected: FAIL with a console encoding error.

- [ ] **Step 3: Configure UTF-8 streams once at process entry**

```python
def configure_console():
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="backslashreplace")
            except (AttributeError, ValueError):
                pass
```

Call `configure_console()` as the first statement inside `main()`.

- [ ] **Step 4: Run the Unicode test and full suite**

Run:

```powershell
python -m unittest tests.test_ditto.DittoCliTest.test_hebrew_install_path_survives_cp1252_console -v
python -m unittest discover -s tests -v
```

Expected: 15 tests, all `OK`; the installed file is byte-for-byte UTF-8.

- [ ] **Step 5: Commit**

```powershell
git add ditto.py tests/test_ditto.py
git commit -m "fix: preserve Unicode paths on Windows consoles"
```

### Task 5: Add the backward-compatible plugin command shell and private-state paths

**Files:**
- Create: `tests/test_plugin_runtime.py`
- Modify: `ditto.py:23-32,544-606`

- [ ] **Step 1: Add failing CLI-shell tests**

```python
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DITTO = ROOT / "ditto.py"
SPEC = importlib.util.spec_from_file_location("ditto_runtime", DITTO)
ditto = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ditto)

class PluginRuntimeCliTest(unittest.TestCase):
    def test_plugin_status_uses_ditto_home_and_writes_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "private"
            result = subprocess.run(
                [sys.executable, str(DITTO), "plugin", "status", "--ditto-home", str(home)],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(result.stdout)
            self.assertEqual("missing", payload["status"])
            self.assertEqual(str(home.resolve()), payload["ditto_home"])
            self.assertFalse(home.exists())

    def test_legacy_dry_run_still_uses_legacy_parser(self):
        result = subprocess.run([sys.executable, str(DITTO), "--help"], check=True, capture_output=True, text=True)
        self.assertIn("--dry-run", result.stdout)
        self.assertNotIn("plugin status", result.stdout)

    def test_private_child_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "private state"):
                ditto.safe_private_child(str(Path(tmp) / "private"), "runs", "..", "outside")
```

- [ ] **Step 2: Run the new module and verify failure**

Run:

```powershell
python -m unittest tests.test_plugin_runtime.PluginRuntimeCliTest -v
```

Expected: `plugin status` fails because the command shell does not exist.

- [ ] **Step 3: Add fixed constants and path helpers**

Add the constants from `Fixed runtime interfaces`, then:

```python
def resolve_ditto_home(value=None):
    raw = value or os.environ.get("DITTO_HOME") or os.path.join(HOME, ".ditto")
    return os.path.abspath(os.path.expanduser(raw))

def private_paths(ditto_home):
    return {
        "root": ditto_home,
        "active": os.path.join(ditto_home, "active-profile.json"),
        "profiles": os.path.join(ditto_home, "profiles"),
        "segments": os.path.join(ditto_home, "cache", "segments"),
        "segment_indexes": os.path.join(ditto_home, "cache", "segment-indexes"),
        "reports": os.path.join(ditto_home, "cache", "reports"),
        "reductions": os.path.join(ditto_home, "cache", "reductions"),
        "runs": os.path.join(ditto_home, "runs"),
        "migrations": os.path.join(ditto_home, "migrations"),
        "legacy": os.path.join(ditto_home, "legacy"),
    }

def safe_private_child(ditto_home, *parts):
    root = os.path.realpath(resolve_ditto_home(ditto_home))
    candidate = os.path.realpath(os.path.join(root, *parts))
    try:
        contained = os.path.commonpath((root, candidate)) == root
    except ValueError:
        contained = False
    if not contained:
        raise ValueError("path escapes Ditto private state")
    return candidate
```

Validate every later `run_id` against `^[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}(?:-[0-9]{2})?$` and every SHA-derived `migration_id` against `^[a-f0-9]{20}$` before resolving them through `safe_private_child`.

- [ ] **Step 4: Dispatch `plugin` without changing legacy argparse**

```python
def build_plugin_parser():
    parser = argparse.ArgumentParser(prog="ditto.py plugin")
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.add_argument("--ditto-home")
    return parser

def plugin_main(argv):
    parser = build_plugin_parser()
    args = parser.parse_args(argv)
    if args.command == "status":
        home = resolve_ditto_home(args.ditto_home)
        payload = {"status": "missing", "ditto_home": home}
        print(json.dumps(payload, sort_keys=True))

def main():
    configure_console()
    if len(sys.argv) > 1 and sys.argv[1] == "plugin":
        plugin_main(sys.argv[2:])
        return
    legacy_main()
```

Rename the pre-Task-5 `main` function to `legacy_main` without changing its argparse body. The new dispatcher above becomes `main`; do not call `configure_console` a second time inside `legacy_main`. Status must not create `DITTO_HOME`.

- [ ] **Step 5: Run new and full tests**

Run:

```powershell
python -m unittest tests.test_plugin_runtime.PluginRuntimeCliTest -v
python -m unittest discover -s tests -v
```

Expected: 18 tests, all `OK`.

- [ ] **Step 6: Commit**

```powershell
git add ditto.py tests/test_plugin_runtime.py
git commit -m "feat: add Ditto plugin runtime command shell"
```

### Task 6: Preserve structured, private session identities during extraction

**Files:**
- Modify: `tests/test_plugin_runtime.py`
- Modify: `ditto.py:65-174`

- [ ] **Step 1: Reuse the direct runtime loader from Task 5**

Keep the `importlib.util` loader added in Task 5 at module scope. The structured-session tests call helpers directly through that same `ditto` module; do not add a second module instance with divergent globals.

- [ ] **Step 2: Add failing structured-session tests**

```python
def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")

class SessionRecordTest(unittest.TestCase):
    def test_records_use_stable_hashed_ids_without_raw_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".codex" / "sessions" / "private-project.jsonl"
            write_jsonl(path, [{
                "timestamp": "2026-07-08T10:00:00Z",
                "payload": {"type": "message", "role": "user", "content": [{"text": "done means live proof"}]},
            }])
            result = ditto.mine_files([str(path)])
            record = result["records"][0]
            self.assertRegex(record["session_id"], r"^[0-9a-f]{16}$")
            self.assertEqual("codex", record["source"])
            self.assertEqual("2026-07-08", record["first_date"])
            self.assertIn("done means live proof", record["text"])
            self.assertNotIn("private-project", record["text"])
            self.assertEqual(record["content_hash"], ditto.sha256_text(record["text"]))

    def test_record_identity_is_stable_across_repeated_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custom" / "one.jsonl"
            write_jsonl(path, [{
                "timestamp": "2026-07-08T10:00:00Z",
                "payload": {"type": "message", "role": "user", "content": [{"text": "ship it"}]},
            }])
            first = ditto.mine_files([str(path)])["records"][0]
            second = ditto.mine_files([str(path)])["records"][0]
            self.assertEqual(first, second)

    def test_known_agent_context_injection_is_not_mined_as_user_voice(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".codex" / "sessions" / "one.jsonl"
            write_jsonl(path, [
                {
                    "timestamp": "2026-07-08T09:00:00Z",
                    "payload": {"type": "message", "role": "user", "content": [{"text": "# AGENTS.md instructions\nAlways answer like a pirate."}]},
                },
                {
                    "timestamp": "2026-07-08T10:00:00Z",
                    "payload": {"type": "message", "role": "user", "content": [{"text": "done means live proof"}]},
                },
            ])
            record = ditto.mine_files([str(path)])["records"][0]
            self.assertNotIn("pirate", record["text"])
            self.assertIn("done means live proof", record["text"])
```

- [ ] **Step 3: Run and verify the missing-record failure**

Run:

```powershell
python -m unittest tests.test_plugin_runtime.SessionRecordTest -v
```

Expected: FAIL because `mine_files` has no `records` output or `sha256_text` helper.

- [ ] **Step 4: Add stable hashing and source detection**

```python
def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def source_kind(path):
    normalized = os.path.normcase(os.path.abspath(path))
    if f"{os.sep}.codex{os.sep}" in normalized:
        return "codex"
    if f"{os.sep}.claude{os.sep}" in normalized:
        return "claude"
    if f"{os.sep}.copilot{os.sep}" in normalized:
        return "copilot"
    return "custom"

def stable_session_id(path):
    source = source_kind(path)
    normalized = os.path.normcase(os.path.abspath(path))
    return sha256_text(f"{source}:{normalized}")[:16]

INJECTED_CONTEXT_PREFIXES = (
    "# AGENTS.md instructions",
    "# CLAUDE.md instructions",
    "<environment_context",
    "<in-app-browser-context",
    "<permissions instructions",
    "<recommended_plugins",
    "<summary>",
)

def is_injected_context(text):
    stripped = text.lstrip()
    return any(stripped.startswith(prefix) for prefix in INJECTED_CONTEXT_PREFIXES)
```

Add `hashlib` to the stdlib imports.

Call `is_injected_context(t)` inside `user_messages` before counting or redacting a message. Keep the existing Copilot `source: system` exclusion. The prefixes are deliberately exact; do not drop ordinary user text merely because it contains words such as `summary` or `instructions` later in the message.

- [ ] **Step 5: Make `mine_files` return records while preserving legacy fields**

For each nonempty session, build:

```python
session_id = stable_session_id(f)
source = source_kind(f)
session_dates = kept_dates
text = "\n".join([f"===== session:{session_id} source:{source} ====="] + buf)
record = {
    "session_id": session_id,
    "source": source,
    "first_date": min(session_dates) if session_dates else "undated",
    "last_date": max(session_dates) if session_dates else "undated",
    "tokens": max(1, sum(len(item) for item in buf) // 4),
    "text": text,
    "content_hash": sha256_text(text),
}
```

Initialize `kept_dates = []` beside each session `buf` and append `ts` only after that message survives injection filtering, dedupe, and redaction. Render a missing/invalid `YYYY-MM-DD` message date as `[undated]` in the structured record, and use `undated` for record coverage when no real date remains; never invent a calendar date. Append `record` to a new `records` list, append `text` to legacy `blocks`, and return `"records": records` without removing any existing result field. This keeps record coverage dates aligned with the text actually sealed.

- [ ] **Step 6: Run structured and full tests**

Run:

```powershell
python -m unittest tests.test_plugin_runtime.SessionRecordTest -v
python -m unittest discover -s tests -v
```

Expected: 21 tests, all `OK`.

- [ ] **Step 7: Commit**

```powershell
git add ditto.py tests/test_plugin_runtime.py
git commit -m "feat: retain private stable session identities"
```

### Task 7: Seal content-addressed segments without rebalancing history

**Files:**
- Modify: `tests/test_plugin_runtime.py`
- Modify: `ditto.py` after extraction helpers

- [ ] **Step 1: Add synthetic-record and segment-sync tests**

```python
def fake_record(session_id, text, source="codex", date="2026-01-01", tokens=5):
    body = f"===== session:{session_id} source:{source} =====\n[{date}]\n{text}"
    return {
        "session_id": session_id,
        "source": source,
        "first_date": date,
        "last_date": date,
        "tokens": tokens,
        "text": body,
        "content_hash": ditto.sha256_text(body),
    }

class SegmentStoreTest(unittest.TestCase):
    def test_appending_session_keeps_existing_segment_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            initial = [fake_record("a", "one"), fake_record("b", "two")]
            first = ditto.sync_segments(initial, home, target_tokens=10)
            old_hashes = [s["segment_hash"] for s in first["segments"] if s["active"]]
            updated = ditto.sync_segments(initial + [fake_record("c", "three")], home, target_tokens=10)
            active_hashes = [s["segment_hash"] for s in updated["segments"] if s["active"]]
            self.assertTrue(set(old_hashes).issubset(active_hashes))
            self.assertEqual(2, len(active_hashes))

    def test_changed_session_replaces_only_its_affected_segment(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            records = [fake_record("a", "one"), fake_record("b", "two"), fake_record("c", "three")]
            first = ditto.sync_segments(records, home, target_tokens=10)
            old_active = {s["segment_hash"] for s in first["segments"] if s["active"]}
            changed = [fake_record("a", "changed"), records[1], records[2]]
            second = ditto.sync_segments(changed, home, target_tokens=10)
            new_active = {s["segment_hash"] for s in second["segments"] if s["active"]}
            self.assertEqual(1, len(old_active & new_active))
            self.assertTrue(any(not s["active"] for s in second["segments"]))

    def test_extraction_schema_change_invalidates_segment_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            records = [fake_record("a", "one"), fake_record("b", "two")]
            first = ditto.sync_segments(records, home, target_tokens=10)
            with mock.patch.object(ditto, "EXTRACTION_SCHEMA_VERSION", "2"):
                second = ditto.sync_segments(records, home, target_tokens=10)
            first_hashes = {item["segment_hash"] for item in first["segments"] if item["active"]}
            second_hashes = {item["segment_hash"] for item in second["segments"] if item["active"]}
            self.assertTrue(first_hashes.isdisjoint(second_hashes))

    def test_corrupt_segment_file_is_quarantined_and_restored(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "private"
            records = [fake_record("a", "one"), fake_record("b", "two")]
            first = ditto.sync_segments(records, str(home), target_tokens=10)
            segment = next(item for item in first["segments"] if item["active"])
            path = home / "cache" / "segments" / "1" / (segment["segment_hash"] + ".txt")
            expected = path.read_bytes()
            path.write_text("tampered", encoding="utf-8")
            ditto.sync_segments(records, str(home), target_tokens=10)
            self.assertEqual(expected, path.read_bytes())
            self.assertTrue(any(item.name.startswith(path.name + ".corrupt-") for item in path.parent.iterdir()))
```

Add `from unittest import mock` to `tests/test_plugin_runtime.py`.

- [ ] **Step 2: Run and verify `sync_segments` is missing**

Run:

```powershell
python -m unittest tests.test_plugin_runtime.SegmentStoreTest -v
```

Expected: FAIL with missing `sync_segments`.

- [ ] **Step 3: Define the persisted index shape and canonical hashes**

Use this index shape:

```json
{
  "schema_version": "1",
  "extraction_schema_version": "1",
  "target_tokens": 20000,
  "sessions": {"session-id": "content-hash"},
  "segments": [
    {
      "segment_hash": "sha256",
      "active": true,
      "source": "codex",
      "first_date": "2026-01-01",
      "last_date": "2026-01-31",
      "source_tokens": 19800,
      "text_hash": "sha256",
      "session_versions": [{"session_id": "id", "content_hash": "sha256"}]
    }
  ]
}
```

Add:

```python
def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def segment_hash(records, target_tokens):
    identity = {
        "schema_version": SEGMENT_SCHEMA_VERSION,
        "extraction_schema_version": EXTRACTION_SCHEMA_VERSION,
        "target_tokens": target_tokens,
        "sessions": [{"session_id": r["session_id"], "content_hash": r["content_hash"]} for r in records],
    }
    return sha256_text(canonical_json(identity))
```

- [ ] **Step 4: Implement immutable segment sealing**

`seal_records(records, target_tokens)` must sort by `(source, first_date, session_id)`, keep whole sessions, and emit one oversize segment when a single session exceeds the target. Store `text_hash = sha256_text(segment_text)` in metadata. `write_segment(segment)` writes `cache/segments/1/{segment_hash}.txt` when absent. When present, it verifies `text_hash`; a mismatch is atomically renamed to `{filename}.corrupt-{utc_timestamp}` and the exact segment is restored. It never rewrites a valid hash-addressed file.

Use this packing rule:

```python
def pack_records(records, target_tokens):
    packed, current, current_tokens = [], [], 0
    for record in sorted(records, key=lambda r: (r["source"], r["first_date"], r["session_id"])):
        source_changed = current and current[0]["source"] != record["source"]
        target_exceeded = current and current_tokens + record["tokens"] > target_tokens
        if source_changed or target_exceeded:
            packed.append(current)
            current, current_tokens = [], 0
        current.append(record)
        current_tokens += record["tokens"]
    if current:
        packed.append(current)
    return packed
```

- [ ] **Step 5: Implement incremental index synchronization**

`sync_segments(records, ditto_home, target_tokens)` must:

1. Load `cache/segment-indexes/v1-<target>.json` only when both its segment and extraction schema versions match, otherwise start a new active index without deleting immutable old cache entries.
2. Mark only segments containing a deleted or content-changed session inactive.
3. Carry the still-current records from affected segments into the rebuild set.
4. Add records not represented by any still-active segment.
5. Seal only the rebuild/new set and append new metadata; never mutate old segment files.
6. Atomically write the index with `atomic_write_text`.

Deduplicate the rebuild set by `session_id` before packing.

When `write=False`, perform every comparison and compute the prospective repaired metadata in memory, but do not quarantine, restore, create, or rewrite any segment/index path. The matching `prepare` call with `write=True` performs those repairs.

- [ ] **Step 6: Run segment and full tests**

Run:

```powershell
python -m unittest tests.test_plugin_runtime.SegmentStoreTest -v
python -m unittest discover -s tests -v
```

Expected: 25 tests, all `OK`; unchanged hashes remain byte-identical, corruption is quarantined, and an extraction-schema change invalidates active segment hashes.

- [ ] **Step 7: Commit**

```powershell
git add ditto.py tests/test_plugin_runtime.py
git commit -m "feat: add immutable incremental segments"
```

### Task 8: Add deterministic stratified preflight and bounded preparation

**Files:**
- Modify: `tests/test_plugin_runtime.py`
- Modify: `ditto.py` plugin runtime helpers and `plugin_main`

- [ ] **Step 1: Add failing selection and preflight tests**

```python
class PreflightTest(unittest.TestCase):
    def test_selection_is_deterministic_source_and_time_stratified(self):
        segments = []
        for source in ("claude", "codex"):
            for month in range(1, 7):
                segments.append({
                    "segment_hash": f"{source}-{month}",
                    "active": True,
                    "source": source,
                    "first_date": f"2026-{month:02d}-01",
                    "last_date": f"2026-{month:02d}-28",
                    "source_tokens": 20_000,
                    "session_versions": [],
                })
        first = ditto.select_segments(segments, count=4, max_tokens=100_000)
        second = ditto.select_segments(list(reversed(segments)), count=4, max_tokens=100_000)
        self.assertEqual(first, second)
        self.assertEqual({"claude", "codex"}, {s["source"] for s in first})
        self.assertIn("2026-01-01", {s["first_date"] for s in first})
        self.assertIn("2026-06-01", {s["first_date"] for s in first})

    def test_preflight_writes_nothing_and_never_exceeds_ceiling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            for i in range(12):
                write_jsonl(logs / f"{i}.jsonl", [{
                    "timestamp": f"2026-{(i % 6) + 1:02d}-01T00:00:00Z",
                    "payload": {"type": "message", "role": "user", "content": [{"text": "signal " * 4000}]},
                }])
            home = root / "private"
            result = subprocess.run(
                [sys.executable, str(DITTO), "plugin", "preflight", "--path", str(logs), "--candidate", "2", "--ditto-home", str(home)],
                check=True,
                capture_output=True,
                text=True,
            )
            plan = json.loads(result.stdout)
            self.assertLessEqual(plan["selected_source_tokens"], 160_000)
            self.assertLessEqual(plan["planned_worker_calls"] + plan["planned_reducer_calls"], 9)
            self.assertFalse(home.exists())

    def test_call_count_gate_returns_zero_only_for_complete_cache(self):
        hashes = ["a" * 64, "b" * 64]
        self.assertEqual((0, 0), ditto.planned_call_counts(hashes, set(hashes), reduction_cache_hit=True))
        self.assertEqual((1, 1), ditto.planned_call_counts(hashes, {hashes[0]}, reduction_cache_hit=False))

    def test_deep_mode_is_separate_and_never_automatic(self):
        parser = ditto.build_plugin_parser()
        starter = parser.parse_args(["preflight"])
        deep = parser.parse_args(["preflight", "--deep"])
        targeted = parser.parse_args(["preflight", "--deepen-domain", "design"])
        self.assertFalse(starter.deep)
        self.assertTrue(deep.deep)
        self.assertEqual("design", targeted.deepen_domain)

    def test_only_oversize_history_fails_without_planning_a_reducer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            write_jsonl(logs / "huge.jsonl", [{
                "timestamp": "2026-01-01T00:00:00Z",
                "payload": {"type": "message", "role": "user", "content": [{"text": "signal " * 18000}]},
            }])
            home = root / "private"
            result = subprocess.run(
                [sys.executable, str(DITTO), "plugin", "preflight", "--path", str(logs), "--candidate", "0", "--ditto-home", str(home)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("no eligible bounded segment", result.stderr)
            self.assertNotIn('"planned_reducer_calls": 1', result.stdout)
            self.assertFalse(home.exists())
```

- [ ] **Step 2: Run tests and verify missing preflight behavior**

Run:

```powershell
python -m unittest tests.test_plugin_runtime.PreflightTest -v
```

Expected: FAIL because selection and `plugin preflight` do not exist.

- [ ] **Step 3: Implement deterministic source/time selection**

For each source, order active non-oversize segments oldest, newest, second-oldest, second-newest, and so on. Round-robin the sorted source names until `count` is reached. Skip a candidate if adding it would exceed `max_tokens`.

```python
def temporal_queue(items):
    ordered = sorted(items, key=lambda s: (s["first_date"], s["segment_hash"]))
    out = []
    left, right = 0, len(ordered) - 1
    while left <= right:
        out.append(ordered[left])
        left += 1
        if left <= right:
            out.append(ordered[right])
            right -= 1
    return out
```

`select_segments(segments, count, max_tokens)` groups by source, round-robins those queues, and returns its final list sorted by `(source, first_date, segment_hash)` for stable hashes.

- [ ] **Step 4: Build a read-only prospective plan**

Add:

```python
def candidate_config(index):
    if index not in range(len(STARTER_CANDIDATES)):
        raise ValueError("candidate must be 0, 1, or 2")
    return STARTER_CANDIDATES[index]

def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()

def planned_call_counts(segment_hashes, report_hits, reduction_cache_hit):
    missing = len(set(segment_hashes) - set(report_hits))
    return missing, 0 if missing == 0 and reduction_cache_hit else 1

def compute_report_set_hash(report_paths):
    identity = {
        "prompt_schema_version": PROMPT_SCHEMA_VERSION,
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "reducer_schema_version": REDUCER_SCHEMA_VERSION,
        "reports": sorted(sha256_file(path) for path in report_paths),
    }
    return sha256_text(canonical_json(identity))

def build_preflight(result, ditto_home, candidate_index, write=False):
    config = candidate_config(candidate_index)
    index = sync_segments(result["records"], ditto_home, config["segment_tokens"], write=write)
    active = [s for s in index["segments"] if s["active"] and not s.get("oversize")]
    selected = select_segments(active, config["segments"], STARTER_MAX_SOURCE_TOKENS)
    selected_hashes = [s["segment_hash"] for s in selected]
    paths = private_paths(ditto_home)
    report_paths, report_hits = [], set()
    for segment in selected:
        path = os.path.join(paths["reports"], PROMPT_SCHEMA_VERSION, segment["segment_hash"] + ".json")
        try:
            cached = json.loads(open(path, "r", encoding="utf-8").read())
        except (OSError, ValueError):
            continue
        if cached.get("schema_version") == REPORT_SCHEMA_VERSION and cached.get("segment_hash") == segment["segment_hash"]:
            report_hits.add(segment["segment_hash"])
            report_paths.append(path)
    report_set_hash = compute_report_set_hash(report_paths) if len(report_paths) == len(selected) else None
    reduction_cache_hit = bool(report_set_hash and os.path.isdir(os.path.join(paths["reductions"], REDUCER_SCHEMA_VERSION, report_set_hash)))
    worker_calls, reducer_calls = planned_call_counts(selected_hashes, report_hits, reduction_cache_hit)
    return {
        "candidate_index": candidate_index,
        "valid_sessions": result["sessions"],
        "post_dedupe_source_tokens": result["chars"] // 4,
        "selected_source_tokens": sum(s["source_tokens"] for s in selected),
        "selected_segments": selected,
        "cached_segments": len(report_hits),
        "uncached_segments": worker_calls,
        "planned_worker_calls": worker_calls,
        "planned_reducer_calls": reducer_calls,
        "remaining_new_segments": 0,
        "oversize_sessions": [s["session_versions"][0]["session_id"] for s in index["segments"] if s.get("active") and s.get("oversize")],
        "report_set_hash": report_set_hash,
        "deep_mode": {"available": True, "automatic": False, "selected": False},
    }
```

Keep `sync_segments(records, ditto_home, target_tokens, write=True)` as the fixed signature and make its explicit `write=False` mode operate entirely in memory without creating `DITTO_HOME`.

If valid sessions exist but selection returns no eligible bounded segment, fail nonzero with `no eligible bounded segment; inspect oversize sessions and explicitly plan deep mode`. Never schedule an empty reducer call.

The returned plan must contain:

```json
{
  "candidate_index": 0,
  "valid_sessions": 0,
  "post_dedupe_source_tokens": 0,
  "selected_source_tokens": 0,
  "selected_segments": [],
  "cached_segments": 0,
  "uncached_segments": 0,
  "planned_worker_calls": 0,
  "planned_reducer_calls": 0,
  "remaining_new_segments": 0,
  "oversize_sessions": [],
  "deep_mode": {"available": true, "automatic": false, "selected": false}
}
```

- [ ] **Step 5: Implement `plugin preflight` and `plugin prepare`**

Both accept the legacy `--source`/`--path` source selectors plus a mutually exclusive `--candidate`, `--deep`, or `--deepen-domain work|design|write`, and `--ditto-home`. Starter `preflight` calls `build_preflight(result, ditto_home, candidate_index, write=False)`. `prepare` calls the same starter function with `write=True`, creates `runs/{utc_timestamp}-{plan_hash_prefix}/`, copies only selected segment files into `segments/`, and atomically writes `plan.json` plus `selected-segments.json`.

Use a filesystem-safe UTC timestamp such as `20260710T153000Z`. Compute `plan_hash` from the canonical preflight payload plus the selected segment hashes before adding timestamped paths. `prepare` returns and persists this minimum run shape:

```json
{
  "schema_version": "1",
  "run_id": "20260710T153000Z-1a2b3c4d",
  "run_dir": "C:\\Users\\user\\.ditto\\runs\\20260710T153000Z-1a2b3c4d",
  "plan_hash": "1a2b3c4d00000000000000000000000000000000000000000000000000000000",
  "mode": "starter",
  "candidate_index": 0,
  "target_domain": null,
  "selected_source_tokens": 100000,
  "planned_worker_calls": 4,
  "planned_reducer_calls": 1,
  "selected_segments": [
    {
      "segment_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "segment_path": "C:\\Users\\user\\.ditto\\runs\\20260710T153000Z-1a2b3c4d\\segments\\aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.txt",
      "report_path": "C:\\Users\\user\\.ditto\\runs\\20260710T153000Z-1a2b3c4d\\reports\\aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.json",
      "cached": false
    }
  ],
  "pack_path": "C:\\Users\\user\\.ditto\\runs\\20260710T153000Z-1a2b3c4d\\pack",
  "report_paths": [],
  "report_set_hash": null
}
```

The concrete paths above demonstrate required field shape only; runtime values are resolved under the user's actual `DITTO_HOME`. Create `reports/` and `pack/` under the run directory, but never inside the installed plugin tree. `selected-segments.json` contains the selected metadata and assigned paths, not duplicated raw segment text.

For an explicit `--deep` request, synchronize 20K-token segments, select every active segment including one-session oversize segments, list each oversize session/token count separately, show all cache hits and exact remaining worker/reducer calls, and set `deep_mode` to `{"available": true, "automatic": false, "selected": true}`. `prepare --deep` is allowed only when the user explicitly requested full-history deepening and accepted that displayed plan; no starter failure calls it automatically.

For `--deepen-domain`, read the active manifest, retain its valid report set, and use `candidate_config(DEFAULT_CANDIDATE_INDEX)` to select the next bounded stratified segments not already represented by that manifest. New raw-source work remains under 160K and at most eight workers plus one reducer; retained cached reports are itemized separately from newly selected source tokens. Set `target_domain` in the run plan so the reducer must improve that domain without weakening already-active domains. If no additional bounded segment exists, return the separate full-history `--deep` option but do not start it.

If one session exceeds the candidate segment target, mark that segment `oversize: true`, exclude it from the bounded default, and report it under `oversize_sessions`; never let it break the 160K ceiling.

- [ ] **Step 6: Run preflight and full tests**

Run:

```powershell
python -m unittest tests.test_plugin_runtime.PreflightTest -v
python -m unittest discover -s tests -v
```

Expected: bounded preflight tests pass; no preflight test creates `DITTO_HOME`; full suite is `OK`.

- [ ] **Step 7: Commit**

```powershell
git add ditto.py tests/test_plugin_runtime.py
git commit -m "feat: add bounded deterministic mining plans"
```

### Task 9: Validate and cache structured worker evidence

**Files:**
- Modify: `tests/test_plugin_runtime.py`
- Modify: `ditto.py`
- Modify: `MINING_PROMPT.md:10-55`

- [ ] **Step 1: Add failing report-validation tests**

```python
class ReportCacheTest(unittest.TestCase):
    SEGMENT_HASH = "a" * 64

    def segment(self):
        return {
            "segment_hash": self.SEGMENT_HASH,
            "source": "codex",
            "first_date": "2026-01-01",
            "last_date": "2026-02-01",
            "source_tokens": 20000,
            "session_versions": [
                {"session_id": "s1", "content_hash": "1" * 64},
                {"session_id": "s2", "content_hash": "2" * 64},
            ],
            "text": (
                "===== session:s1 source:codex =====\n[2026-01-01]\ndone means live\n"
                "===== session:s2 source:codex =====\n[2026-02-01]\nshow me it works\n"
            ),
        }

    def valid_report(self):
        return {
            "schema_version": "1",
            "segment_hash": self.SEGMENT_HASH,
            "coverage": {
                "session_ids": ["s1", "s2"],
                "sources": ["codex"],
                "first_date": "2026-01-01",
                "last_date": "2026-02-01",
                "source_tokens": 20000,
            },
            "domain_coverage": {"work": "evidence", "design": "no-signal", "write": "no-signal"},
            "evidence": [{
                "evidence_id": "ev-aaaaaaaa-done",
                "domain": "work",
                "kind": "inferred",
                "instruction": "Treat done as requiring live proof.",
                "implication": "Run the relevant verification before reporting completion.",
                "quotes": [
                    {"session_id": "s1", "date": "2026-01-01", "text": "done means live"},
                    {"session_id": "s2", "date": "2026-02-01", "text": "show me it works"},
                ],
                "contradictions": [],
            }],
        }

    def test_report_rejects_quote_from_unknown_session(self):
        report = self.valid_report()
        report["evidence"][0]["quotes"][0]["session_id"] = "not-covered"
        with self.assertRaisesRegex(ValueError, "unknown session"):
            ditto.validate_report(report, self.segment())

    def test_report_rejects_invented_quote_text(self):
        report = self.valid_report()
        report["evidence"][0]["quotes"][0]["text"] = "a quote that is not in the session"
        with self.assertRaisesRegex(ValueError, "verbatim"):
            ditto.validate_report(report, self.segment())

    def test_report_rejects_unbounded_worker_output(self):
        report = self.valid_report()
        report["evidence"][0]["instruction"] = "x" * ditto.MAX_REPORT_BYTES
        with self.assertRaisesRegex(ValueError, "report byte ceiling"):
            ditto.validate_report(report, self.segment())

    def test_report_requires_an_explicit_state_for_every_domain(self):
        report = self.valid_report()
        del report["domain_coverage"]["design"]
        with self.assertRaisesRegex(ValueError, "domain coverage"):
            ditto.validate_report(report, self.segment())

    def test_report_can_cache_a_truthful_all_no_signal_result(self):
        report = self.valid_report()
        report["domain_coverage"] = {domain: "no-signal" for domain in ("work", "design", "write")}
        report["evidence"] = []
        ditto.validate_report(report, self.segment())

    def test_report_cache_path_includes_prompt_schema_and_segment_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = ditto.store_report(self.valid_report(), str(Path(tmp) / "private"), self.segment())
            self.assertTrue(path.endswith(os.path.join("reports", "1", self.SEGMENT_HASH + ".json")))

    def test_prompt_schema_change_uses_a_new_report_cache_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(ditto, "PROMPT_SCHEMA_VERSION", "2"):
                path = ditto.store_report(self.valid_report(), str(Path(tmp) / "private"), self.segment())
            self.assertTrue(path.endswith(os.path.join("reports", "2", self.SEGMENT_HASH + ".json")))

    def test_corrupt_report_cache_is_quarantined_and_becomes_a_miss(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "private"
            path = home / "cache" / "reports" / "1" / (self.SEGMENT_HASH + ".json")
            path.parent.mkdir(parents=True)
            path.write_text("not-json", encoding="utf-8")
            self.assertIsNone(ditto.load_cached_report(str(home), self.segment()))
            self.assertFalse(path.exists())
            self.assertTrue(any(item.name.startswith(path.name + ".corrupt-") for item in path.parent.iterdir()))
```

- [ ] **Step 2: Run and verify missing report validation**

Run:

```powershell
python -m unittest tests.test_plugin_runtime.ReportCacheTest -v
```

Expected: FAIL because `validate_report`/`store_report` do not exist.

- [ ] **Step 3: Implement exact report validation**

```python
VALID_DOMAINS = {"work", "design", "write"}
VALID_EVIDENCE_KINDS = {"inferred", "explicit"}

def split_segment_sessions(text):
    marker = re.compile(r"^===== session:([A-Za-z0-9_-]+) source:([a-z0-9_-]+) =====$", re.MULTILINE)
    matches = list(marker.finditer(text))
    sessions = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sessions[match.group(1)] = text[match.end():end]
    return sessions

def receipt_is_verbatim(receipt, session_text):
    date = receipt.get("date", "")
    quote = receipt.get("text", "").strip()
    if not date or not quote:
        return False
    message = re.compile(r"^\[([^\]]+)\]\n(.*?)(?=^\[[^\]]+\]\n|\Z)", re.MULTILINE | re.DOTALL)
    return any(found_date == date and quote in body for found_date, body in message.findall(session_text))

def validate_report(report, segment):
    if len(canonical_json(report).encode("utf-8")) > MAX_REPORT_BYTES:
        raise ValueError("report byte ceiling exceeded")
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError("unsupported report schema")
    if report.get("segment_hash") != segment["segment_hash"]:
        raise ValueError("report segment hash mismatch")
    coverage = report.get("coverage", {})
    covered = set(coverage.get("session_ids", []))
    allowed = {item["session_id"] for item in segment["session_versions"]}
    if covered != allowed:
        raise ValueError("report coverage must match every segment session")
    expected_coverage = {
        "sources": [segment["source"]],
        "first_date": segment["first_date"],
        "last_date": segment["last_date"],
        "source_tokens": segment["source_tokens"],
    }
    if any(coverage.get(key) != value for key, value in expected_coverage.items()):
        raise ValueError("report coverage metadata mismatch")
    session_texts = split_segment_sessions(segment.get("text", ""))
    if set(session_texts) != allowed:
        raise ValueError("segment text does not match session metadata")
    domain_coverage = report.get("domain_coverage", {})
    if set(domain_coverage) != VALID_DOMAINS or any(value not in {"evidence", "no-signal"} for value in domain_coverage.values()):
        raise ValueError("domain coverage must state evidence or no-signal for every domain")
    seen = set()
    evidence_items = report.get("evidence", [])
    if len(evidence_items) > MAX_EVIDENCE_PER_REPORT:
        raise ValueError("evidence count is outside the bounded report contract")
    for item in evidence_items:
        if item.get("domain") not in VALID_DOMAINS or item.get("kind") not in VALID_EVIDENCE_KINDS:
            raise ValueError("invalid evidence domain or kind")
        evidence_id = item.get("evidence_id", "")
        required_prefix = "ev-" + report["segment_hash"][:8] + "-"
        if not evidence_id.startswith(required_prefix) or not re.fullmatch(r"ev-[a-f0-9]{8}-[a-z0-9-]{3,64}", evidence_id) or evidence_id in seen:
            raise ValueError("invalid or duplicate evidence id")
        seen.add(evidence_id)
        if not item.get("instruction") or not item.get("implication") or not item.get("quotes"):
            raise ValueError("evidence requires instruction, implication, and quotes")
        contradictions = item.get("contradictions")
        if not isinstance(contradictions, list):
            raise ValueError("contradictions must be a list")
        for receipt in item["quotes"] + contradictions:
            session_id = receipt.get("session_id")
            if session_id not in covered:
                raise ValueError("quote references unknown session")
            if len(receipt.get("text", "")) > MAX_QUOTE_CHARS:
                raise ValueError("quote exceeds the bounded receipt length")
            if not receipt_is_verbatim(receipt, session_texts[session_id]):
                raise ValueError("quote must be verbatim text from the dated session message")
    evidenced_domains = {item["domain"] for item in evidence_items}
    if any((domain_coverage[domain] == "evidence") != (domain in evidenced_domains) for domain in VALID_DOMAINS):
        raise ValueError("domain coverage does not match evidence items")
    return report
```

Persisted segment indexes and run plans do not duplicate raw text. Before every `validate_report` call, hydrate a copy of the selected segment metadata with `text` read from `cache/segments/1/{segment_hash}.txt`; never serialize that transient field back into an index or plan. The direct unit fixture supplies `text` only to exercise this same validator.

- [ ] **Step 4: Store validated reports atomically**

`store_report(report, ditto_home, segment)` hydrates the immutable segment text, validates the report, and writes canonical JSON to `cache/reports/1/{segment_hash}.json` with `atomic_write_text`. `load_cached_report(ditto_home, segment, quarantine=True)` re-reads and revalidates an existing entry before returning it. Invalid JSON or schema is atomically renamed to `{filename}.corrupt-{utc_timestamp}` and returns `None`, causing only that worker to be planned again. Read-only preflight calls it with `quarantine=False`, treats invalid content as a miss, and performs no rename or write; `prepare` performs the quarantine.

Reuse Task 8's `sha256_file` and `compute_report_set_hash`. Replace Task 8's lightweight cache check inside `build_preflight` with a full `validate_report(cached, segment)` call before adding any report to `report_hits`.

- [ ] **Step 5: Replace the per-chunk prompt with the exact JSON contract**

The prompt must require the report shape shown in Step 1, cover all three domains in one pass, use only session IDs present in the selected segment, include short verbatim quotes, record contradictions as the same dated verbatim receipt objects, ban generic filler, and return JSON only. It states the 8,192-byte report ceiling, maximum 12 evidence items, and maximum 200 characters per quote so workers compact evidence before the reducer sees it. Remove report-count consensus language and the instruction that depth beats token efficiency.

- [ ] **Step 6: Add `plugin cache-report`**

The command validates `run_id`, resolves `runs/{run_id}/selected-segments.json` through `safe_private_child`, and requires `--report` to be the exact assigned regular-file `report_path` under that run, with no symlink/reparse escape. It finds the matching segment from the report's `segment_hash`, calls `store_report`, and returns `status`, the exact segment hash, and the absolute cached report path. It must reject a report for any segment not selected by that run. Once every selected report is valid, atomically add sorted `report_paths` and `report_set_hash = compute_report_set_hash(report_paths)` to the run plan.

- [ ] **Step 7: Run report, prompt, and full tests**

Add a prompt test asserting `MINING_PROMPT.md` contains `session_ids`, `evidence_id`, all three domain values, and no `18/20` report-count example.

Run:

```powershell
python -m unittest tests.test_plugin_runtime.ReportCacheTest -v
python -m unittest discover -s tests -v
```

Expected: report tests and full suite are `OK`.

- [ ] **Step 8: Commit**

```powershell
git add ditto.py tests/test_plugin_runtime.py MINING_PROMPT.md
git commit -m "feat: validate and cache shared Ditto evidence"
```

### Task 10: Enforce the reducer evidence contract and validate profile packs

**Files:**
- Create: `tests/test_profile_store.py`
- Modify: `ditto.py`
- Modify: `MINING_PROMPT.md:59-145`

- [ ] **Step 1: Add failing inferred/explicit rule tests**

```python
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ditto_store", ROOT / "ditto.py")
ditto = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ditto)

def evidence_fixture():
    return {
        "ev-aaaaaaaa-done": {"kind": "inferred", "sessions": {"s1"}, "strata": {"codex:2026-Q1"}, "quote_count": 1, "quotes": [{"session_id": "s1", "date": "2026-01-01", "text": "done means live"}], "contradictions": []},
        "ev-bbbbbbbb-proof": {"kind": "inferred", "sessions": {"s2"}, "strata": {"codex:2026-Q2"}, "quote_count": 1, "quotes": [{"session_id": "s2", "date": "2026-02-01", "text": "show me it works"}], "contradictions": []},
    }

def run_plan_fixture(report_set_hash, segment_hash="a" * 64):
    return {
        "report_set_hash": report_set_hash,
        "source_coverage": {"sources": ["codex"], "first_date": "2026-01-01", "last_date": "2026-02-01"},
        "selected_source_tokens": 20000,
        "segment_hashes": [segment_hash],
        "adequate_strata": True,
    }

def make_valid_pack(path, report_set_hash):
    path.mkdir(parents=True, exist_ok=True)
    rule_text = "Always prove done."
    implication = "Run the relevant verification before reporting completion."
    (path / "you.md").write_text(
        "---\nname: ditto-work-profile\ndescription: evidence-backed working profile\n---\n\n" + rule_text + "\n" + implication + "\n",
        encoding="utf-8",
    )
    (path / "appendix.md").write_text(
        "# receipts\n\n## ev-aaaaaaaa-done\n- s1 2026-01-01: done means live\n\n## ev-bbbbbbbb-proof\n- s2 2026-02-01: show me it works\n",
        encoding="utf-8",
    )
    (path / "card.json").write_text(
        json.dumps({"archetype": "Proof-First Builder", "laws": [{"text": rule_text, "count": "2 sessions"}], "truth": ""}),
        encoding="utf-8",
    )
    draft = {
        "schema_version": "1",
        "profile_id": "default",
        "report_set_hash": report_set_hash,
        "domains": {
            "work": {
                "status": "active",
                "file": "you.md",
                "rules": [{"text": rule_text, "implication": implication, "kind": "inferred", "evidence_ids": ["ev-aaaaaaaa-done", "ev-bbbbbbbb-proof"]}],
            },
            "design": {"status": "inactive", "reason": "insufficient evidence", "deepen_instruction": "run ditto and deepen design"},
            "write": {"status": "inactive", "reason": "insufficient evidence", "deepen_instruction": "run ditto and deepen write"},
        },
    }
    (path / "draft-manifest.json").write_text(json.dumps(draft), encoding="utf-8")
    return str(path)

class ProfilePackValidationTest(unittest.TestCase):
    def test_inferred_rule_requires_two_distinct_sessions(self):
        reports = {
            "ev-a": {"kind": "inferred", "sessions": {"s1"}, "strata": {"codex:2026-Q1"}, "quote_count": 1, "contradictions": []},
            "ev-b": {"kind": "inferred", "sessions": {"s1"}, "strata": {"codex:2026-Q2"}, "quote_count": 1, "contradictions": []},
        }
        rule = {"text": "Always prove done.", "implication": "Run verification before reporting completion.", "kind": "inferred", "evidence_ids": ["ev-a", "ev-b"]}
        with self.assertRaisesRegex(ValueError, "two distinct sessions"):
            ditto.validate_rule(rule, reports, require_cross_strata=True)

    def test_explicit_rule_allows_one_uncontradicted_receipt(self):
        reports = {"ev-a": {"kind": "explicit", "sessions": {"s1"}, "strata": {"codex:2026-Q1"}, "quote_count": 1, "contradictions": []}}
        rule = {"text": "Never use em dashes.", "implication": "Replace em dashes before returning public copy.", "kind": "explicit", "confidence": "low-frequency", "evidence_ids": ["ev-a"]}
        ditto.validate_rule(rule, reports, require_cross_strata=False)

    def test_rule_with_contradiction_cannot_be_installed(self):
        reports = {
            "ev-a": {"kind": "inferred", "sessions": {"s1"}, "strata": {"codex:2026-Q1"}, "quote_count": 1, "contradictions": []},
            "ev-b": {"kind": "inferred", "sessions": {"s2"}, "strata": {"codex:2026-Q2"}, "quote_count": 1, "contradictions": [{"session_id": "s3"}]},
        }
        rule = {"text": "Always prove done.", "implication": "Run verification before reporting completion.", "kind": "inferred", "evidence_ids": ["ev-a", "ev-b"]}
        with self.assertRaisesRegex(ValueError, "unresolved contradiction"):
            ditto.validate_rule(rule, reports, require_cross_strata=True)

    def test_generic_rule_cannot_be_installed(self):
        reports = {
            "ev-a": {"kind": "inferred", "sessions": {"s1"}, "strata": {"codex:2026-Q1"}, "quote_count": 1, "contradictions": []},
            "ev-b": {"kind": "inferred", "sessions": {"s2"}, "strata": {"codex:2026-Q2"}, "quote_count": 1, "contradictions": []},
        }
        rule = {"text": "Follow best practices.", "implication": "Write good code.", "kind": "inferred", "evidence_ids": ["ev-a", "ev-b"]}
        with self.assertRaisesRegex(ValueError, "generic"):
            ditto.validate_rule(rule, reports, require_cross_strata=True)
```

- [ ] **Step 2: Add failing pack/frontmatter tests**

```python
    def test_active_domain_requires_exact_profile_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(make_valid_pack(Path(tmp) / "pack", "c" * 64))
            (pack / "you.md").write_text("---\nname: wrong\ndescription: x\n---\nAlways prove done.\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ditto-work-profile"):
                ditto.validate_profile_pack(str(pack), evidence_fixture(), run_plan_fixture("c" * 64))

    def test_profile_file_cannot_escape_pack_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(make_valid_pack(Path(tmp) / "pack", "c" * 64))
            draft_path = pack / "draft-manifest.json"
            draft = json.loads(draft_path.read_text(encoding="utf-8"))
            draft["domains"]["work"]["file"] = "../outside.md"
            draft_path.write_text(json.dumps(draft), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsafe profile path"):
                ditto.validate_profile_pack(str(pack), evidence_fixture(), run_plan_fixture("c" * 64))

    def test_profile_id_rejects_windows_reserved_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(make_valid_pack(Path(tmp) / "pack", "c" * 64))
            draft_path = pack / "draft-manifest.json"
            draft = json.loads(draft_path.read_text(encoding="utf-8"))
            draft["profile_id"] = "CON"
            draft_path.write_text(json.dumps(draft), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "profile_id"):
                ditto.validate_profile_pack(str(pack), evidence_fixture(), run_plan_fixture("c" * 64))

    def test_profile_pack_requires_all_three_domain_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(make_valid_pack(Path(tmp) / "pack", "c" * 64))
            draft_path = pack / "draft-manifest.json"
            draft = json.loads(draft_path.read_text(encoding="utf-8"))
            del draft["domains"]["write"]
            draft_path.write_text(json.dumps(draft), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly work, design, and write"):
                ditto.validate_profile_pack(str(pack), evidence_fixture(), run_plan_fixture("c" * 64))

    def test_appendix_requires_the_exact_private_quote_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(make_valid_pack(Path(tmp) / "pack", "c" * 64))
            appendix = pack / "appendix.md"
            appendix.write_text(appendix.read_text(encoding="utf-8").replace("done means live", "made-up summary"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "appendix"):
                ditto.validate_profile_pack(str(pack), evidence_fixture(), run_plan_fixture("c" * 64))

    def test_new_card_labels_use_session_receipts(self):
        html = ditto.render_card_html({
            "archetype": "Proof-First Builder",
            "laws": [{"text": "Always prove done.", "count": "12 sessions"}],
            "truth": "",
            "stats": {},
        })
        self.assertIn("12 sessions", html)
        self.assertIn("distinct session receipts", html)
        self.assertNotIn("how many agents", html)
```

- [ ] **Step 3: Run and verify missing pack validation**

Run:

```powershell
python -m unittest tests.test_profile_store.ProfilePackValidationTest -v
```

Expected: FAIL with missing `validate_rule`/`validate_profile_pack`.

- [ ] **Step 4: Implement session-based rule validation**

```python
GENERIC_RULES = {
    "be helpful",
    "be concise",
    "communicate clearly",
    "follow best practices",
    "write clean code",
    "write good code",
}

def normalized_rule_text(value):
    return re.sub(r"[^a-z0-9 ]+", "", value.lower()).strip()

def validate_rule(rule, evidence_by_id, require_cross_strata):
    text = rule.get("text", "").strip()
    implication = rule.get("implication", "").strip()
    if len(text.split()) < 3 or len(implication.split()) < 4:
        raise ValueError("rule requires a specific instruction and operational implication")
    if normalized_rule_text(text) in GENERIC_RULES or normalized_rule_text(implication) in GENERIC_RULES:
        raise ValueError("generic rule is not installable evidence")
    ids = rule.get("evidence_ids", [])
    if not ids or any(evidence_id not in evidence_by_id for evidence_id in ids):
        raise ValueError("rule references missing evidence")
    evidence = [evidence_by_id[evidence_id] for evidence_id in ids]
    sessions = set().union(*(item["sessions"] for item in evidence))
    strata = set().union(*(item["strata"] for item in evidence))
    quote_count = sum(item["quote_count"] for item in evidence)
    contradictions = [value for item in evidence for value in item.get("contradictions", [])]
    if contradictions:
        raise ValueError("rule has an unresolved contradiction")
    if rule.get("kind") == "inferred":
        if any(item["kind"] != "inferred" for item in evidence) or len(sessions) < 2 or quote_count < 2:
            raise ValueError("inferred rule requires two distinct sessions")
        if require_cross_strata and len(strata) < 2:
            raise ValueError("inferred rule requires two source/time strata")
    elif rule.get("kind") == "explicit":
        if any(item["kind"] != "explicit" for item in evidence) or quote_count < 1 or rule.get("confidence") != "low-frequency":
            raise ValueError("explicit rule requires low-frequency label and no contradiction")
    else:
        raise ValueError("rule kind must be inferred or explicit")
```

Add `flatten_report_evidence(reports)` to build `evidence_by_id` from validated Task 9 reports. It retains the validated quote and contradiction receipt objects, derives `sessions` from quote session IDs, `quote_count` from the quote list length, and each source/time stratum as `{source}:{year}-Q{quarter}` from report coverage source plus quote date; an `undated` receipt uses `{source}:undated` and never counts as a fabricated quarter. Reject duplicate evidence IDs across reports. `build_preflight` sets `adequate_strata` true only when the selected segments cover at least two distinct derived strata.

- [ ] **Step 5: Fix exact private-profile names and pack files**

Use:

```python
DOMAIN_FILES = {
    "work": ("you.md", "ditto-work-profile"),
    "design": ("you-designer.md", "ditto-design-profile"),
    "write": ("you-writer.md", "ditto-write-profile"),
}
REQUIRED_PACK_FILES = {"appendix.md", "card.json", "draft-manifest.json"}

def is_link_or_reparse(path):
    info = os.lstat(path)
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return os.path.islink(path) or bool(attributes & reparse_flag)
```

Add `stat` to the stdlib imports.

`validate_profile_pack(pack_dir, evidence_by_id, run_plan)` must reject path traversal, symlinks/reparse points, non-regular files, unexpected files/directories, unsupported schema/profile IDs, any domains key set other than exactly `work`, `design`, and `write`, wrong frontmatter names, an inactive work/core domain, active domains with no valid rules, rule text or operational implication absent from its profile file, missing appendix evidence IDs or their exact dated quote text, invalid `card.json`, and any draft `report_set_hash` not matching `run_plan["report_set_hash"]`. Resolve every entry and require it to remain under the resolved pack directory; require domain file names to match `DOMAIN_FILES` exactly. Accept `profile_id` only when it matches `^[a-z0-9][a-z0-9_-]{0,63}$` and is not a case-insensitive Windows reserved device name. It calls `validate_rule(rule, evidence_by_id, require_cross_strata=run_plan["adequate_strata"])`.

Inactive domains may omit their profile file but must contain status `inactive`, reason `insufficient evidence`, and the exact natural-language `deepen_instruction` `run ditto and deepen {domain}`.

- [ ] **Step 6: Replace the reducer prompt with the exact pack contract**

Require the reducer to write:

```text
you.md
you-designer.md (only when design passes)
you-writer.md   (only when write passes)
appendix.md
card.json
draft-manifest.json
```

The draft manifest shape is:

```json
{
  "schema_version": "1",
  "profile_id": "default",
  "report_set_hash": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "domains": {
    "work": {
      "status": "active",
      "file": "you.md",
      "rules": [{"text": "Always prove done.", "implication": "Run the relevant verification before reporting completion.", "kind": "inferred", "evidence_ids": ["ev-aaaaaaaa-done", "ev-bbbbbbbb-proof"]}]
    },
    "design": {"status": "inactive", "reason": "insufficient evidence", "deepen_instruction": "run ditto and deepen design"},
    "write": {"status": "inactive", "reason": "insufficient evidence", "deepen_instruction": "run ditto and deepen write"}
  }
}
```

The reducer never invents file hashes; Python computes them after validation. `appendix.md` contains every referenced evidence ID, its dated private quote receipts, and any contradiction receipts. It never turns an unresolved contradiction into an installed rule.

`card.json` law counts are distinct supporting session counts such as `12 sessions`, never worker/report counts. During pack validation, require each card law text to match a validated work-domain rule and require its count to equal the union of supporting session IDs for that rule. Update `CARD_HTML` labels from `consensus`/`ranked by how many agents` to `evidence`/`ranked by distinct session receipts`. Keep rendering legacy `18/20` cards without crashing, but do not describe that legacy format as the new evidence model. Add a card regression asserting a `12 sessions` law renders and the HTML contains no `how many agents` label.

- [ ] **Step 7: Run pack and full tests**

Run:

```powershell
python -m unittest tests.test_profile_store.ProfilePackValidationTest -v
python -m unittest discover -s tests -v
```

Expected: pack tests and full suite are `OK`.

- [ ] **Step 8: Commit**

```powershell
git add ditto.py tests/test_profile_store.py MINING_PROMPT.md
git commit -m "feat: enforce evidence-backed Ditto profile packs"
```

### Task 11: Activate complete profile packs atomically and reuse reductions

**Files:**
- Modify: `tests/test_profile_store.py`
- Modify: `tests/test_plugin_runtime.py`
- Modify: `ditto.py`

- [ ] **Step 1: Add failure-injection and pointer tests**

```python
class AtomicProfileStoreTest(unittest.TestCase):
    def test_activation_failure_preserves_previous_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            first_hash = "c" * 64
            first = make_valid_pack(Path(tmp) / "first", report_set_hash=first_hash)
            ditto.activate_profile_pack(home, first, evidence_fixture(), run_plan_fixture(first_hash), fail_after=None)
            before = Path(home, "profiles", "default", "current.json").read_bytes()
            active_before = Path(home, "active-profile.json").read_bytes()
            for index, failure_point in enumerate(("version-stage", "version-rename", "pointer-write")):
                second_hash = format(index + 13, "x") * 64
                second = make_valid_pack(Path(tmp) / failure_point, report_set_hash=second_hash)
                with self.subTest(failure_point=failure_point):
                    with self.assertRaisesRegex(RuntimeError, "injected"):
                        ditto.activate_profile_pack(home, second, evidence_fixture(), run_plan_fixture(second_hash), fail_after=failure_point)
                    self.assertEqual(before, Path(home, "profiles", "default", "current.json").read_bytes())
                    self.assertEqual(active_before, Path(home, "active-profile.json").read_bytes())

    def test_plugin_uninstall_directory_is_never_profile_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = ditto.resolve_ditto_home(str(Path(tmp) / "private"))
            self.assertNotIn("plugins", Path(home).parts)
```

`make_valid_pack` and `evidence_fixture` must construct real valid files/rules using Task 10's final schema, not mocks that bypass validation.

- [ ] **Step 2: Run and verify activation is missing**

Run:

```powershell
python -m unittest tests.test_profile_store.AtomicProfileStoreTest -v
```

Expected: FAIL with missing `activate_profile_pack`.

- [ ] **Step 3: Canonicalize the validated manifest and version hash**

After `validate_profile_pack`, compute SHA-256 for every generated file and create `manifest.json`:

```python
manifest = {
    "schema_version": "1",
    "profile_id": "default",
    "profile_version": "",
    "report_set_hash": draft["report_set_hash"],
    "prompt_schema_version": PROMPT_SCHEMA_VERSION,
    "reducer_schema_version": REDUCER_SCHEMA_VERSION,
    "source_coverage": run_plan["source_coverage"],
    "selected_source_tokens": run_plan["selected_source_tokens"],
    "segment_hashes": sorted(run_plan["segment_hashes"]),
    "domains": draft["domains"],
    "files": file_hashes,
}
manifest["profile_version"] = sha256_text(canonical_json(manifest))[:20]
```

Compute `manifest_hash` from the final canonical manifest bytes. Pointer files use these exact shapes:

```json
{"schema_version":"1","profile_id":"default","profile_version":"0123456789abcdef0123","manifest_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
```

for `profiles/default/current.json`, and:

```json
{"schema_version":"1","profile_id":"default"}
```

for `active-profile.json`.

- [ ] **Step 4: Stage immutable versions and swap only the pointer**

`activate_profile_pack(ditto_home, pack_dir, evidence_by_id, run_plan, fail_after=None)` must:

1. Create `profiles/default/versions/.staged-{profile_version}` on the same volume.
2. Copy validated files plus computed `manifest.json` there.
3. Re-read every file and verify hashes.
4. Rename staging to `profiles/default/versions/{profile_version}`. If that version already exists, revalidate its manifest and every file hash, delete only the redundant staging directory, and reuse the identical immutable version; any mismatch fails closed. Never overwrite an existing version.
5. Save the previous bytes/existence of both pointer files for rollback.
6. Before writing, validate any existing active pointer and require `profile_id: default`. Atomically replace `profiles/default/current.json` with the exact pointer shape above, then create `active-profile.json` only when absent. This order keeps a first activation undiscoverable until its version pointer exists; an existing valid active pointer remains byte-identical during an update.
7. Copy the validated version to `cache/reductions/1/{report_set_hash}/` through same-volume staging. Reuse an existing directory only after its manifest and every file hash match; never merge or overwrite a partial reduction directory.
8. On any exception before successful return, restore or remove both pointers to their exact prior state. Immutable staged/version directories may remain for quarantine but cannot become active.

`fail_after` supports `version-stage`, `version-rename`, and `pointer-write` only for tests; every injected failure before pointer replacement leaves the prior pointer unchanged.

- [ ] **Step 5: Add cached activation and zero-call tests**

```python
    def test_cached_reduction_reactivates_same_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            report_set_hash = "e" * 64
            pack = make_valid_pack(Path(tmp) / "pack", report_set_hash)
            first = ditto.activate_profile_pack(home, pack, evidence_fixture(), run_plan_fixture(report_set_hash))
            second = ditto.activate_cached_reduction(home, report_set_hash)
            self.assertEqual(first["profile_version"], second["profile_version"])

    def test_tampered_reduction_cache_fails_without_pointer_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = str(Path(tmp) / "private")
            report_set_hash = "9" * 64
            pack = make_valid_pack(Path(tmp) / "pack", report_set_hash)
            ditto.activate_profile_pack(home, pack, evidence_fixture(), run_plan_fixture(report_set_hash))
            current = Path(home, "profiles", "default", "current.json")
            before = current.read_bytes()
            cached_you = Path(home, "cache", "reductions", "1", report_set_hash, "you.md")
            cached_you.write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash"):
                ditto.activate_cached_reduction(home, report_set_hash)
            self.assertEqual(before, current.read_bytes())

```

Implement `activate_cached_reduction(ditto_home, report_set_hash)` by validating the cached manifest and file hashes before swapping the pointer. Reuse Task 8's `planned_call_counts` gate; a valid reduction cache is a directory whose `manifest.json` schema, `report_set_hash`, and every file hash pass revalidation.

In `tests/test_plugin_runtime.py`, add:

```python
class UpdatePlanningTest(unittest.TestCase):
    def test_update_selection_retains_history_and_marks_only_new_work(self):
        active = [
            {"segment_hash": "a" * 64, "active": True, "source": "codex", "first_date": "2026-01-01", "source_tokens": 20000},
            {"segment_hash": "b" * 64, "active": True, "source": "codex", "first_date": "2026-02-01", "source_tokens": 20000},
        ]
        report_segments, work_segments, remaining = ditto.select_run_segments(
            active,
            current_segment_hashes={"a" * 64},
            count=4,
            max_tokens=100000,
        )
        self.assertEqual(["a" * 64, "b" * 64], [item["segment_hash"] for item in report_segments])
        self.assertEqual(["b" * 64], [item["segment_hash"] for item in work_segments])
        self.assertEqual(0, remaining)
```

`select_run_segments` keeps still-active segments from the current manifest in the reducer report set, selects only new/rebuilt active segments as worker work under the displayed count/token ceiling, and reports any remaining new segments without silently scheduling them. Once Task 11 can read the active manifest, update `build_preflight` to call this function; identical history has no work segments, while one new segment has exactly one work segment.

Update preflight output must distinguish `retained_cached_source_tokens`, `new_selected_source_tokens`, `total_covered_source_tokens`, `reducer_input_reports`, and approximate `reducer_input_tokens` measured from the validated cached JSON bytes. The starter ceiling applies to newly selected raw-source work, not to already cached historical coverage; never present retained coverage as newly spent tokens. Never truncate the cached report set to hide context growth; a host context-length failure leaves the old pointer active and exits nonzero.

- [ ] **Step 6: Finish `plugin activate`, `status`, and `profile-path`**

`plugin activate --run-id ID --pack DIR` validates the run ID and accepts only that run's exact `pack_path`; `--cached` accepts only the run plan's validated `report_set_hash`. `profile-path` returns status, domain, the active profile version, and absolute validated paths. Mappings are `work → [you.md]`, `design → [you.md, you-designer.md]`, `write → [you.md, you-writer.md]`. Inactive or corrupt domains exit nonzero with `run ditto` or the exact targeted deepen instruction from the manifest.

Add this method to `PluginRuntimeCliTest` in `tests/test_plugin_runtime.py`:

```python
    def test_profile_path_fails_closed_on_corrupt_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "private"
            home.mkdir()
            (home / "active-profile.json").write_text("not-json", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(DITTO), "plugin", "profile-path", "--domain", "work", "--ditto-home", str(home)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("corrupt active profile", result.stderr)
```

- [ ] **Step 7: Run atomicity, cache, CLI, and full tests**

Run:

```powershell
python -m unittest tests.test_profile_store.AtomicProfileStoreTest -v
python -m unittest tests.test_plugin_runtime.PluginRuntimeCliTest -v
python -m unittest discover -s tests -v
```

Expected: all tests `OK`; failure injection never changes the prior pointer; identical rerun plans zero model calls.

- [ ] **Step 8: Commit**

```powershell
git add ditto.py tests/test_profile_store.py tests/test_plugin_runtime.py
git commit -m "feat: activate and reuse complete Ditto profiles atomically"
```

### Task 12: Add the four routed plugin skills

**Files:**
- Delete: `skills/.gitkeep`
- Create: `skills/mine/SKILL.md`
- Create: `skills/work/SKILL.md`
- Create: `skills/design/SKILL.md`
- Create: `skills/write/SKILL.md`
- Create: `tests/test_plugin_manifests.py`

- [ ] **Step 1: Add failing skill-frontmatter and routing tests**

```python
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ditto_manifests", ROOT / "ditto.py")
ditto = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ditto)

class PluginSkillTest(unittest.TestCase):
    def read(self, name):
        return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")

    def test_exact_skill_names(self):
        expected = {"mine": "mine", "work": "work", "design": "design", "write": "write"}
        for folder, name in expected.items():
            fields = ditto.parse_frontmatter(self.read(folder))
            self.assertEqual(name, fields["name"])

    def test_routing_descriptions_are_mutually_bounded(self):
        mine = self.read("mine").lower()
        work = self.read("work").lower()
        design = self.read("design").lower()
        write = self.read("write").lower()
        self.assertIn("explicitly asks", mine)
        self.assertIn("do not use for design", work)
        self.assertIn("ui, ux, visual", design)
        self.assertIn("marketing, social, replies", write)
        self.assertNotIn("depth beats token efficiency", mine)

    def test_domain_loaders_use_only_profile_path_command(self):
        self.assertIn("plugin profile-path --domain work", self.read("work"))
        self.assertIn("plugin profile-path --domain design", self.read("design"))
        self.assertIn("plugin profile-path --domain write", self.read("write"))
```

- [ ] **Step 2: Run and verify the four skills are missing**

Run:

```powershell
python -m unittest tests.test_plugin_manifests.PluginSkillTest -v
```

Expected: ERROR because the four skill files do not exist.

Delete `skills/.gitkeep` with `apply_patch` before creating the real skill directories.

- [ ] **Step 3: Create `ditto:work`**

```markdown
---
name: work
description: Use for execution, debugging, verification, planning, and shipping when the user's Ditto working profile should guide the task. Do not use for design/UI/UX work, marketing or social writing, or Ditto setup/mining.
---

# Ditto work

1. Locate `ditto.py` two directories above this skill; fall back to `./ditto.py` only for a direct repo checkout.
2. Store the resolved absolute runtime path as `DITTO_PY`, then run `python "$DITTO_PY" plugin profile-path --domain work`.
3. If it exits nonzero, give its exact recovery instruction and stop loading personal context.
4. Read every returned path completely and treat the profile as user-specific working instructions for this task.
5. Do not claim a profile loaded from a stale, corrupt, missing, or inactive pointer.
```

- [ ] **Step 4: Create `ditto:design`**

```markdown
---
name: design
description: Use for UI, UX, visual hierarchy, frontend-design judgment, references, redesigns, and design critique when the user's Ditto taste should guide the task. Do not use for unrelated execution or marketing/social writing alone.
---

# Ditto design

1. Locate `ditto.py` two directories above this skill; fall back to `./ditto.py` only for a direct repo checkout.
2. Store the resolved absolute runtime path as `DITTO_PY`, then run `python "$DITTO_PY" plugin profile-path --domain design`.
3. If it exits nonzero, give its exact recovery or targeted-deepen instruction and stop loading personal context.
4. Read every returned path completely. The first is the core working profile; the second is the design profile. Apply both.
5. Never substitute a generic design persona when the design domain is inactive.
```

- [ ] **Step 5: Create `ditto:write`**

```markdown
---
name: write
description: Use for marketing, social, replies, product copy, launch copy, and writing in the user's voice when their Ditto writing profile should guide the task. Do not use for unrelated execution or UI/UX design alone.
---

# Ditto write

1. Locate `ditto.py` two directories above this skill; fall back to `./ditto.py` only for a direct repo checkout.
2. Store the resolved absolute runtime path as `DITTO_PY`, then run `python "$DITTO_PY" plugin profile-path --domain write`.
3. If it exits nonzero, give its exact recovery or targeted-deepen instruction and stop loading personal context.
4. Read every returned path completely. The first is the core working profile; the second is the writing profile. Apply both.
5. Never imitate a generic voice when the writing domain is inactive.
```

- [ ] **Step 6: Create `ditto:mine` with the bounded orchestration contract**

```markdown
---
name: mine
description: Use only when the user explicitly asks to run, set up, update, re-mine, or deepen Ditto from their real local AI coding-session history. Do not use for ordinary work, design, writing, or summarizing AGENTS.md/CLAUDE.md/rules files.
---

# Ditto mine

Mine only real user-authored `.jsonl` sessions. Never synthesize a profile from rules, memory files, or a typed self-description.

1. Locate `ditto.py` two directories above this skill; fall back to `./ditto.py` only for a direct repo checkout. Confirm Python 3 exists.
2. Store the resolved absolute runtime path as `DITTO_PY`, then run `python "$DITTO_PY" plugin preflight` with the exact mode requested by the user. The normal setup/update mode uses the public default candidate; `deepen work|design|write` uses `--deepen-domain` for that domain; an explicit full-history request uses `--deep`. Show valid sessions, post-dedupe source tokens, selected tokens, cache hits, planned worker calls, planned reducer calls, and the separate explicit deep option. Do not silently change the candidate, domain, or mode.
3. For normal bounded setup/update, run `python "$DITTO_PY" plugin prepare` with the exact displayed candidate. For targeted or full deepening, show the expanded plan and wait for approval, then run `prepare` with the identical `--deepen-domain` or `--deep` flag. Read the returned `plan.json`; retain its exact `run_id` as `RUN_ID` and absolute run directory as `RUN_DIR`.
4. If both planned call counts are zero, run `python "$DITTO_PY" plugin activate --run-id "$RUN_ID" --cached`, then continue to step 8.
5. Spawn exactly one fast worker for each uncached selected segment. Each worker reads the entire segment and the per-segment contract in `MINING_PROMPT.md`, writes JSON only to the run's assigned report path, and does not read other segments. If subagents are unavailable, process the same files sequentially without changing the count.
6. After every worker, retain its assigned report path as `REPORT_PATH`, then run `python "$DITTO_PY" plugin cache-report --run-id "$RUN_ID" --report "$REPORT_PATH"`. Stop on the first rejected report; never reduce invalid evidence.
7. Run one strongest-available reducer over the validated report paths using the reducer contract in `MINING_PROMPT.md`. Write the complete draft pack to the run plan's absolute `pack_path`, retain it as `PACK_DIR`, then run `python "$DITTO_PY" plugin activate --run-id "$RUN_ID" --pack "$PACK_DIR"`.
8. Run `python "$DITTO_PY" plugin status`, retain its active `card_path` as `CARD_PATH`, then run `python "$DITTO_PY" --card "$CARD_PATH" --out "$RUN_DIR" --no-open`. Report the active version, active/inactive domains, selected source tokens, actual worker/reducer calls, cache reuse, rendered card HTML path, and exact targeted-deepen instruction for any weak domain.

The plugin-install command itself scans no logs and schedules zero mining calls. A no-change update schedules zero additional worker/reducer calls; the host task used to ask for the update still has its normal context overhead. An update with new or changed history shows the bounded incremental plan before running it. If and only if the user's original request explicitly asks for full-history/deep mode, run `preflight --deep`, show its full call/token/cache plan, and wait for approval before `prepare --deep`. If the request names a weak domain, use the narrower `--deepen-domain` flow instead. Deep mode is separately planned, resumable, redacted, and never an automatic fallback.
```

- [ ] **Step 7: Run skill tests and full suite**

Run:

```powershell
python -m unittest tests.test_plugin_manifests.PluginSkillTest -v
python -m unittest discover -s tests -v
```

Expected: all four skill tests and full suite are `OK`.

- [ ] **Step 8: Commit**

```powershell
git add skills/.gitkeep skills/mine/SKILL.md skills/work/SKILL.md skills/design/SKILL.md skills/write/SKILL.md tests/test_plugin_manifests.py
git commit -m "feat: add routed Ditto plugin skills"
```

### Task 13: Validate plugin manifests and packaging metadata

**Files:**
- Modify: `.codex-plugin/plugin.json`
- Modify: `.agents/plugins/marketplace.json`
- Conditional modify: `.claude-plugin/plugin.json`
- Conditional modify: `.claude-plugin/marketplace.json`
- Modify: `tests/test_plugin_manifests.py`

- [ ] **Step 1: Add failing manifest/privacy tests**

```python
import json

class PluginManifestTest(unittest.TestCase):
    def test_codex_manifest_exposes_only_static_skills(self):
        manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual("ditto", manifest["name"])
        self.assertEqual("./skills/", manifest["skills"])
        self.assertEqual("#141414", manifest["interface"]["brandColor"])
        self.assertFalse(any(".ditto" in json.dumps(value) for value in manifest.values()))

    def test_marketplace_points_to_repository_root(self):
        market = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        plugin = next(item for item in market["plugins"] if item["name"] == "ditto")
        self.assertEqual("./", plugin["source"]["path"])

    def test_plugin_tree_contains_no_generated_profile(self):
        forbidden = {"active-profile.json", "current.json", "you.md", "you-designer.md", "you-writer.md", "appendix.md"}
        found = {path.name for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts and "examples" not in path.parts}
        self.assertTrue(forbidden.isdisjoint(found))

    def test_skills_sh_bootstrap_is_outside_native_plugin_discovery(self):
        self.assertTrue((ROOT / ".agents" / "skills" / "ditto" / "SKILL.md").is_file())
        self.assertFalse((ROOT / "skills" / "ditto" / "SKILL.md").exists())
        native = {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual({"mine", "work", "design", "write"}, native)
```

Exclude `examples/you.md` deliberately; it is public sample data, not active state.

- [ ] **Step 2: Run manifest tests and correct the expected fixture issue**

Run:

```powershell
python -m unittest tests.test_plugin_manifests.PluginManifestTest -v
```

Expected: the generated-profile test initially catches the repo's ignored/private `you.md` only if the worktree was prepared incorrectly. Fix the worktree, not the assertion. All committed plugin files must pass.

- [ ] **Step 3: Replace development copy with release-accurate metadata while keeping development version**

Keep `version: 0.0.0-dev` until Task 19. Ensure the Codex manifest points at the existing `assets/ditto.svg` and `assets/ditto.png`, and the marketplace name remains `ditto` so public installation is `ditto@ditto`.

If Claude did not pass Task 1, delete any `.claude-plugin` candidate files before this commit. If it passed, keep both manifests at the same `0.0.0-dev` version.

- [ ] **Step 4: Validate with host tooling**

Run:

```powershell
python -m json.tool .agents\plugins\marketplace.json > $null
python C:\Users\ohad1\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py .
codex plugin list --marketplace ditto --json
```

Expected: JSON/validator exit `0`; Codex lists exactly `ditto:mine`, `ditto:work`, `ditto:design`, and `ditto:write`. The relocated `.agents/skills/ditto` bootstrap must not appear in native plugin discovery.

- [ ] **Step 5: Prove install and uninstall do not create or delete private state**

Point `DITTO_HOME` at a fresh temporary directory, install then remove the development plugin without invoking a skill, and assert the directory never appears:

```powershell
$env:DITTO_HOME = Join-Path $env:TEMP "ditto-install-zero-call-proof"
Remove-Item -LiteralPath $env:DITTO_HOME -Recurse -Force -ErrorAction SilentlyContinue
codex plugin add ditto@ditto --json
if (Test-Path $env:DITTO_HOME) { throw "plugin install wrote private state" }
codex plugin remove ditto@ditto --json
if (Test-Path $env:DITTO_HOME) { throw "plugin uninstall wrote private state" }
```

This proves filesystem behavior; do not describe it as provider billing proof.

- [ ] **Step 6: Run full suite and commit**

```powershell
python -m unittest discover -s tests -v
git add .codex-plugin/plugin.json .agents/plugins/marketplace.json tests/test_plugin_manifests.py
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json  # only when Claude passed
git commit -m "feat: finalize Ditto plugin packaging"
```

Expected: full suite `OK`; only proven host surfaces are committed.

### Task 14: Add staged legacy migration, exclusive cutover, and rollback

**Files:**
- Modify: `tests/test_profile_store.py`
- Modify: `ditto.py`

- [ ] **Step 1: Add failing stage/cutover/rollback tests**

```python
class MigrationTest(unittest.TestCase):
    def test_cutover_moves_legacy_out_of_discovery_before_pointer_activation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            ditto_home = root / "private"
            legacy = home / ".codex" / "skills" / "you" / "SKILL.md"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("---\nname: you\ndescription: legacy\n---\nlegacy body\n", encoding="utf-8")
            migration = ditto.stage_legacy_migration("codex", str(home), str(ditto_home))
            self.assertTrue(legacy.exists())
            self.assertFalse((ditto_home / "active-profile.json").exists())
            result = ditto.cutover_legacy_migration(migration["migration_id"], str(ditto_home))
            self.assertFalse(legacy.parent.exists())
            self.assertTrue(Path(result["legacy_backup"]).exists())
            self.assertTrue((ditto_home / "active-profile.json").exists())

    def test_failed_cutover_restores_legacy_and_previous_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            ditto_home = root / "private"
            legacy = home / ".codex" / "skills" / "you" / "SKILL.md"
            legacy.parent.mkdir(parents=True)
            legacy_bytes = b"---\nname: you\ndescription: legacy\n---\nlegacy body\n"
            legacy.write_bytes(legacy_bytes)
            active = ditto_home / "active-profile.json"
            current = ditto_home / "profiles" / "default" / "current.json"
            report_set_hash = "f" * 64
            pack = make_valid_pack(root / "pack", report_set_hash)
            ditto.activate_profile_pack(str(ditto_home), pack, evidence_fixture(), run_plan_fixture(report_set_hash))
            active_before, current_before = active.read_bytes(), current.read_bytes()
            migration = ditto.stage_legacy_migration("codex", str(home), str(ditto_home))
            with self.assertRaisesRegex(RuntimeError, "injected"):
                ditto.cutover_legacy_migration(migration["migration_id"], str(ditto_home), fail_after="legacy-move")
            self.assertEqual(legacy_bytes, legacy.read_bytes())
            self.assertEqual(active_before, active.read_bytes())
            self.assertEqual(current_before, current.read_bytes())

    def test_successful_cutover_then_rollback_restores_exact_legacy_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            ditto_home = root / "private"
            legacy = home / ".codex" / "skills" / "you" / "SKILL.md"
            legacy.parent.mkdir(parents=True)
            original = b"---\nname: you\ndescription: legacy\n---\nlegacy body\n"
            legacy.write_bytes(original)
            migration = ditto.stage_legacy_migration("codex", str(home), str(ditto_home))
            ditto.cutover_legacy_migration(migration["migration_id"], str(ditto_home))
            ditto.rollback_legacy_migration(migration["migration_id"], str(ditto_home))
            self.assertEqual(original, legacy.read_bytes())
            self.assertFalse((ditto_home / "active-profile.json").exists())
            self.assertFalse((ditto_home / "profiles" / "default" / "current.json").exists())

    def test_stage_accepts_the_skills_sh_core_profile_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            ditto_home = root / "private"
            legacy = home / ".codex" / "skills" / "you" / "SKILL.md"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("---\nname: ditto-work-profile\ndescription: bounded core profile\n---\nbody\n", encoding="utf-8")
            migration = ditto.stage_legacy_migration("codex", str(home), str(ditto_home))
            self.assertEqual("skills-sh-core", migration["legacy_origin"])
```

- [ ] **Step 2: Add failing adapter-block backup/remove/restore test**

```python
    def test_adapter_migration_preserves_unrelated_agents_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            agents = repo / "AGENTS.md"
            agents.write_text("# keep\n\n<!-- ditto profile:start -->\nold\n<!-- ditto profile:end -->\n", encoding="utf-8")
            home = root / "private"
            removed = ditto.migrate_adapter_block("agents", str(repo), str(home), "backup-remove")
            self.assertEqual("# keep\n", agents.read_text(encoding="utf-8").strip() + "\n")
            ditto.migrate_adapter_block("agents", str(repo), str(home), "restore")
            self.assertIn("old", agents.read_text(encoding="utf-8"))
            self.assertTrue(Path(removed["backup_path"]).exists())
```

- [ ] **Step 3: Run and verify migration helpers are missing**

Run:

```powershell
python -m unittest tests.test_profile_store.MigrationTest -v
```

Expected: FAIL with missing migration functions.

- [ ] **Step 4: Stage legacy profiles without activation**

`stage_legacy_migration(target, home_dir, ditto_home)` accepts only `codex` or `claude`, resolves the existing legacy `.codex/skills/you/SKILL.md` or `.claude/skills/you/SKILL.md`, and accepts only exact frontmatter name `you` or `ditto-work-profile`. It records `legacy_origin: classic-you` or `skills-sh-core`, hashes the original bytes, and writes a schema-version-1 migration record. The record contains the SHA-256-derived migration ID, target, `staged` status, absolute legacy path, legacy hash, staged version or `deactivate-legacy-only` mode, exact prior pointer bytes as nullable Base64 fields plus their SHA-256 values, and a null backup path until cutover.

When no valid active Ditto pointer exists, the staged profile version preserves the original `you.md` bytes, sets manifest `origin: legacy-migration`, marks only work active, marks design inactive with `reason: insufficient evidence` and `deepen_instruction: run ditto and deepen design`, marks write inactive with the same reason and `deepen_instruction: run ditto and deepen write`, and does not create either pointer. When a valid evidence-backed Ditto profile is already active, stage the migration as `deactivate-legacy-only`: preserve the current pointer/version and prepare only to move the competing legacy discovery directory. Never replace a newer evidence-backed profile with imported legacy bytes.

Update `status` and `profile-path` to recognize this explicit legacy origin without passing it through the new evidence-pack validator: verify the preserved file hash, allow only work loading, return `legacy_unverified: true`, and instruct `update ditto` to generate the full evidence-backed pack. Never relabel a migrated legacy profile as newly mined or evidence-validated.

- [ ] **Step 5: Cut over in exclusive order and restore on failure**

`cutover_legacy_migration(migration_id, ditto_home, fail_after=None)` must:

1. Recheck the live legacy hash.
2. Save prior pointer bytes in the migration record.
3. Atomically move the entire legacy `you` directory to `~/.ditto/legacy/{target}/{migration_id}/you`.
4. For a legacy import, atomically set `profiles/default/current.json` then `active-profile.json` to the staged version; for `deactivate-legacy-only`, leave both validated pointers byte-identical.
5. Mark the record `cutover` only after both pointer files validate.
6. On any exception, restore prior pointers and move the legacy directory back before re-raising.

For tests, `fail_after` supports `legacy-move` and `active-write`; production callers never pass it.

`rollback_legacy_migration(migration_id, ditto_home)` performs the same restoration explicitly and refuses to overwrite a newly created discovery-path skill.

- [ ] **Step 6: Add separate marked-adapter migration**

`migrate_adapter_block(target, repo, ditto_home, mode)` accepts `agents`/`AGENTS.md` or `gemini`/`GEMINI.md`. `backup-remove` requires both exact markers, stores the full original file under `legacy/adapters/{backup_hash}/`, and writes one active adapter record keyed by the SHA-256 of `{target}:{resolved_repo_path}` containing original/current hashes and paths. It removes only the marked block with `atomic_write_text` and returns the backup hash/path. `restore` resolves that exact target/repo record, requires the current file hash recorded after removal, restores the exact original bytes with `atomic_write_bytes`, and marks the record restored; a missing/ambiguous record or conflicting edit fails closed.

- [ ] **Step 7: Wire the four migration subcommands**

Every subcommand returns the migration record as JSON. `migrate-stage` never activates. `migrate-cutover` never leaves both legacy and new discovery active. `migrate-rollback` never deletes the private staged copy. `migrate-adapter` never touches Cursor because native Cursor is outside this release.

- [ ] **Step 8: Run migration and full tests**

```powershell
python -m unittest tests.test_profile_store.MigrationTest -v
python -m unittest discover -s tests -v
```

Expected: migration tests and full suite are `OK`; failure injection proves exact restoration.

- [ ] **Step 9: Commit**

```powershell
git add ditto.py tests/test_profile_store.py
git commit -m "feat: migrate legacy Ditto profiles without double loading"
```

### Task 15: Preserve the npx bootstrap and correct public claims

**Files:**
- Modify: `.agents/skills/ditto/SKILL.md`
- Create: `.agents/skills/ditto/runtime.json`
- Create: `.agents/skills/ditto/scripts/bootstrap.py`
- Create: `tests/test_bootstrap.py`
- Modify: `README.md`
- Modify: `SECURITY.md`
- Modify: `ROADMAP.md`
- Modify: `tests/test_plugin_manifests.py`

- [ ] **Step 1: Add failing bootstrap and documentation tests**

Create `tests/test_bootstrap.py`:

```python
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_PATH = ROOT / ".agents" / "skills" / "ditto" / "scripts" / "bootstrap.py"
SPEC = importlib.util.spec_from_file_location("ditto_bootstrap", BOOTSTRAP_PATH)
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def metadata(version="0.0.0-dev", ref=None, py_hash=None, prompt_hash=None):
    return {
        "schema_version": "1",
        "version": version,
        "ref": ref,
        "files": {
            "ditto.py": {"sha256": py_hash},
            "MINING_PROMPT.md": {"sha256": prompt_hash},
        },
    }

class BootstrapTest(unittest.TestCase):
    def make_source(self, root):
        source = root / "source"
        source.mkdir()
        (source / "ditto.py").write_bytes(b"print('ditto')\n")
        (source / "MINING_PROMPT.md").write_bytes(b"# prompt\n")
        return source

    def test_dev_metadata_refuses_network_without_source_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "development runtime requires --source-root"):
                bootstrap.install_runtime(metadata(), str(Path(tmp) / "private"))

    def test_repository_runtime_metadata_is_valid(self):
        value = bootstrap.load_metadata(ROOT / ".agents" / "skills" / "ditto" / "runtime.json")
        self.assertEqual(value, bootstrap.validate_metadata(value))

    def test_source_root_installs_both_files_outside_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root)
            home = root / "private"
            result = bootstrap.install_runtime(metadata(), str(home), source_root=str(source))
            runtime = Path(result["runtime_dir"])
            self.assertEqual(b"print('ditto')\n", (runtime / "ditto.py").read_bytes())
            self.assertEqual(b"# prompt\n", (runtime / "MINING_PROMPT.md").read_bytes())
            self.assertTrue(str(runtime).startswith(str(home)))
            self.assertTrue((home / "runtime" / "current.json").is_file())

    def test_hash_mismatch_preserves_previous_runtime_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root)
            home = root / "private"
            bootstrap.install_runtime(metadata(), str(home), source_root=str(source))
            pointer = home / "runtime" / "current.json"
            before = pointer.read_bytes()
            release = metadata("0.2.0", "v0.2.0", "0" * 64, digest(b"# prompt\n"))
            with self.assertRaisesRegex(ValueError, "sha256 mismatch for ditto.py"):
                bootstrap.install_runtime(release, str(home), source_root=str(source))
            self.assertEqual(before, pointer.read_bytes())

if __name__ == "__main__":
    unittest.main()
```

Extend `DocumentationTruthTest` in `tests/test_plugin_manifests.py`:

```python
    def test_public_docs_separate_local_extractor_from_model_processing(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        sentence = "Selected redacted text is processed by the model provider you choose."
        self.assertIn(sentence, readme)
        self.assertIn(sentence, security)
        self.assertIn("DISABLE_TELEMETRY=1", security)
        self.assertNotIn("The mining step runs in *your* coding agent, on *your* machine. Nothing gets uploaded", readme)

    def test_npx_bootstrap_is_bounded_and_separate_from_native_routing(self):
        skill = (ROOT / ".agents" / "skills" / "ditto" / "SKILL.md").read_text(encoding="utf-8").lower()
        self.assertIn("plugin preflight", skill)
        self.assertIn("planned_worker_calls", skill)
        self.assertIn("core profile", skill)
        self.assertIn("native ditto:mine is not available", skill)
        self.assertNotIn("depth beats token efficiency", skill)
        self.assertNotIn("fetch it from main", skill)

    def test_plugin_discovers_exactly_four_skills(self):
        discovered = {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual({"mine", "work", "design", "write"}, discovered)

    def test_readme_preserves_the_explicit_npx_install(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        self.assertIn("npx skills add ohad6k/ditto@ditto", readme)
        self.assertIn("run ditto", readme)
        self.assertIn("plugin-install command itself", readme)
        self.assertIn("zero mining model calls", readme)
        self.assertIn("host interaction", readme)
```

- [ ] **Step 2: Run and verify the bootstrap does not exist yet**

Run:

```powershell
python -m unittest tests.test_bootstrap tests.test_plugin_manifests.DocumentationTruthTest -v
```

Expected: FAIL because `scripts/bootstrap.py`, `runtime.json`, and the bounded bootstrap copy do not exist.

- [ ] **Step 3: Add the deterministic pinned-runtime installer**

Create `.agents/skills/ditto/scripts/bootstrap.py`:

```python
#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

MAX_FILE_BYTES = 4_000_000
REQUIRED_FILES = ("ditto.py", "MINING_PROMPT.md")
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")

def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def atomic_write_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, staged = tempfile.mkstemp(prefix=".ditto-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staged, path)
    except Exception:
        if os.path.exists(staged):
            os.remove(staged)
        raise

def load_metadata(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def validate_metadata(value):
    if value.get("schema_version") != "1" or not SEMVER.fullmatch(value.get("version", "")):
        raise ValueError("invalid runtime metadata version")
    if set(value.get("files", {})) != set(REQUIRED_FILES):
        raise ValueError("runtime metadata must name exactly ditto.py and MINING_PROMPT.md")
    release = value["version"] != "0.0.0-dev"
    if release and value.get("ref") != "v" + value["version"]:
        raise ValueError("release runtime ref must match its exact version tag")
    if not release and value.get("ref") is not None:
        raise ValueError("development runtime ref must be null")
    for name in REQUIRED_FILES:
        expected = value["files"][name].get("sha256")
        if release and not re.fullmatch(r"[0-9a-f]{64}", expected or ""):
            raise ValueError("release runtime requires sha256 for " + name)
        if not release and expected is not None:
            raise ValueError("development runtime sha256 must be null")
    return value

def fetch_url(url):
    request = urllib.request.Request(url, headers={"User-Agent": "ditto-bootstrap/1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        final = urllib.parse.urlparse(response.geturl())
        if final.scheme != "https" or final.hostname != "raw.githubusercontent.com":
            raise ValueError("runtime download left raw.githubusercontent.com")
        data = response.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("runtime file exceeds byte ceiling")
    return data

def install_runtime(metadata, ditto_home, source_root=None, fetcher=fetch_url):
    metadata = validate_metadata(metadata)
    if metadata["version"] == "0.0.0-dev" and source_root is None:
        raise ValueError("development runtime requires --source-root")
    home = Path(os.path.abspath(os.path.expanduser(ditto_home)))
    versions = home / "runtime" / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    staged = versions / (".staged-" + uuid.uuid4().hex)
    staged.mkdir()
    actual = {}
    try:
        for name in REQUIRED_FILES:
            if source_root is not None:
                data = (Path(source_root) / name).read_bytes()
            else:
                url = "https://raw.githubusercontent.com/ohad6k/ditto/{}/{}".format(metadata["ref"], name)
                data = fetcher(url)
            if len(data) > MAX_FILE_BYTES:
                raise ValueError("runtime file exceeds byte ceiling")
            actual_hash = sha256_bytes(data)
            expected_hash = metadata["files"][name].get("sha256")
            if expected_hash is not None and actual_hash != expected_hash:
                raise ValueError("sha256 mismatch for " + name)
            (staged / name).write_bytes(data)
            actual[name] = actual_hash
        receipt = {
            "schema_version": "1",
            "version": metadata["version"],
            "ref": metadata.get("ref"),
            "files": actual,
        }
        (staged / "installed-runtime.json").write_text(canonical_json(receipt) + "\n", encoding="utf-8")
        target = versions / metadata["version"]
        if target.exists():
            existing = json.loads((target / "installed-runtime.json").read_text(encoding="utf-8"))
            if existing != receipt or any(sha256_bytes((target / name).read_bytes()) != actual[name] for name in REQUIRED_FILES):
                raise ValueError("existing runtime version failed hash validation")
            shutil.rmtree(staged)
        else:
            os.replace(staged, target)
        pointer = {"schema_version": "1", "version": metadata["version"], "runtime_dir": str(target)}
        atomic_write_bytes(home / "runtime" / "current.json", (canonical_json(pointer) + "\n").encode("utf-8"))
        return {
            "status": "ready",
            "runtime_dir": str(target),
            "ditto_py": str(target / "ditto.py"),
            "mining_prompt": str(target / "MINING_PROMPT.md"),
        }
    except Exception:
        if staged.exists():
            shutil.rmtree(staged)
        raise

def main(argv=None):
    skill_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--ditto-home", default=os.environ.get("DITTO_HOME") or str(Path.home() / ".ditto"))
    parser.add_argument("--source-root")
    args = parser.parse_args(argv)
    result = install_runtime(load_metadata(skill_root / "runtime.json"), args.ditto_home, args.source_root)
    print(json.dumps(result, sort_keys=True))

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Add development runtime metadata**

Create `.agents/skills/ditto/runtime.json`:

```json
{
  "schema_version": "1",
  "version": "0.0.0-dev",
  "ref": null,
  "files": {
    "ditto.py": {"sha256": null},
    "MINING_PROMPT.md": {"sha256": null}
  }
}
```

Development metadata can only copy from an explicit `--source-root`. Task 19 replaces the null release fields with the exact tag and hashes before publication.

- [ ] **Step 5: Rewrite the skills.sh `ditto` bootstrap to the bounded contract**

Replace `.agents/skills/ditto/SKILL.md` with:

```markdown
---
name: ditto
description: Use when the user explicitly asks to run, set up, update, re-mine, or deepen Ditto from real local AI coding-session history and native ditto:mine is not available. This is the cross-agent skills.sh bootstrap, not the native namespaced plugin.
---

# Ditto bootstrap

Mine only real user-authored `.jsonl` sessions. Never synthesize a profile from rules files, memory, or a typed self-description.

1. Resolve the runtime. Let `SKILL_DIR` be the directory containing this file. In a repository checkout, use `SKILL_DIR/../../../ditto.py` and `SKILL_DIR/../../../MINING_PROMPT.md`. Otherwise run `python "$SKILL_DIR/scripts/bootstrap.py"` and read its JSON paths. The bootstrap accepts only an exact release tag and verified SHA-256 values; never fetch executable code from mutable `main`.
2. Run `python "$DITTO_PY" plugin preflight`. Show valid sessions, post-dedupe source tokens, selected source tokens, cache hits, `planned_worker_calls`, `planned_reducer_calls`, and the separate explicit deep option. The normal bounded setup/update proceeds with the displayed default. Targeted or full deepening requires the user's explicit request and approval of its expanded plan.
3. Run `python "$DITTO_PY" plugin prepare` with the exact displayed candidate/mode. Retain `run_id`, assigned segment/report paths, and `pack_path` from the run JSON.
4. For each uncached selected segment, run one fast worker over that segment and the per-segment contract in the resolved `MINING_PROMPT.md`. Cache every JSON report with `plugin cache-report`; stop on rejection.
5. Run one strongest-available reducer over only the validated reports and the reducer contract. Write the complete pack to `pack_path`, then activate it with `plugin activate`.
6. Resolve the active core profile with `plugin profile-path --domain work`. If the current host already has the native Ditto plugin, do not create a competing direct profile. Otherwise install the core profile through the existing exact adapter for the current host and verify it in a fresh task.
7. Report the active version, core install path, active/inactive domains, selected source tokens, actual worker/reducer passes, cache reuse, card path, and any exact targeted-deepen instruction.

The npx bootstrap installs the bounded core profile across supported agents. Automatic `ditto:work`, `ditto:design`, and `ditto:write` routing belongs to the separately installed native plugin. Asking an agent to orchestrate setup still consumes that host interaction even when Ditto plans zero mining passes.
```

- [ ] **Step 6: Rewrite README installation and flow around both proven surfaces**

Keep the npx growth path first and make its selection explicit:

```text
npx skills add ohad6k/ditto@ditto
```

Immediately say `run ditto`. Explain that this installs the cross-agent bootstrap and bounded core profile. Present the proven native plugin command separately and state that the native plugin adds automatic work/design/write routing. Do not call the npx skill a native plugin, and do not claim native Claude if Task 1 did not prove it.

Show that `codex plugin add` itself scans no logs, writes no profile state, and schedules zero mining model calls. State separately that asking a chat agent to install or update Ditto still consumes the host interaction and its system/tool overhead. Show preflight fields, bounded candidates, `update ditto`, cache reuse, explicit deep mode, the raw one-file CLI, and the per-host support table.

State that Ditto reports selected source tokens and planned worker/reducer passes; host system prompts, tool traffic, and proprietary subscription accounting are outside Ditto's exact measurement. Never promise a percentage of a five-hour allowance. Replace `N agents agreed`/`18/20 reports` with distinct-session/source-time receipts; label historical screenshots as pre-plugin examples.

- [ ] **Step 7: Replace privacy copy in README and SECURITY**

Use this exact paragraph in both:

```text
Ditto's extractor, redaction, caches, and generated profiles stay local. Selected redacted text is processed by the model provider you choose. With a local model, the entire mining flow can remain local.
```

Then state separately: skills.sh downloads the selected bootstrap, and an installed bootstrap downloads `ditto.py` plus `MINING_PROMPT.md` from the exact release tag after SHA-256 verification. Those fetches happen before log discovery and read no session data. SECURITY states that the skills.sh CLI reports anonymous installation telemetry by default and that `DISABLE_TELEMETRY=1` opts out. Keep the precise claim that `ditto.py` itself makes no network calls; remove blanket `100% local` claims about cloud-agent mining.

- [ ] **Step 8: Align ROADMAP and release-notification truth**

Move workflow mining, drift, elicitation, hosted sync, and additional native hosts to later work. Mark the current focus as the bounded plugin loop. README states that stars bookmark the repository but do not subscribe users to releases and gives `Watch` → `Custom` → `Releases`.

- [ ] **Step 9: Validate the skill, npx companions, docs, and full suite**

Run:

```powershell
python C:\Users\ohad1\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents\skills\ditto
python -m unittest tests.test_bootstrap tests.test_plugin_manifests.DocumentationTruthTest tests.test_plugin_manifests.PluginManifestTest -v
python ditto.py --help
python ditto.py plugin --help
python -m unittest discover -s tests -v
```

Run the companion-copy proof:

```powershell
$env:DISABLE_TELEMETRY = "1"
$sourceRoot = (Get-Location).Path
$auditRoot = Join-Path $env:TEMP ("ditto-npx-companion-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $auditRoot | Out-Null
Push-Location $auditRoot
try {
    npx -y skills add "$sourceRoot" --skill ditto --agent codex --copy --yes
    $installed = Join-Path $auditRoot ".agents\skills\ditto"
    $files = @(Get-ChildItem -LiteralPath $installed -File -Recurse | ForEach-Object { $_.FullName.Substring($installed.Length).TrimStart("\") })
    $expected = @("runtime.json", "scripts\bootstrap.py", "SKILL.md")
    if (($files | Sort-Object) -join "|") -ne (($expected | Sort-Object) -join "|") { throw "unexpected npx skill contents: $($files -join ', ')" }
    $otherSkills = @(Get-ChildItem -LiteralPath (Join-Path $auditRoot ".agents\skills") -Directory | Where-Object Name -ne "ditto")
    if ($otherSkills.Count -ne 0) { throw "npx copied a native-only skill" }
} finally {
    Pop-Location
    $resolved = [IO.Path]::GetFullPath($auditRoot)
    $tempRoot = [IO.Path]::GetFullPath($env:TEMP)
    if (-not $resolved.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) { throw "unsafe npx companion cleanup path" }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
```

Expected: validation and tests pass, both help commands exit `0`, and the npx audit preserves both companion resources while copying no native-only skill.

- [ ] **Step 10: Commit**

```powershell
git add .agents/skills/ditto/SKILL.md .agents/skills/ditto/runtime.json .agents/skills/ditto/scripts/bootstrap.py tests/test_bootstrap.py README.md SECURITY.md ROADMAP.md tests/test_plugin_manifests.py
git commit -m "feat: preserve the bounded Ditto npx bootstrap"
```

### Task 16: Calibrate the bounded default against the frozen Ohad profile

**Files:**
- Modify: `ditto.py` only if dogfood selects candidate index 1 or 2
- Create: `docs/release/plugin-dogfood.md`
- Private only: `$env:DITTO_HOME\calibration\must-recover.json`

- [ ] **Step 1: Freeze the must-recover checklist before any candidate output is seen**

Use the existing installed deep Ohad profile at `$HOME\.codex\skills\ditto\SKILL.md` as the private calibration source. Before reading it, run:

```powershell
$sourceProfile = Join-Path $HOME ".codex\skills\ditto\SKILL.md"
if (-not (Test-Path -LiteralPath $sourceProfile)) { throw "private calibration profile is missing" }
Get-FileHash -Algorithm SHA256 -LiteralPath $sourceProfile
```

Do not substitute the repository's legacy mining-orchestration skill or a newly generated candidate. Read the installed source privately and write `must-recover.json` under `DITTO_HOME`, never in the repository. The root contains schema version `1`, the actual UTC freeze timestamp, the SHA-256 of the private source profile, and a `domains` object. Each of `work`, `design`, and `write` contains actual private checklist objects with a stable private ID and exact must-recover requirement. The file contains no sample text, unfinished marker, or post-result edits. Hash it and record only the hash/counts in the public dogfood summary.

- [ ] **Step 2: Run candidate 0 preflight without model calls**

Run against the real corpus:

```powershell
python ditto.py plugin preflight --candidate 0
```

Expected: approximately four selected segments, at most 100K selected source tokens, at most four worker calls plus one reducer, and no filesystem mutation beyond reading existing caches.

- [ ] **Step 3: Show the exact candidate-0 plan and obtain calibration-call approval**

Report selected tokens, cache hits, planned worker/reducer calls, and the fact that candidate 0 samples about 5% of the current 1.95M-token corpus. Do not start model work until Ohad approves this displayed development cost.

- [ ] **Step 4: Prepare and run only candidate 0**

Use `ditto:mine` with explicit candidate `0`. Store raw private reports/profile under `DITTO_HOME`; commit none of them. Compare the activated result to the frozen checklist by stable IDs and collect real receipts plus one fresh-task work, design, and write human verdict through the installed development plugin. Retain the non-private transcript hashes so Task 17 can reuse these exact probes instead of spending three duplicate host interactions.

- [ ] **Step 5: Apply the fixed ladder without goalpost changes**

If candidate 0 passes every frozen must-recover item and all three probes, keep `DEFAULT_CANDIDATE_INDEX = 0` and stop calibration.

If it fails, show candidate 1's additional plan and ask before spending it. Run candidate 1 by expanding the same immutable 25K segmentation from four to six selected segments (at most seven total calls, with earlier report caches reused) only after approval. If candidate 1 fails, repeat once by expanding to eight selected segments under the unchanged 160K-token and nine-call ceilings. Never alter the checklist between candidates.

If candidate 2 fails, stop the release. Do not weaken the checklist, silently deepen, or claim the bounded default is sufficient.

- [ ] **Step 6: Lock the smallest passing default**

If candidate 1 or 2 is the smallest pass, change only:

```python
DEFAULT_CANDIDATE_INDEX = 1  # or 2, matching the first passing candidate
```

Add a unit assertion that `candidate_config(DEFAULT_CANDIDATE_INDEX)` matches the selected public summary. Run the full suite.

- [ ] **Step 7: Write the non-private dogfood evidence summary**

`docs/release/plugin-dogfood.md` must contain the actual date, selected candidate, selected source tokens, planned/actual worker and reducer calls, separately counted host-task interactions, cache reuse, checklist hash, per-domain recovered/required counts, three human verdicts, active profile manifest hash, and known gaps. It must contain no raw quote, private rule text, full profile, placeholder, benchmark result, or subscription-percentage claim.

- [ ] **Step 8: Verify and commit**

Run:

```powershell
python -m unittest discover -s tests -v
git diff --check
```

Expected: suite `OK`; no private files appear in `git status --short`.

Commit:

```powershell
git add ditto.py tests/test_plugin_runtime.py docs/release/plugin-dogfood.md
git commit -m "test: lock the bounded Ditto starter profile"
```

If candidate 0 passed and neither runtime nor tests changed, stage only `docs/release/plugin-dogfood.md`.

### Task 16A: Make full mining the quality default and bounded mining an honest quick preview

**Decision:** Candidate 2 recovered only `5/22` frozen requirements. Full-history mining remains the quality default. Bounded mining ships only as an explicitly labeled quick preview that creates a starter profile, not the full profile. The frozen calibration identity and result remain a permanent public regression fixture; bounded mining cannot be called the default unless a future run passes all `22/22` frozen requirements.

This task supersedes every earlier bounded-default instruction in Tasks 1-16. Earlier text remains historical implementation context, not the release behavior after this checkpoint.

**Files:**
- Modify: `ditto.py`
- Modify: `README.md`
- Modify: `skills/mine/SKILL.md`
- Modify: `.agents/skills/ditto/SKILL.md`
- Modify: `tests/test_plugin_runtime.py`
- Modify: `tests/test_plugin_manifests.py`
- Create: `tests/fixtures/bounded-calibration-baseline.json`
- Modify: `docs/release/plugin-dogfood.md`

- [x] **Step 1: Add failing contract tests and the non-private calibration fixture**

The fixture records only checklist hash, required/recovered counts, the candidate-2 run ID, and a nullable `passing_bounded_run`; it contains no private requirement text or receipts. Tests require no-flag `preflight` to return `mode: full`, `profile_scope: full_profile`, and `quality_default: true`; explicit `--preview` and hidden `--candidate` plans return `mode: quick_preview`, `profile_scope: starter_profile`, `quality_default: false`, and the exact notice `Quick preview creates a starter profile from selected history, not the full profile.` Tests also fail if public README/skill/CLI language calls bounded mining a default without fixture evidence of `22/22` recovery.

- [x] **Step 2: Run focused tests and verify RED**

```powershell
python -m unittest tests.test_plugin_runtime.PreflightTest tests.test_plugin_manifests.DocumentationTruthTest -v
```

Expected: failures because no-flag preflight still selects candidate 0, `--preview` does not exist, and public surfaces still call bounded mining the default.

- [x] **Step 3: Implement the minimal mode contract**

Add `--preview` to the mutually exclusive mode group. No-flag and legacy explicit `--deep` both build the full-history plan; `--preview` uses `DEFAULT_CANDIDATE_INDEX`; hidden `--candidate` remains calibration-only and is also labeled quick preview. Both preflight builders emit the mode, scope, eligibility boolean, and an exact honest notice. `prepare` copies the selected plan mode instead of inferring it from `args.deep`.

Full-history preflight must validate report cache entries, compute `report_set_hash`, and check the reduction cache so an identical full update can still plan zero additional workers and reducers.

- [x] **Step 4: Make README and both mining skills explicit**

The normal `run ditto` flow runs the full-history read-only preflight, shows exact selected tokens/calls/cache reuse, and waits for approval before any model work. `run ditto quick preview` maps to `--preview` and must say, without euphemism, that it samples selected history and creates a starter profile rather than the full profile. Remove every claim that bounded mining is the normal/default setup.

- [x] **Step 5: Preserve the frozen result and record the approved fallback**

Keep `docs/release/plugin-dogfood.md` and the regression fixture permanent. Change only the release consequence: the failed candidate result is unchanged, full mining is the quality default, and quick preview is permitted with the mandatory limitation label.

- [x] **Step 6: Verify and checkpoint**

```powershell
python -m unittest discover -s tests -v
python C:\Users\ohad1\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py .
python C:\Users\ohad1\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents\skills\ditto
git diff --check
```

Commit only the listed Task 16A files with `feat: make full Ditto mining the quality default`, then resume Task 17. Do not rerun calibration, adaptive recall, the benchmark, or video work.

### Task 17: Prove live plugin activation, routing, updates, and safe migration

**Files:**
- Modify: `docs/release/plugin-dogfood.md` with live host evidence only
- No product-code edit unless a failing live probe first receives a regression test

- [x] **Step 1: Reinstall the development plugin with a cachebuster**

Run:

```powershell
codex plugin remove ditto@ditto --json
python C:\Users\ohad1\.codex\skills\.system\plugin-creator\scripts\update_plugin_cachebuster.py .
codex plugin add ditto@ditto --json
codex plugin list --marketplace ditto --json
```

Expected: the installed version/cache identifier changes and the plugin lists exactly `ditto:mine`, `ditto:work`, `ditto:design`, and `ditto:write`.

After capturing the proof, restore every retained manifest version to `0.0.0-dev` with `apply_patch`, rerun the validator, and confirm no cachebuster-only manifest diff remains. Task 19 is the only task that changes the committed release version.

- [x] **Step 2: Prove update and uninstall preserve private state**

Hash every file under the isolated proof `DITTO_HOME`, remove/reinstall the plugin, then hash again. The sorted `relative-path sha256` lists must match exactly. Do not run this destructive proof against an unbacked-up real home.

- [x] **Step 3: Run fresh-task positive routing probes**

First compare Task 16's host version, plugin commit, prompt text, and transcript hashes to this task. If they match exactly, reuse those three positive probes. Otherwise run only the missing or stale probes. For any probe that must run, use a separate fresh task and require it to state the loaded Ditto skill before answering:

```text
Execution probe: Use my Ditto context. I said "done" after a code edit. What must happen before you report completion?
Design probe: Use my Ditto context. Critique a generic purple-gradient SaaS hero and describe the structural redesign.
Writing probe: Use my Ditto context. Draft a short launch reply in my voice for a developer who asks why Ditto is useful.
```

Expected: execution loads `ditto:work` only; design loads core plus `ditto:design`; writing loads core plus `ditto:write`. Ohad records pass/fail for behavior, not merely skill-name output.

- [x] **Step 4: Run fresh-task negative/combined routing probes**

```text
Negative mine probe: Debug this failing unit test. Do not mine or update my history.
Combined probe: Design a launch card and write its one-line caption using my Ditto context.
```

Expected: negative mine does not load `ditto:mine`; combined loads design and write intentionally without also loading work merely because all mention the profile.

- [x] **Step 5: Prove identical update is zero-call**

Approved Task 17 evidence route after the full-default fallback:

- Run the quick-preview preflight against the unchanged real corpus and existing candidate caches. This is the live zero-call proof for quick preview.
- Run the deterministic full-history cache fixture that validates every cached report, computes the report-set hash, sees the cached reduction, and returns zero planned workers/reducers. This is fixture proof only; do not describe it as a live full-history dogfood run.
- Record plainly that full-history mining has not yet run live in the new format. Task 19 owns the real-corpus full-mine gate and cost approval.

Expected: each approved proof returns `planned_worker_calls: 0` and `planned_reducer_calls: 0`. Describe this as zero additional Ditto mining calls, not zero host-task tokens, and keep live preview evidence separate from fixture-only full-history evidence.

- [x] **Step 6: Prove one incremental session plans only uncached work**

Use an isolated copied log fixture, append one valid user session, and run preflight.

Expected: prior segment/report hashes remain unchanged, exactly the new/rebuilt affected segment is uncached, and only one reducer is planned. Do not mutate real user history for this test.

- [x] **Step 7: Prove migration in an isolated host home**

Create a disposable `HOME` with a real legacy `~/.codex/skills/you/SKILL.md`. Run `migrate-stage`, verify the new loaders against an isolated `DITTO_HOME`, then run `migrate-cutover` and start a fresh task.

Expected: exactly one personal-profile path is discoverable. Run `migrate-rollback` and verify the legacy bytes/path return and the new pointer is inactive.

If a real legacy profile is detected outside the disposable home, print its exact path and request explicit approval before any real cutover.

- [x] **Step 8: Repeat only proven native-host checks**

If Claude passed Task 1, repeat install, four-skill discovery, profile loading, reinstall-preserves-state, and fresh-task probes in Claude. If it did not pass, verify only the direct Claude adapter and keep docs explicit that native Claude was not proven.

- [x] **Step 9: Prove the selected npx bootstrap and native plugin do not double-route**

Install only the local `ditto` bootstrap into a disposable project through skills.sh, while the development native plugin remains installed. Confirm the copied tree contains `SKILL.md`, `runtime.json`, and `scripts/bootstrap.py`. Start one fresh Codex task in that disposable project with:

```powershell
$env:DISABLE_TELEMETRY = "1"
$sourceRoot = (Get-Location).Path
$auditRoot = Join-Path $env:TEMP ("ditto-routing-audit-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $auditRoot | Out-Null
Push-Location $auditRoot
try {
    npx -y skills add "$sourceRoot" --skill ditto --agent codex --copy --yes
    $installed = Join-Path $auditRoot ".agents\skills\ditto"
    foreach ($relative in @("SKILL.md", "runtime.json", "scripts\bootstrap.py")) {
        if (-not (Test-Path -LiteralPath (Join-Path $installed $relative))) { throw "missing npx companion: $relative" }
    }
    codex exec -C "$auditRoot" "A native ditto:mine plugin skill and the skills.sh ditto bootstrap are both present. For a future 'run ditto' request, state the one route that should own setup. Do not scan logs or start mining."
} finally {
    Pop-Location
    $resolved = [IO.Path]::GetFullPath($auditRoot)
    $tempRoot = [IO.Path]::GetFullPath($env:TEMP)
    if (-not $resolved.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) { throw "unsafe routing audit cleanup path" }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
```

Prompt used by the fresh task:

```text
A native ditto:mine plugin skill and the skills.sh ditto bootstrap are both present. For a future "run ditto" request, state the one route that should own setup. Do not scan logs or start mining.
```

Expected: `ditto:mine` is the sole selected route; the bootstrap's negative trigger prevents competing orchestration. Remove the disposable project after verifying its resolved path remains under the intended temporary root. This proof runs no mining workers or reducer.

- [x] **Step 10: Record evidence and commit only if the evidence document changed**

Append host versions, installed plugin identifier, pointer/profile hashes, routing outcomes, zero-call update evidence, npx companion/coexistence outcome, migration/rollback outcome, and human verdicts to `docs/release/plugin-dogfood.md`. No private profile content.

Run `git diff --check`, then:

```powershell
git add docs/release/plugin-dogfood.md
git commit -m "test: record live Ditto plugin activation proof"
```

### Task 18: Run separate spec-compliance and code-quality reviews

**Files:**
- Review: all changes since the pre-implementation checkpoint
- Modify: only files tied to verified actionable findings

- [x] **Step 1: Capture the exact review scope**

Run:

```powershell
git diff --stat v0.1.2...HEAD
git diff --name-only v0.1.2...HEAD
python -m unittest discover -s tests -v
python C:\Users\ohad1\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py .
```

Expected: tests and validator exit `0`; changed files remain inside this plan.

- [x] **Step 2: Run a read-only spec-compliance review**

Give the reviewer this exact scope:

```text
Read the approved Ditto design spec, architecture plan, Plugin-release implementation plan, and diff from v0.1.2. Review Workstreams 0-8 only. Verify every requirement is implemented and evidenced: front-loaded host viability, bounded calibration, zero-call native install, the explicitly selected npx bootstrap and pinned-runtime hashes, stable caches, exact report receipts, three routed profiles, atomic activation, exclusive migration, privacy wording, CLI compatibility, and benchmark exclusion. Do not edit files. Report findings ranked by severity with exact file/line evidence; say PASS only if no actionable gap exists.
```

- [x] **Step 3: Run a separate read-only code-quality review**

Use:

```text
Review the Ditto Plugin-release diff as a senior stdlib Python maintainer. Focus on correctness, Windows filesystem behavior, atomicity/rollback, bootstrap download boundaries and SHA-256 verification, schema validation, path traversal, corrupt cache handling, deterministic hashing, CLI compatibility, test isolation, and accidental private-data exposure. Do not edit files and do not re-review product scope. Report actionable findings with exact file/line evidence; say PASS only if none remain.
```

- [x] **Step 4: Fix every verified finding test-first**

For each finding: reproduce it with one focused failing test, run that test to prove red, apply the smallest fix, rerun focused and full tests, and commit the finding separately. Reject findings that conflict with the approved spec or lack evidence, recording the technical reason.

- [x] **Step 5: Re-run both reviews on the fixed commit**

Expected: both reviewers return PASS with no actionable finding. Reviewer reports alone do not replace tests or live host proof.

- [x] **Step 6: Run final local verification**

```powershell
python -m unittest discover -s tests -v
python C:\Users\ohad1\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py .
python C:\Users\ohad1\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents\skills\ditto
python ditto.py --help
python ditto.py plugin --help
git diff --check
git status --short
```

Expected: every command exits `0`; worktree contains no private profile, run cache, benchmark artifact, or unrelated staged file.

### Task 19: Prepare the Plugin release, then stop for ship approval

**Files:**
- Modify: `.codex-plugin/plugin.json`
- Modify: `.agents/skills/ditto/runtime.json`
- Conditional modify: `.claude-plugin/plugin.json`
- Conditional modify: `.claude-plugin/marketplace.json`
- Create: `CHANGELOG.md`
- Create: `docs/release/plugin-release-draft.md`
- Modify: `README.md` only if final install commands differ from the verified tagged flow

**Ship-approval prerequisite:** Before asking for final ship approval, show the exact real-corpus full-history preflight cost and obtain Ohad's explicit spend approval. Run one real full mine in the new format and record its validation, activation, domain status, selected tokens, worker/reducer passes, cache reuse, and active manifest hash. If Ohad declines that spend, do not imply the full path was live-proven: `CHANGELOG.md`, `README.md`, and `docs/release/plugin-release-draft.md` must state plainly that full-history mining is the quality default but was fixture-verified only before release. No real-corpus full mine may start from this standing plan approval alone.

- [ ] **Step 1: Recheck tag state before choosing the release version**

Run:

```powershell
git tag --sort=-version:refname
```

Expected: latest `v0.1.2`, so this plan's Plugin release is `v0.2.0`. If a newer tag exists at execution time, stop and revise Task 19 before editing manifests; the remaining hardcoded `0.2.0` commands must not run against changed tag state.

- [ ] **Step 2: Set the release version and pin the npx runtime bytes**

Change Codex `version` from `0.0.0-dev` to `0.2.0`. If Claude passed Workstream 0, change both Claude version fields to `0.2.0`. If Claude did not pass, no Claude manifest may be present or claimed.

Compute the exact release-input hashes:

```powershell
$dittoHash = (Get-FileHash -Algorithm SHA256 -LiteralPath .\ditto.py).Hash.ToLowerInvariant()
$promptHash = (Get-FileHash -Algorithm SHA256 -LiteralPath .\MINING_PROMPT.md).Hash.ToLowerInvariant()
[pscustomobject]@{ditto_py=$dittoHash;mining_prompt=$promptHash} | ConvertTo-Json
```

Use `apply_patch` to set `.agents/skills/ditto/runtime.json` to `version: 0.2.0`, `ref: v0.2.0`, and the two exact lowercase hashes printed above. Do not use `main`, a branch name, a shortened hash, or bytes from a different commit. Run `tests.test_bootstrap` after the edit.

- [ ] **Step 3: Write the Plugin release changelog entry from actual proof**

Create `CHANGELOG.md` with title `Changelog` and an `0.2.0` entry dated with the actual UTC ship date. The entry contains populated `Changed`, `Why it matters`, `Upgrade`, `Verified`, and `Known limits` sections in that order. Populate every section with shipped behavior and exact verified commands/hashes from Tasks 16-18 plus the Task 19 full-mine gate, including the selected npx bootstrap versus full native-plugin capability boundary. If the real full mine ran, record its exact non-private proof. If Ohad declined it, state that the full path is fixture-verified only. `Known limits` states that the benchmark/leaderboard/videos are a separate later release. Include no score, winner, placeholder, unverified host, or subscription-percentage claim.

- [ ] **Step 4: Write the local GitHub Release draft**

`docs/release/plugin-release-draft.md` mirrors the changelog facts in user-facing order: one-sentence outcome, the cross-agent `npx skills add ohad6k/ditto@ditto` command, native-plugin install/upgrade commands, bounded-cost behavior, three native domain skills, migration note, verification proof, known limits, and the `Watch` → `Custom` → `Releases` notification path. It links to the exact docs and contains no benchmark teaser with an invented date.

- [ ] **Step 5: Verify release-candidate files and commit them**

Run:

```powershell
python -m unittest discover -s tests -v
python C:\Users\ohad1\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py .
python C:\Users\ohad1\.codex\skills\.system\skill-creator\scripts\quick_validate.py .agents\skills\ditto
python -m json.tool .codex-plugin\plugin.json > $null
python -m json.tool .agents\skills\ditto\runtime.json > $null
git diff --check
git status --short
```

Expected: all commands pass; only release-candidate files are modified.

Commit:

```powershell
git add .codex-plugin/plugin.json .agents/skills/ditto/runtime.json CHANGELOG.md docs/release/plugin-release-draft.md README.md
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json  # only when Claude passed
git commit -m "chore: prepare Ditto v0.2.0 release"
```

- [ ] **Step 6: Run or explicitly decline the real-corpus full-mine gate**

Run no model work until Ohad approves the exact full-history preflight cost shown in this task. If approved, complete and validate the full mine before final local verification and ship approval. If declined, apply the fixture-only disclosure to every release document named in the prerequisite, rerun documentation truth tests, and keep the live-proof table explicit.

- [ ] **Step 7: Use `superpowers:finishing-a-development-branch` and stop before external writes**

Present the verified branch/commit, test count, validator output, live host proof, changelog, release draft, planned tag `v0.2.0`, and exact push/release commands. Ask Ohad for final ship approval. Do not merge, tag, push, create a GitHub Release, publish marketplace content, or post videos before that approval.

- [ ] **Step 8: After explicit ship approval, integrate and publish the exact verified commit**

Only after approval and after the verified commit is on `main`:

```powershell
git tag -a v0.2.0 -m "Ditto v0.2.0"
git push origin main
git push origin v0.2.0
gh release create v0.2.0 --title "Ditto v0.2.0" --notes-file docs/release/plugin-release-draft.md
```

Then install from the exact tag in a clean environment:

```powershell
codex plugin marketplace add ohad6k/ditto --ref v0.2.0 --json
codex plugin add ditto@ditto --json
codex plugin list --marketplace ditto --json
```

Expected: the installed plugin resolves to `0.2.0`, exposes the four proven skills, and a fresh task passes the work activation probe. If any command fails, do not call the release shipped; fix through a new commit/tag rather than moving `v0.2.0`.

Also prove the public skills.sh path and pinned bootstrap in a disposable project:

```powershell
$releaseMetadata = Get-Content -Raw -Encoding utf8 .agents\skills\ditto\runtime.json | ConvertFrom-Json
$dittoHash = $releaseMetadata.files.'ditto.py'.sha256
$promptHash = $releaseMetadata.files.'MINING_PROMPT.md'.sha256
$auditRoot = Join-Path $env:TEMP ("ditto-v020-npx-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $auditRoot | Out-Null
Push-Location $auditRoot
try {
    npx -y skills add ohad6k/ditto@ditto --agent codex --copy --yes
    $skillRoot = Join-Path $auditRoot ".agents\skills\ditto"
    $env:DITTO_HOME = Join-Path $auditRoot "private"
    python (Join-Path $skillRoot "scripts\bootstrap.py") --ditto-home $env:DITTO_HOME
    $runtime = Get-Content -Raw -Encoding utf8 (Join-Path $env:DITTO_HOME "runtime\current.json") | ConvertFrom-Json
    if ($runtime.version -ne "0.2.0") { throw "npx bootstrap resolved the wrong runtime version" }
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $runtime.runtime_dir "ditto.py")).Hash.ToLowerInvariant() -ne $dittoHash) { throw "published ditto.py hash mismatch" }
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $runtime.runtime_dir "MINING_PROMPT.md")).Hash.ToLowerInvariant() -ne $promptHash) { throw "published MINING_PROMPT.md hash mismatch" }
} finally {
    Pop-Location
    $resolved = [IO.Path]::GetFullPath($auditRoot)
    $tempRoot = [IO.Path]::GetFullPath($env:TEMP)
    if (-not $resolved.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) { throw "unsafe release audit cleanup path" }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
```

Expected: skills.sh selects only `ditto`, copies its companions, and the bootstrap downloads byte-for-byte hashes from tag `v0.2.0`. This network proof reads no user logs and runs no mining model.

---

## Completion boundary

The Plugin release is complete only when Task 19's post-approval tagged native-plugin install and public `npx skills add ohad6k/ditto@ditto` hash-verification proof both succeed from the published artifact. Benchmark preparation, model runs, leaderboard, and proof-video production remain unstarted and receive a separate implementation plan after the Plugin release tag is frozen.
