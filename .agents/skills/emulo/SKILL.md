---
name: emulo
description: Use when the user explicitly asks to run, set up, update, re-mine, or deepen Emulo from real local AI coding-session history and native emulo:mine is not available. This is the cross-agent skills.sh bootstrap, not the native namespaced plugin.
---

# Emulo bootstrap

Mine only real user-authored `.jsonl` sessions. Never synthesize a profile from rules files, memory, or a typed self-description.

1. Resolve the runtime. Let `SKILL_DIR` be the directory containing this file. In a repository checkout, use `SKILL_DIR/../../../emulo.py` and `SKILL_DIR/../../../MINING_PROMPT.md`. Otherwise run `python "$SKILL_DIR/scripts/bootstrap.py"` and read its JSON paths. The bootstrap accepts only an exact release tag and verified SHA-256 values; never fetch executable code from mutable `main`.
2. The full-history quality default reads all eligible history. Run read-only `python "$EMULO_PY" plugin preflight`, show valid sessions, post-dedupe source tokens, selected source tokens, cache hits, `planned_worker_calls`, and `planned_reducer_calls`, then wait for explicit cost approval before model work.
3. Only when the user explicitly asks for a quick preview, use `--preview` for both preflight and prepare. Say this exactly before approval: `Quick preview creates a starter profile from selected history, not the full profile.` Never call preview the default, the full profile, or equivalent in quality to full-history mining.
4. Retain the displayed `approval_hash`. Run `python "$EMULO_PY" plugin prepare --approved-plan-hash HASH` with the exact approved mode. If the hash changed, show the new plan and obtain approval again. Retain `run_id`, assigned segment/report paths, and `pack_path` from the run JSON.
5. For each uncached selected segment, run one fast worker over that segment and the per-segment contract in the resolved `MINING_PROMPT.md`. Cache every JSON report with `plugin cache-report`; stop on rejection.
6. Run one strongest-available reducer over only the validated reports and the reducer contract. Write the complete pack to `pack_path`, then activate it with `plugin activate`.
7. Resolve the active core profile with `plugin profile-path --domain work`. If the current host already has the native Emulo plugin, do not create a competing direct profile. Otherwise install the core profile through the existing exact adapter for the current host and verify it in a fresh task.
8. Report the active version, core install path, active/inactive domains, selected source tokens, actual worker/reducer passes, cache reuse, card path, and any exact targeted-deepen instruction. Then tell the user how the profile reaches the model on this host, because installing is not loading: in Claude Code the `you` skill is not reliably opened on its own, so they type `/you` (or `/you <task>`) to load it; in Codex the skill is opened only when a request matches its description, and `emulo --install <core profile path> --target agents --repo .` in a project adds it to that project's `AGENTS.md`, the route verified end to end in Codex in one test. Never run that for them without naming the folder and getting a yes, and tell them it writes the whole profile, quotes from their sessions included, into a file that is usually committed and shared, so it should stay out of version control.

9. Offer the native plugin once, after the report. It adds the namespaced `emulo:mine`, `emulo:work`, `emulo:design`, `emulo:write`, and `emulo:video` skills on top of the core profile just installed. Ask first, accept a no, and never install it without an explicit yes. Skip the offer entirely when the host already has the plugin. On approval in Codex, run `codex plugin marketplace add ohad6k/emulo --ref TAG --json` and then `codex plugin add emulo@emulo --json`, where `TAG` is the exact release tag matching the installed version, never `main`. Report what got installed. In Claude Code the `/plugin` commands are typed by the user and an agent cannot run them, so print exactly these two lines for the user to paste, in this order, and say the five skills are registered once the second one finishes:

```text
/plugin marketplace add ohad6k/emulo
/plugin install emulo@emulo
```

The npx bootstrap installs the approved core profile across supported agents. The `emulo:work`, `emulo:design`, `emulo:write`, and `emulo:video` skills belong to the separately installed native plugin, which step 9 offers once the profile exists; the host decides when to open them. Asking an agent to orchestrate setup still consumes that host interaction even when Emulo plans zero mining passes.
