---
name: ditto
description: Mine your own AI coding-session history into a "you.md" — a model of how you decide, talk, work, and get stuck — that your agents read before every task so they act like you instead of a stranger. Use when someone wants to clone their working style, build a personal agent profile, generate a you.md / AGENTS.md from their real history, or "make my agent act like me." Runs 100% local; redacts secrets first.
---

# ditto

Turn the user's own AI session logs into a `you.md` they can drop into `.claude/skills/`, `.codex/skills/`, `AGENTS.md`, or cursor rules. Runs locally, redacts secrets by default. This skill orchestrates the whole flow so the user never touches python or a manual step.

## The one rule that makes this ditto (read first)

The profile MUST be mined from the user's **raw session logs** (the `.jsonl` history). **NEVER** build it from their `AGENTS.md`, `CLAUDE.md`, cursor rules, memory files, or a description they type — that just reflects their existing rules back at them, which is the exact opposite of the point and something `/init` already does. The whole value of ditto is pulling out what they *never wrote down*, straight from how they actually worked.

So: **run `ditto.py` on the real logs first.** If it finds no logs, **STOP and ask where the logs are** (`--path <folder>`). Do not fall back to summarizing instructions. **No mined logs → no profile.** If you ever produce a profile without having run the extractor over real session `.jsonl`, you have failed the task — say so instead of shipping a fake.

## Steps

1. **Extract (deterministic, safe).** Run the extractor. It reads the user's session logs, keeps only their own words, and redacts API keys / tokens / emails / phone numbers BEFORE anything is written. Never skip redaction.

   First locate `ditto.py`. Check in this order:
   1. `<skill-dir>/../ditto.py` (skill running from inside the cloned repo)
   2. `./ditto.py` in the current working directory
   3. Not found → download it: `curl -O https://raw.githubusercontent.com/ohad6k/ditto/main/ditto.py` (or clone the repo). It is a single stdlib-only file with zero network calls at runtime.

   Then run:
   ```
   python ditto.py --chunks 20 --out ditto-out
   ```
   If no logs are found, **STOP and ask** where their logs live (pass `--path <folder>`). Do not proceed without real logs, and never build a profile from their instructions instead. The counts it prints (sessions / messages / tokens / redactions) are your proof it actually read the logs — report them; if sessions is 0, you have nothing to mine.

2. **Mine (fan-out).** Spawn one sub-agent per file in `ditto-out/chunks/`, each running the per-chunk prompt from `MINING_PROMPT.md` on its chunk (if not next to `ditto.py`, fetch it from `https://raw.githubusercontent.com/ohad6k/ditto/main/MINING_PROMPT.md`). Run them in parallel. Each returns a structured profile of one slice.
   - If the environment can't fan out sub-agents, process chunks sequentially instead — same prompt, one at a time.

3. **Reduce.** Merge all the chunk reports with the reducer prompt in `MINING_PROMPT.md`. Rank every trait by how many chunks independently surfaced it — high-frequency traits are the real person, one-offs are noise. Output a lean `you.md` (deep quotes go in a separate `you-appendix.md`, not in `you.md`).

4. **Install + prove.** The `you.md` already starts with `name:` / `description:` frontmatter, so it's skill-ready. Place it where the user's agent actually reads it, per their tool, then verify it registered:
   - **Claude Code** → save as `.claude/skills/you/SKILL.md`. Confirm it shows in the skill list (invoke `/you`). For it to load in every project, put it in the user-level `~/.claude/skills/you/SKILL.md`.
   - **Codex native skill** - save as `~/.codex/skills/you/SKILL.md`. Confirm it appears in Codex's available skills, or open a new Codex session and verify `you` is loaded before relying on it.
   - **Codex repo context** - append the body (everything below the frontmatter) to `AGENTS.md` at the repo root. Codex reads it automatically, no frontmatter needed. Use this when the profile should apply only to one repo.
   - **Cursor** → save as `.cursor/rules/you.mdc`, with frontmatter `description: act like me` and `alwaysApply: true`, then the body.
   - **Gemini CLI** → append the body to `GEMINI.md`.
   Then prove it: run one real task once without the file and once with it loaded, so the user sees the agent act more like them. Do not claim it's installed until you've confirmed the agent actually picks it up.

## Rules
- **Local only.** No network calls. The user's logs never leave their machine. Say so.
- **Redaction is not optional.** If the user asks for `--no-redact`, warn them their secrets will appear in the corpus and any shared output.
- **Don't invent traits.** Every line in `you.md` must trace to something they actually wrote *in the logs*. Cut generic filler.
- **Mine the logs or stop.** The profile comes ONLY from the raw session `.jsonl`. Never synthesize it from `AGENTS.md` / `CLAUDE.md` / memory / a description — that is not ditto, it is their rules file reflected back.
- Keep `you.md` lean — it loads on every task.
