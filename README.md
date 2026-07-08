<p align="center"><img src="assets/ditto.png" width="360" alt="ditto"></p>

<h1 align="center">ditto</h1>

<p align="center"><b>your AI agents act like they just met you. ditto fixes that.</b></p>

<p align="center">
<img src="https://img.shields.io/github/stars/ohad6k/ditto?style=for-the-badge&color=3a3a3a&labelColor=141414&logo=github&logoColor=white" alt="stars">
<a href="https://discord.gg/VNnMq2U5r"><img src="https://img.shields.io/badge/discord-join-3a3a3a?style=for-the-badge&labelColor=141414&logo=discord&logoColor=white" alt="discord"></a>
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

## a real run

i asked an agent to help me launch this repo. one line: **"help me post ditto on reddit."** same model, once cold, once with my ditto profile loaded.

<table><tr><td>

**🡒 cold agent**

**Title:** Introducing Ditto: Turn Your AI Coding History Into a Personalized Assistant Profile

Are you tired of re-explaining yourself to your AI every session? 🤖 Meet **Ditto**, the open-source tool that transforms your coding history into a personalized profile your agents can read!

🔒 100% local & private  ⚡ Works with Claude, Cursor, Codex & more  🚀 Set up in minutes

Would love your feedback, check it out and drop a ⭐!

</td></tr></table>

<table><tr><td>

**🡒 agent + ditto**

r/ClaudeCode is where this lands, that crowd basically lives in their session logs. i'd run with this:

**title:** I had 20 AI agents read 8 months of my claude sessions and build a model of how I think. it was unsettling how accurate it was

**body:** i work with claude and codex every day. 8 months, solo. every session gets logged and i never looked back at them.

last night it hit me those logs are the most honest record of how i actually work that exists anywhere. i don't perform in them, i just work. so i mined them.

pulled every message i ever typed, ~1,656 sessions, about 3M tokens of just me. split it into 20 chunks, sent 20 agents at it in parallel, each pulling how i decide, what i reject, how i talk, where i get stuck. merged them into one profile ranked by how many agents independently found each trait. what 15+ of them caught is the real me.

turned the top of it into a skill claude reads before every task. now it starts already knowing how i work instead of me re-explaining myself every session.

you have this same goldmine sitting on your disk right now and you're probably deleting it.

</td></tr></table>

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

## community

building this in the open. join the discord to share your `you.md`, compare what the mining pulled out of you, and tell me what the prompt missed: **[discord.gg/VNnMq2U5r](https://discord.gg/VNnMq2U5r)**

## license

MIT. it's yours. if you build something on it, i'd love to see it.

<p align="center"><i>made by <a href="https://github.com/ohad6k">@ohad6k</a> while building in public.</i></p>
