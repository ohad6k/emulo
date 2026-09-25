# Roadmap

Emulo is in maintenance mode. See [MAINTENANCE.md](MAINTENANCE.md) for what gets fixed. Nothing below is planned: the ideas under "Later work" are recorded for reference and are out of scope by default.

What shipped is the bounded plugin loop: deterministic extraction, stable caches, exact evidence receipts, private versioned profiles, safe migration, and separate work/design/write/video routing.

## Current release

- Fourth mined domain `video` (`emulo:video`): mining loads motion, caption, voiceover, and edit taste before video work, alongside work, design, and write
- Voice registers in the writing profile: mined `write` evidence carries a `casual`, `professional`, or `shared` register, `you-writer.md` groups rules by register, and `emulo:write` infers the register from task context instead of asking (from user feedback)
- Cross-agent selected bootstrap through `npx skills add ohad6k/emulo@emulo`
- Native Codex plugin with `emulo:mine`, `emulo:work`, `emulo:design`, `emulo:write`, and `emulo:video`
- Full history is the quality default; the quick preview is capped at 160K new source tokens and nine planned mining passes
- Explicit deep mode, never an automatic fallback
- Content-addressed segments and validated report/reduction reuse
- Atomic profile activation plus exclusive legacy cutover and rollback

## Later work (not planned)

### Benchmark release

Published so far: a pre-registered placebo test (https://emulo.vercel.app/placebo) and a September rerun on two models (https://emulo.vercel.app/fable). Neither measures whether the work got better, and no test of that has been run yet. Any benchmark ships as its own release; no benchmark score belongs in the plugin release.

### More session sources

Adapters for more local coding-agent logs (issue #3). The Hermes Agent spec is complete in-thread: read its SQLite `state.db` read-only (WAL-aware), resolve `HERMES_HOME` overrides and per-profile databases, extract user messages only. Cursor and Windsurf storage is undocumented. No adapter is planned. Adapters already offered in issue #3 (Hermes, Cursor, Windsurf) will still be reviewed if they come with the tests and real-run evidence described in docs/SOURCES.md; new sources beyond those are out of scope. See MAINTENANCE.md.

### Workflow mining

Mine repeated debug, UI-polish, and release sequences into separately reviewable personal skills without bloating the always-loaded core profile. Feedback confirms the appetite: users already hand-mine their session logs for skills and permissions.

### Profile drift

Compare a bounded update against the active profile and show which laws strengthened, weakened, or disappeared.

### Optional elicitation

Ask only the questions session evidence cannot answer, and label those answers separately from mined evidence.

### More native hosts

Add a native host only after its plugin lifecycle, namespaced discovery, private-state boundary, reinstall behavior, and fresh-task loading are proven.

### Hosted sync

Any future sync must be opt-in, encrypted, explicit about provider boundaries, and separate from the local-first default.

### Counterweight profiles

Use the evidence-backed profile to challenge repeated failure modes rather than only restating the user's habits.

### Graph output

Atoms-with-links from issue #7: the reducer emits linkable trait atoms with stable ids and receipt edges, stored local-first (SQLite, no server), with `you.md` as the flattened view. Optional local embeddings for per-task retrieval stay a v2 direction.
