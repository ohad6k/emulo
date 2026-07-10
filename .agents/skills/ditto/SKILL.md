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
