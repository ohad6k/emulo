---
name: ditto
description: Use when the user explicitly asks to run, set up, update, re-mine, or deepen Ditto from real local AI coding-session history and native ditto:mine is not available. This is the cross-agent skills.sh bootstrap, not the native namespaced plugin.
---

# Ditto bootstrap

Mine only real user-authored `.jsonl` sessions. Never synthesize a profile from rules files, memory, or a typed self-description.

1. Resolve the runtime. Let `SKILL_DIR` be the directory containing this file. In a repository checkout, use `SKILL_DIR/../../../ditto.py` and `SKILL_DIR/../../../MINING_PROMPT.md`. Otherwise run `python "$SKILL_DIR/scripts/bootstrap.py"` and read its JSON paths. The bootstrap accepts only an exact release tag and verified SHA-256 values; never fetch executable code from mutable `main`.
2. The full-history quality default reads all eligible history. Run read-only `python "$DITTO_PY" plugin preflight`, show valid sessions, post-dedupe source tokens, selected source tokens, cache hits, `planned_worker_calls`, and `planned_reducer_calls`, then wait for explicit cost approval before model work.
3. Only when the user explicitly asks for a quick preview, use `--preview` for both preflight and prepare. Say this exactly before approval: `Quick preview creates a starter profile from selected history, not the full profile.` Never call preview the default, the full profile, or equivalent in quality to full-history mining.
4. Retain the displayed `approval_hash`. Run `python "$DITTO_PY" plugin prepare --approved-plan-hash HASH` with the exact approved mode. If the hash changed, show the new plan and obtain approval again. Retain `run_id`, assigned segment/report paths, and `pack_path` from the run JSON.
5. For each uncached selected segment, run one fast worker over that segment and the per-segment contract in the resolved `MINING_PROMPT.md`. Cache every JSON report with `plugin cache-report`; stop on rejection.
6. Run one strongest-available reducer over only the validated reports and the reducer contract. Write the complete pack to `pack_path`, then activate it with `plugin activate`.
7. Resolve the active core profile with `plugin profile-path --domain work`. If the current host already has the native Ditto plugin, do not create a competing direct profile. Otherwise install the core profile through the existing exact adapter for the current host and verify it in a fresh task.
8. Report the active version, core install path, active/inactive domains, selected source tokens, actual worker/reducer passes, cache reuse, card path, and any exact targeted-deepen instruction.

The npx bootstrap installs the approved core profile across supported agents. Automatic `ditto:work`, `ditto:design`, and `ditto:write` routing belongs to the separately installed native plugin. Asking an agent to orchestrate setup still consumes that host interaction even when Ditto plans zero mining passes.
