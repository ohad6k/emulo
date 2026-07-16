# Roadmap

Ditto's current focus is the bounded plugin loop: deterministic extraction, stable caches, exact evidence receipts, private versioned profiles, safe migration, and separate work/design/write routing. User feedback and what it changed lives in `docs/FEEDBACK.md`.

## Current release

- Fourth mined domain `video` (`ditto:video`): mining loads motion, caption, voiceover, and edit taste before video work, alongside work, design, and write
- Voice registers in the writing profile: mined `write` evidence carries a `casual`, `professional`, or `shared` register, `you-writer.md` groups rules by register, and `ditto:write` infers the register from task context instead of asking (from user feedback, `docs/FEEDBACK.md`)
- Cross-agent selected bootstrap through `npx skills add ohad6k/ditto@ditto`
- Native Codex plugin with `ditto:mine`, `ditto:work`, `ditto:design`, and `ditto:write`
- Bounded starter candidates capped at 160K new source tokens and nine planned mining passes
- Explicit deep mode, never an automatic fallback
- Content-addressed segments and validated report/reduction reuse
- Atomic profile activation plus exclusive legacy cutover and rollback

## Later work

### Benchmark release

Run the approved cold-versus-Ditto model matrix, publish the reproducible leaderboard, and produce proof clips as a separate release. No benchmark score belongs in the plugin release.

### More session sources

Adapters for more local coding-agent logs (issue #3). The Hermes Agent spec is complete in-thread: read its SQLite `state.db` read-only (WAL-aware), resolve `HERMES_HOME` overrides and per-profile databases, extract user messages only. Cursor and Windsurf storage docs are in progress. Adapter code lands after the ditto.py rewrite.

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

Use the evidence-backed profile to challenge repeated failure modes rather than merely imitate the user.

### Graph output

Atoms-with-links from issue #7: the reducer emits linkable trait atoms with stable ids and receipt edges, stored local-first (SQLite, no server), with `you.md` as the flattened view. Optional local embeddings for per-task retrieval stay a v2 direction.
