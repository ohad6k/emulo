<p align="center"><img src="assets/ditto.png" width="360" alt="ditto"></p>

<h1 align="center">Ditto</h1>

<p align="center"><b>Your AI agents act like they just met you. Ditto fixes that.</b></p>

<p align="center">
<img src="https://img.shields.io/github/stars/ohad6k/ditto?style=for-the-badge&color=3a3a3a&labelColor=141414&logo=github&logoColor=white" alt="stars">
<a href="https://github.com/ohad6k/ditto/actions/workflows/tests.yml"><img src="https://img.shields.io/github/actions/workflow/status/ohad6k/ditto/tests.yml?branch=main&style=for-the-badge&label=tests&labelColor=141414&color=3a3a3a" alt="tests"></a>
<a href="https://discord.gg/VNnMq2U5r"><img src="https://img.shields.io/badge/discord-join-3a3a3a?style=for-the-badge&labelColor=141414&logo=discord&logoColor=white" alt="discord"></a>
<img src="https://img.shields.io/badge/license-MIT-3a3a3a?style=for-the-badge&labelColor=141414" alt="MIT">
<img src="https://img.shields.io/badge/python-zero_deps-3a3a3a?style=for-the-badge&labelColor=141414&logo=python&logoColor=white" alt="python, zero deps">
<img src="https://img.shields.io/badge/works_with-claude_·_cursor_·_codex_·_gemini-141414?style=for-the-badge&labelColor=3a3a3a" alt="works with claude, cursor, codex, gemini">
</p>

<p align="center">
You have months of chat logs with Claude / Codex / Cursor sitting on your disk.<br>
It is the most honest record of how you actually think, and you are deleting it.<br>
Ditto mines it into a <code>you.md</code> your agents read before every task.
</p>

---

## Not Memory

Memory is what you explicitly told the model.

Ditto mines what your work already proved about you: what you reject, what "done" means, when you ask for proof, how you talk when you're actually working, and the agent behaviors that make you stop the task.

That's why it reads raw session logs, not your `CLAUDE.md` or rules file.

<p align="center"><img src="assets/card.png" width="460" alt="a ditto profile card: archetype, laws with consensus counts, session stats, and the one uncomfortable truth"></p>

## A Real Run

I asked an agent to help me launch this repo. One line: **"help me post ditto on reddit."** Same model, once cold, once with my Ditto profile loaded.

<table><tr><td>

**🡒 agent**

Here's how I'd play it.

**Subreddits:** r/ClaudeAI and r/ChatGPTCoding are your core audience — they've got the .jsonl logs on disk right now. r/LocalLLaMA fits the local angle but is allergic to hype. r/cursor, r/SideProject, r/opensource for reach. Skip r/programming on launch day. Don't blast all at once — post to one, tune the title, repost over a few days.

**Titles (pick per sub):**
- I built a local tool that reads your AI coding logs and writes a "you.md" your agents read before every task
- ditto: mine your own Claude Code / Cursor history into a profile so your agent codes like you (local, open source)

**Body:**
> Every fresh agent session starts from zero — it doesn't know how you work, so you re-explain yourself every time. All of that is already in your session logs. So I built **ditto**: it reads your history, mines how you decide and talk, and writes a `you.md` your agents read before every task.
> - runs locally, your logs never leave your machine
> - redacts secrets before processing
> - open source: [link]

Also: open with the pain not the product, reply fast in the first hour, add a demo gif, and flair it correctly. Want me to write tuned variants for each subreddit?

</td></tr></table>

<table><tr><td>

**🡒 agent + ditto**

the insight first: the mining number is your whole post. "i read 1,656 of my own sessions" is a confession, not a pitch, and nobody scrolls past a confession. lead with the mirror, not the mechanism. the tool is secondary.

post it in r/ClaudeCode. one sub, not five — that crowd lives in their session logs, they'll get it instantly. the repo link goes in your first comment, not the body.

**title:** I had 20 AI agents read 8 months of my claude sessions and build a model of how I think. it was unsettling how accurate it was

**body:** i work with claude and codex every day. 8 months, solo. every session gets logged and i never looked back at them.

last night it hit me those logs are the most honest record of how i actually work that exists anywhere. i don't perform in them, i just work. so i mined them.

pulled every message i ever typed, ~1,656 sessions, about 3M tokens of just me. split it into 20 chunks, sent 20 agents at it in parallel, each pulling how i decide, what i reject, how i talk, where i get stuck. merged them into one profile ranked by how many agents independently found each trait. what 15+ of them caught is the real me.

turned the top of it into a skill claude reads before every task. now it starts already knowing how i work instead of me re-explaining myself every session.

you have this same goldmine sitting on your disk right now and you're probably deleting it.

then the move: post it, drop the repo as your own first comment within a minute, and answer every "how" with the mining approach, not features. the comments are where it converts.

</td></tr></table>

## What It Finds

The kind of profile Ditto builds, ranked by how many of the 20 agents independently pulled each trait. What 15+ of them agree on is the real you. Your agent reads this before every task.

> **done means it runs live.** never trust "done" off a code edit. show it working first.
>
> **fix the one thing.** rewriting or "cleaning up" code that isn't the problem gets rejected every time.
>
> **builds faster than they understand what they built** — then asks the agent to explain their own system back.
>
> **voice:** lowercase, short, "you get me", no walls of text, no hype.
>
> **gets frustrated by repeating the same ask** until it lands, not by escalating.

Nobody wrote those rules down. 20 agents pulled them out of one person's own history and agreed on them.

> This is an example. Yours is mined from your logs and will read nothing like it.

---

## What It Does

1. Reads your local session logs and keeps **only the words you typed** (strips all the tool output, file dumps, and pasted errors).
2. **Redacts secrets + personal info** by default, before anything is written or seen by an agent.
3. Splits it into chunks and hands you a prompt to fan a coding agent across them, then merge into one `you.md`.

That `you.md` is a skill/context file. Drop it in `.claude/skills/`, `.codex/skills/`, your `AGENTS.md`, or Cursor rules, and every agent starts already knowing how you work.

## Quickstart

No clone needed - it's one stdlib file:

```bash
curl -O https://raw.githubusercontent.com/ohad6k/ditto/main/ditto.py
python ditto.py --dry-run  # preview counts + output paths without writing files.
python ditto.py            # auto-detects Codex + Claude + Copilot logs. no deps, stdlib only.
```

Or the full repo (gets you the mining prompt + skill too):

```bash
git clone https://github.com/ohad6k/ditto
cd ditto
python ditto.py
```

What you can audit before running it:

- [`ditto.py`](ditto.py) is the extractor. stdlib only, no network calls.
- Redaction happens before text is written to `ditto-out/`.
- The mining prompt is plain markdown: [`MINING_PROMPT.md`](MINING_PROMPT.md).
- The full security model is here: [`SECURITY.md`](SECURITY.md).

You get:

```
sessions: 1,656
your messages: 7,678
tokens (approx): 2,950,000
secrets/PII redacted: 41
wrote: ditto-out/you-corpus.txt  +  20 chunks in ditto-out/chunks/
```

Then open your coding agent (Claude Code / Codex / Cursor), paste [`MINING_PROMPT.md`](MINING_PROMPT.md), point it at `ditto-out/chunks/`, and let it build your `you.md`. Size chunks so each is ~70K tokens (`--chunks N`, N ≈ tokens / 70000) — agents genuinely read that; bigger gets skimmed. Example output: [`examples/you.md`](examples/you.md).

When it finds something true about you that you never wrote down - [post the weirdest one](https://github.com/ohad6k/ditto/issues/1). Don't post your full `you.md`, just the one trait that got you.

## Install Your you.md (Any Agent)

> **More than one self.** The default `you.md` is your *working self* — laws and taste for doing a task. The same logs also hold a *thinking self* (how you reason) and a *designer self* (how you make taste calls). See [`examples/`](examples/lenses/) for all three mined from one real 8-month history, and [`examples/unified-system.md`](examples/unified-system.md) for how ditto stacks with graph memory (Obsidian) and soul.md.

Your `you.md` is just a context file. Drop it where your agent already looks and it reads it before every task:

| Tool | Where it goes |
|---|---|
| Claude Code | `.claude/skills/you/SKILL.md` (or append to `CLAUDE.md`) |
| Codex skill | `~/.codex/skills/you/SKILL.md` |
| Cursor | `.cursor/rules/you.mdc` |
| Codex repo context | `AGENTS.md` |
| Gemini CLI | `GEMINI.md` |
| Windsurf / other | its rules or context file |

Ditto writes the `you.md` with the right frontmatter already, so on Claude Code, Codex, and Cursor it **registers as a skill the moment you drop it in** - nothing to wire. For Codex, use the native skill path above if you want it everywhere; use `AGENTS.md` if you only want it in one repo. That's it, no plugin, no config.

**Using a coding agent?** Point it at this repo and say *"run ditto and install my you.md"* - the skill in [`skills/ditto/`](skills/ditto/SKILL.md) walks it through the whole flow (extract, mine, write, place the file) on its own. Works in Claude Code, Cursor, Codex, and Gemini.

Copy/paste version:

```text
run ditto on my local Claude/Codex logs, mine a you.md from the chunks, install it for my current agent, and show me the session/message/token/redaction counts before claiming it worked.
```

Manual install:

```bash
python ditto.py --install you.md --target codex
python ditto.py --install you.md --target claude
python ditto.py --install you.md --target cursor --repo .
python ditto.py --install you.md --target agents --repo .
python ditto.py --install you.md --target gemini --repo .
```

## Your Card

After mining, get your profile as a card:

```bash
python ditto.py --card
```

Your archetype, your laws with their receipt counts (how many of the 20 agents independently found each one), your session stats, and the one uncomfortable truth. Rendered in the terminal + as `ditto-out/card.html`. Screenshot the card, not the profile - the `you.md` is for your agent; the card is for everyone else.

## Privacy (Read This)

- **100% local.** Ditto makes zero network calls. Your logs never leave your machine. It's plain Python; read the file.
- **Redaction is on by default.** API keys, tokens, JWTs, emails, phone numbers, IPs get stripped before your text hits disk or an agent. (`--no-redact` exists; don't use it.)
- The mining step runs in *your* coding agent, on *your* machine. Nothing gets uploaded unless you choose to.

## How It Works

Your logs are ~95% noise (tool output, file contents, diffs). The signal is the small slice of words you actually typed. Ditto isolates that, drops verbatim-duplicate specs and injected rules you pasted more than once (often ~40% of a heavy history — this is what keeps the token cost down), then uses an agent fan-out so no single context has to hold all of it: each agent reads a chunk and pulls how you decide, what you reject, how you talk, where you get stuck. Traits that show up across many chunks are the real you. One-offs are noise. That ranking is the whole trick.

**It mines your raw sessions, not your `CLAUDE.md` or rules file.** That's the entire point - anything can summarize the rules you already wrote (that's what `/init` does). Ditto surfaces the stuff you *never* wrote down, straight from how you actually worked. If a run builds a profile without reading your real `.jsonl` logs, it isn't Ditto - it's just your rules file reflected back.

## Limits (Being Honest)

- It models how you *work and talk*, not your knowledge. It won't make an agent smarter, it makes it act more like you.
- Garbage in, garbage out: if your logs are 3 sessions long, the profile is thin. It shines around months of history.
- It reads Codex (`~/.codex/sessions`), Claude Code (`~/.claude/projects`), and Copilot CLI (`~/.copilot/session-state`) jsonl out of the box. Other tools: point `--path` at a folder of jsonl.

## Roadmap

Next up: one-command installer, more log sources, and counterweight profiles that use your `you.md` to challenge you instead of mimic you.

See [`ROADMAP.md`](ROADMAP.md).

## Community

Building this in the open.

If you run it, don't post your full `you.md`. Post the weirdest thing it found about how you work:

- [Share what Ditto found in your logs](https://github.com/ohad6k/ditto/issues/1)
- [discord.gg/VNnMq2U5r](https://discord.gg/VNnMq2U5r)

## License

MIT. It's yours. If you build something on it, I'd love to see it.

<p align="center"><i>Made by <a href="https://github.com/ohad6k">@ohad6k</a> while building in public.</i></p>
