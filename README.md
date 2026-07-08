<p align="center"><img src="assets/ditto.png" width="360" alt="ditto"></p>

<h1 align="center">ditto</h1>

<p align="center"><b>your AI agents act like they just met you. ditto fixes that.</b></p>

<p align="center">
<img src="https://img.shields.io/github/stars/ohad6k/ditto?style=for-the-badge&color=14b8a6&labelColor=17303a&logo=github&logoColor=white" alt="stars">
<img src="https://img.shields.io/badge/license-MIT-14b8a6?style=for-the-badge&labelColor=17303a" alt="MIT">
<img src="https://img.shields.io/badge/python-zero_deps-14b8a6?style=for-the-badge&labelColor=17303a&logo=python&logoColor=white" alt="python, zero deps">
<img src="https://img.shields.io/badge/works_with-claude_·_cursor_·_codex_·_gemini-17303a?style=for-the-badge&labelColor=14b8a6" alt="works with claude, cursor, codex, gemini">
</p>

<p align="center">
you have months of chat logs with claude / codex / cursor sitting on your disk.<br>
it's the most honest record of how you actually think, and you're deleting it.<br>
ditto mines it into a <code>you.md</code> your agents read before every task.
</p>

---

## the difference

ask an agent to "clean up" a 7-line function. watch what each one hands back.

<table>
<tr><th>cold agent</th><th>agent + ditto</th></tr>
<tr valign="top"><td>

> The main issue is a bug: `fetch` is async, so `data` is `null` when your `if` runs...
>
> ```js
> async function getUser(id) {
>   const res = await fetch(`/api/users/${id}`);
>   if (!res.ok) return "no user";
>   const user = await res.json();
>   return user?.name ?? "no user";
> }
> ```
>
> *changed: async/await, const over var, template literals, an `res.ok` check, `?.` / `??` guards.*
>
> Want me to add a try/catch for network errors too?

</td><td>

> the fetch is async so `data` is always null when you check it. that's the bug, not the style.
>
> ```js
> async function getUser(id){
>   const r = await fetch('/api/users/'+id)
>   const data = await r.json()
>   return data != null ? data.name : "no user"
> }
> ```
>
> caller has to `await getUser(...)` now.

</td></tr>
</table>

both caught the bug. the cold one rewrote your style, bolted on error handling you never asked for, and offered to add more. ditto fixed the one thing and stopped. it didn't get smarter. it did less, the way you would.

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
