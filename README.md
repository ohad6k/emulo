<p align="center"><img src="assets/ditto.png" width="360" alt="ditto"></p>

<h1 align="center">ditto</h1>

<p align="center"><b>your AI agents act like they just met you. ditto fixes that.</b></p>

<p align="center">
<img src="https://img.shields.io/github/stars/ohad6k/ditto?style=for-the-badge&color=3a3a3a&labelColor=141414&logo=github&logoColor=white" alt="stars">
<img src="https://img.shields.io/badge/license-MIT-3a3a3a?style=for-the-badge&labelColor=141414" alt="MIT">
<img src="https://img.shields.io/badge/python-zero_deps-3a3a3a?style=for-the-badge&labelColor=141414&logo=python&logoColor=white" alt="python, zero deps">
<img src="https://img.shields.io/badge/works_with-claude_·_cursor_·_codex_·_gemini-141414?style=for-the-badge&labelColor=3a3a3a" alt="works with claude, cursor, codex, gemini">
</p>

<p align="center">
you have months of chat logs with claude / codex / cursor sitting on your disk.<br>
it's the most honest record of how you actually think, and you're deleting it.<br>
ditto mines it into a <code>you.md</code> your agents read before every task.
</p>

---

## the difference

ask an agent a real judgment call. one hedges through a wall of considerations. one answers like you.

**prompt:** *"i'm thinking of building a dashboard to track my users. good idea?"*

<table>
<tr><th width="50%">cold agent</th><th width="50%">agent + ditto</th></tr>
<tr valign="top"><td>

> it can be a good idea, but it depends. before building anything i'd pin down:
>
> - what decision does this drive?
> - how many users? under a few hundred, a weekly SQL query beats a custom UI.
> - buy vs build: PostHog or Plausible give you this today.
>
> …good idea *if* you can name the decision it drives and you've outgrown a manual query.

</td><td>

> no. build the thing that gets you users, not the thing that watches them.
>
> a dashboard for a handful of users is procrastination dressed up as work.
>
> if you need the numbers, wire posthog in 20 min and move on. then go ship something that pulls people in.

</td></tr>
</table>

both landed in a similar place. the cold one hedged through a wall to get there. ditto just told you, the way you would: no, go do the real thing.

## what it finds

the kind of profile ditto builds, ranked by how many of the 20 agents independently pulled each trait. what 15+ of them agree on is the real you. your agent reads this before every task.

> **done means it runs live.** never trust "done" off a code edit. show it working first.
>
> **fix the one thing.** rewriting or "cleaning up" code that isn't the problem gets rejected every time.
>
> **builds faster than they understand what they built** — then asks the agent to explain their own system back.
>
> **voice:** lowercase, short, "you get me", no walls of text, no hype.
>
> **gets frustrated by repeating the same ask** until it lands, not by escalating.

nobody wrote those rules down. 20 agents pulled them out of one person's own history and agreed on them.

> this is an example. yours is mined from your logs and will read nothing like it.

---

## what it does

1. reads your local session logs and keeps **only the words you typed** (strips all the tool output, file dumps, and pasted errors).
2. **redacts secrets + personal info** by default, before anything is written or seen by an agent.
3. splits it into chunks and hands you a prompt to fan a coding agent across them, then merge into one `you.md`.

that `you.md` is a skill/context file. drop it in `.claude/skills/`, your `AGENTS.md`, or cursor rules, and every agent starts already knowing how you work.

## quickstart

```bash
git clone https://github.com/ohad6k/ditto
cd ditto
python ditto.py            # auto-detects Codex + Claude logs. no deps, stdlib only.
```

you get:

```
sessions: 1,656
your messages: 7,678
tokens (approx): 2,950,000
secrets/PII redacted: 41
wrote: ditto-out/you-corpus.txt  +  20 chunks in ditto-out/chunks/
```

then open your coding agent (Claude Code / Codex / Cursor), paste [`MINING_PROMPT.md`](MINING_PROMPT.md), point it at `ditto-out/chunks/`, and let it build your `you.md`. example output: [`examples/you.md`](examples/you.md).

## install your you.md (any agent)

your `you.md` is just a context file. drop it where your agent already looks and it reads it before every task:

| tool | where it goes |
|---|---|
| claude code | `.claude/skills/you/SKILL.md` (or append to `CLAUDE.md`) |
| cursor | `.cursor/rules/you.mdc` |
| codex | `AGENTS.md` |
| gemini cli | `GEMINI.md` |
| windsurf / other | its rules or context file |

that's it. no plugin, no config.

**using a coding agent?** point it at this repo and say *"run ditto and install my you.md"* — the skill in [`skill/`](skill/SKILL.md) walks it through the whole flow (extract, mine, write, place the file) on its own. works in claude code, cursor, codex, and gemini.

## privacy (read this)

- **100% local.** ditto makes zero network calls. your logs never leave your machine. it's plain python, read the file.
- **redaction is on by default.** API keys, tokens, JWTs, emails, phone numbers, IPs get stripped before your text hits disk or an agent. (`--no-redact` exists; don't use it.)
- the mining step runs in *your* coding agent, on *your* machine. nothing gets uploaded unless you choose to.

## how it works

your logs are ~95% noise (tool output, file contents, diffs). the signal is the small slice of words you actually typed. ditto isolates that, then uses an agent fan-out so no single context has to hold all of it: each agent reads a chunk and pulls how you decide, what you reject, how you talk, where you get stuck. traits that show up across many chunks are the real you. one-offs are noise. that ranking is the whole trick.

## limits (being honest)

- it models how you *work and talk*, not your knowledge. it won't make an agent smarter, it makes it act more like you.
- garbage in, garbage out: if your logs are 3 sessions long, the profile is thin. it shines around months of history.
- it reads Codex (`~/.codex/sessions`) and Claude Code (`~/.claude/projects`) jsonl out of the box. other tools: point `--path` at a folder of jsonl.

## license

MIT. it's yours. if you build something on it, i'd love to see it.

<p align="center"><i>made by <a href="https://github.com/ohad6k">@ohad6k</a> while building in public.</i></p>
