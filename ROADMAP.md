# Roadmap

Ditto's current focus is the bounded plugin loop: deterministic extraction, stable caches, exact evidence receipts, private versioned profiles, safe migration, and separate work/design/write routing.

## Current release

- Cross-agent selected bootstrap through `npx skills add ohad6k/ditto@ditto`
- Native Codex plugin with `ditto:mine`, `ditto:work`, `ditto:design`, and `ditto:write`
- Bounded starter candidates capped at 160K new source tokens and nine planned mining passes
- Explicit deep mode, never an automatic fallback
- Content-addressed segments and validated report/reduction reuse
- Atomic profile activation plus exclusive legacy cutover and rollback

## Later work

### Benchmark release

Run the approved cold-versus-Ditto model matrix, publish the reproducible leaderboard, and produce proof clips as a separate release. No benchmark score belongs in the plugin release.

### Workflow mining

Mine repeated debug, UI-polish, and release sequences into separately reviewable personal skills without bloating the always-loaded core profile.

### Profile drift

Compare a bounded update against the active profile and show which laws strengthened, weakened, or disappeared.

### Optional elicitation

Ask only the questions session evidence cannot answer, and label those answers separately from mined evidence.

### More native hosts

Add a native host only after its plugin lifecycle, namespaced discovery, private-state boundary, reinstall behavior, and fresh-task loading are proven.

### Hosted sync

Any future sync must be opt-in, encrypted, explicit about provider boundaries, and separate from the local-first default.

### Counterweight profiles

Use the evidence-backed profile to challenge repeated failure modes rather than merely imitate the user.
