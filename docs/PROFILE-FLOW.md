# The profile flow, step by step

This guide explains what Emulo does with your session logs, what it writes, what can reach a model provider, and how to load and remove a profile. It describes Emulo 0.6.6.

Commands use `emulo`, which `pip install emulo` puts on your path. From a checkout of this repository, use `python emulo.py` instead.

## 1. Three separate things

Emulo does three different jobs. You can use any of them without the others.

| Job | Command | Uses a model? | Writes files? |
|---|---|---|---|
| Usage report | `emulo --coach` | No | No |
| Mine a profile | `emulo`, then a coding agent | Yes, in the agent step | Yes |
| Load a profile | `emulo --install ...`, or `emulo mcp` for a plugin-activated profile | Emulo does not. The agent that loads it does. | `--install` writes one file or block |

**The usage report** reads the messages you typed and prints counts: asks you sent three or more times in a row, messages that say "as I said", runs of near-identical asks, and messages that open like a correction. Every finding prints the dated messages behind it. It makes no model call and writes nothing.

**Mining** has two halves. First Emulo reads your logs on your machine, keeps only what you typed, redacts it, and writes it out as text files. Then a coding agent reads those files and writes the profile. The second half is the only part that involves a model.

**Loading** puts a finished profile where an agent reads it: a skill folder, a rules file, or an MCP server the agent can call.

If you only want to see how you use the model, `emulo --coach` is all you need.

Whether loading a profile makes an agent's work better is not proven. The one published test so far, where a mined profile was run against a made-up one, is at <https://emulo.vercel.app/placebo>.

### Two ways to mine

There are two mining paths and they store the profile in different places.

- **The one-file CLI (the `RUN_ME.md` path).** You run `emulo`. It writes `emulo-out/` with chunk files and a `RUN_ME.md` straight away, with no plan or approval step, because it makes no model call. You tell your agent `read emulo-out/RUN_ME.md and follow it`, and the agent writes `emulo-out/you.md`. You load it with `emulo --install`. This path writes no card.
- **The agent mining flow (plugin or bootstrap).** You ask your agent to `run emulo` (after `npx skills add ohad6k/emulo@emulo`) or use `emulo:mine` from the native plugin. The agent runs `emulo plugin preflight`, shows you the plan, waits for your approval, runs one worker pass per segment and one reducer pass, and activates the profile inside `~/.emulo`, including a `card.json`.

The MCP server only serves a profile activated by the agent mining flow. It does not read a `you.md` from the `RUN_ME.md` path, even after you install it with `emulo --install`. The same is true of the `emulo:work`, `emulo:design`, `emulo:write` and `emulo:video` skills.

## 2. Before mining

### Where Emulo looks

With no options, Emulo searches all of these. `~` is your home directory (`C:\Users\<you>` on Windows, from `USERPROFILE`). The code uses the same layout on every operating system.

| Source | Where it looks | Override |
|---|---|---|
| Codex | `~/.codex/sessions` and `~/.codex/archived_sessions` | `CODEX_HOME` replaces `~/.codex` |
| Claude Code | `~/.claude/projects` | none |
| Copilot CLI | `~/.copilot/session-state` | none |
| OpenCode | `~/.local/share/opencode` (the `opencode.db` SQLite file and `storage/session/**/*.json`) | `XDG_DATA_HOME` replaces `~/.local/share` |
| Google Antigravity | `~/.gemini/antigravity/brain` | none |

If `CODEX_HOME` or `XDG_DATA_HOME` is set but empty, Emulo treats it as unset and uses the default above. (Before 0.6.6, an empty value made it search folders under the directory you ran it from.)

It reads every `*.jsonl` file under those folders, skips any file under a `subagents` folder, and reads OpenCode's database read-only. It looks nowhere else.

To narrow it:

```bash
emulo --dry-run --source claude      # one source: codex, claude, copilot, opencode or antigravity
emulo --dry-run --path ./my-logs     # only this folder
```

### What is kept

Only messages you typed. Each kept message keeps its date. Each session gets a header like `===== session:3d6edccf33496eaa source:claude =====`. The session id is a hash of the log file path, not the path itself.

### What is dropped

- Assistant replies, tool calls and tool output.
- Records the agent marks as not typed by a human: Claude Code meta, sidechain and compact-summary records, headless SDK prompts, Copilot system steering, Antigravity input that is not marked as typed, and OpenCode synthetic parts.
- Injected context: messages that start with pasted `AGENTS.md` or `CLAUDE.md` instructions, IDE context, attached-file lists, `<environment_context>`, slash-command wrappers, task notifications, `[Request interrupted`, and similar harness text. Codex control envelopes and image markers are stripped and the text around them is kept.
- Pasted stack traces and error dumps (a message of four or more lines where more than a quarter of the lines look like stack frames).
- Emulo's own chunks. Since 0.6.5, any message with a line that matches Emulo's chunk header is dropped whole, including any question you typed around it.
- Repeats. A message of 200 or more characters that appears again word for word is kept once. `--no-dedupe` turns this off. `--coach` never collapses repeats, because repeats are what it counts.

### Redaction

Redaction runs before anything is written. This list is the one in [SECURITY.md](../SECURITY.md), where each pattern is pinned by a test. It covers:

- OpenAI keys (`sk-`, `sk-proj-`, `sk-svcacct-`, `sk-admin-`)
- Anthropic keys (`sk-ant-`)
- Google API keys (`AIza` plus 35 characters)
- Stripe live secret keys (`sk_live_`)
- webhook secrets (`whsec_`)
- Supabase access tokens (`sbp_`)
- GitHub tokens (`ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_`)
- JWTs (three dot-separated parts starting `eyJ`)
- AWS access key IDs (`AKIA`)
- Slack tokens (`xoxb-`, `xoxa-`, `xoxp-`, `xoxr-`, `xoxs-`)
- the password in a connection URL (`scheme://user:password@host`; tested for postgres, postgresql, mysql, mongodb+srv, redis, amqp and https, including a percent-encoded password)
- email addresses
- phone numbers with an international or trunk prefix
- IPv4 addresses
- any value assigned with `=` or `:` to a name ending in `api_key`, `apikey`, `api-key`, `secret`, `token`, `password` or `passwd`, in any case, so `client_secret=` and `GITHUB_TOKEN=` are covered
- `password is`, `passwd`, `passphrase`, `passkey`, `psk` and `wifi key` followed by a value, when that value has a digit or a symbol or is at least 12 characters long

Anything else passes through. Known misses:

- `AWS_SECRET_ACCESS_KEY=...`, because the name ends in `ACCESS_KEY`
- a provider key with no fixed prefix
- a connection URL password that holds a raw `#`, `/`, `?` or space
- a connection URL password after a user name that holds a raw `@`, as in `postgres://user@corp.com:pw@host`, where only the user name is replaced

Redaction is best-effort. Read the output before you share it.

The line `messages with secrets/PII redacted` counts messages that had anything replaced, not the number of items.

`--no-redact` turns redaction off. Do not use it unless you are keeping everything local.

### The dry run

```bash
emulo --dry-run
```

This reads your logs, applies all the rules above, and prints counts. It makes no model call and writes no files. On a small test history it printed:

```text
dry run: no files written
looked in: <each folder from the table above>
jsonl files: 3
sessions: 3
your messages: 6
tokens (approx): 110
messages with secrets/PII redacted: 2
would write: emulo-out/you-corpus.txt  +  emulo-out/RUN_ME.md  +  chunks in emulo-out/chunks/
```

If nothing is found it prints `no session logs found`, lists every folder it looked in, and exits with status 1.

On the agent mining flow, the plan comes from `emulo plugin preflight`. It prints one line of JSON with the valid sessions, the source tokens, the planned worker and reducer passes, and an `approval_hash`. It writes nothing. `emulo plugin prepare --approved-plan-hash HASH` refuses to run if the plan changed since you approved it.

## 3. What can reach a model provider

`emulo.py` makes no network calls and calls no model. These steps run entirely on your machine: `--coach`, `--dry-run`, extraction, `verify`, `--install`, the MCP server, and the `plugin` subcommands.

Text reaches a model in exactly these places:

1. **The mining agent.** When your coding agent reads the chunk files (`RUN_ME.md` path) or its assigned segments (agent mining flow), that text goes to the model the agent runs on. The text is your redacted typed messages, their dates, the session id hashes and the source names, plus the instructions in `RUN_ME.md` or `MINING_PROMPT.md`.
2. **The reducer, in the agent mining flow.** It reads the workers' JSON reports, not your raw logs. Those reports contain short verbatim quotes of your messages.
3. **Loading the profile.** Whenever an agent loads your profile, the profile text goes to that agent's model with the task. A profile includes quotes of your own messages.

Emulo cannot control what else the agent does while it works, such as other files it opens. That is up to the agent and its settings.

To keep everything on your machine, run the mining agent, and any agent that loads the profile, on a local model. Emulo does not include or set up a model. Whether your agent can use a local one depends on the agent.

One more network step, not involving your logs: the `npx skills add` bootstrap downloads `emulo.py` and `MINING_PROMPT.md` from GitHub at the exact release tag and checks their SHA-256 before running them. That happens before any log is read. The skills.sh CLI sends anonymous install telemetry by default; `DISABLE_TELEMETRY=1` turns it off.

## 4. Output files and caches

### The `RUN_ME.md` path

```bash
emulo
```

It writes to `emulo-out/` inside the folder you run it from. `--out DIR` picks another folder, and `--chunks N` sets roughly how many chunks (default 20).

| File | What it is |
|---|---|
| `emulo-out/you-corpus.txt` | All kept, redacted messages in one file |
| `emulo-out/chunks/chunk-01.txt` ... | The same text split on session boundaries |
| `emulo-out/stats.json` | Session, message, token and redaction counts and the date range |
| `emulo-out/RUN_ME.md` | Instructions for your agent, listing the chunk files |
| `emulo-out/you.md` | The profile. The agent writes this, not Emulo. |

This path writes no `card.json`, so `emulo --card` has nothing to show after it. It says so and exits with status 1. A card comes only from the agent mining flow: `emulo plugin status` prints its `card_path`, and `emulo --card <card_path>` renders it and writes `card.html` into `emulo-out/` (or `--out DIR`).

Running `emulo` again replaces `chunks/` and overwrites the corpus, `stats.json` and `RUN_ME.md`. It does not touch `you.md`. If you have an old `ditto-out/` folder and no `emulo-out/`, Emulo keeps using `ditto-out/`.

The next step is one line to your agent, opened in the same folder:

```text
read emulo-out/RUN_ME.md and follow it
```

Let the agent open `RUN_ME.md` and the chunks with its own file tools. Do not paste chunk text into the prompt (see section 8).

This path writes nothing to `~/.emulo`.

### The agent mining flow

Everything goes to `~/.emulo`, or to `EMULO_HOME` if set. An existing `~/.ditto` from before the rename is still used if `~/.emulo` holds no mined data.

| Folder | What it holds |
|---|---|
| `cache/segments/`, `cache/segment-indexes/` | Your redacted messages, split into segments, in plain text |
| `cache/reports/`, `cache/reductions/` | Validated worker reports and reducer output, reused on the next run |
| `runs/<run id>/` | Each run's plan, its copies of the segments, reports and the draft pack |
| `profiles/default/versions/<version>/` | The activated profile: `you.md`, `you-designer.md`, `you-writer.md`, `you-video.md` (only the active ones), `appendix.md` with the private quotes behind each rule, `card.json` and `manifest.json` |
| `profiles/default/current.json`, `active-profile.json` | Which version is active |
| `runtime/` | The bootstrap's downloaded copy of `emulo.py` and `MINING_PROMPT.md` |
| `migrations/`, `legacy/` | Records and backups from upgrading an old install |

`emulo plugin status` prints the active version, which domains are active, and the card path. `emulo plugin profile-path --domain work` prints the exact profile files.

### Deleting output and caches

The CLI output folder:

```bash
rm -rf emulo-out                           # macOS, Linux
Remove-Item -Recurse -Force emulo-out      # Windows PowerShell
```

Everything the agent mining flow stored, including the active profile:

```bash
rm -rf ~/.emulo                            # macOS, Linux
Remove-Item -Recurse -Force $HOME\.emulo   # Windows PowerShell
```

After that, the MCP server and the `emulo:*` skills report `no active Emulo profile; run emulo`. If you only delete `~/.emulo/cache` and `~/.emulo/runs`, the active profile stays, and the next mining run cannot reuse earlier work.

## 5. Inspect, edit and verify

### Read and edit it

`you.md` is plain Markdown. Open it, read every rule, and delete or rewrite anything that is wrong. It is your file.

`you.md` needs no frontmatter. See section 6 for what `--install` does with it.

Profile files from the agent mining flow are hash-checked against their manifest. If you edit one in place, the loaders refuse it with `corrupt active profile; run emulo to recover`. To change one, mine again.

### Check the receipts

```bash
emulo verify emulo-out/you.md
```

It finds every quoted span in the profile and searches your mined corpus for it. On a test profile with one invented quote it printed:

```text
checked 3 quotes against 3 sessions in emulo-out

  NOT FOUND  "I love a long planning meeting"

  one session  "fix the one thing I asked about"  (8b0f15686137fe49)

2/3 quotes traced to a real session.

1 quote(s) appear in no session. Cut those rules.
```

It exits with status 1 when any quote is not found, 2 when the profile or the mined corpus is missing, and 0 otherwise. `--json` prints the same result with the supporting session ids. `--out DIR` points it at another output folder.

What it checks: that each quote in straight or curly double quotes, of four or more words, appears in `emulo-out/you-corpus.txt` (or the chunk files), ignoring case, spacing and quote style. It also flags quotes found in only one session.

What it cannot check:

- whether a rule actually follows from its quote
- the date next to a quote
- rules with no quote, quotes shorter than four words (`--min-words` changes this), and quotes in single quotes or backticks
- anything outside the corpus currently in `emulo-out`. If you mined different sources since, re-run `emulo` over the same history first. This also applies to a profile from the agent mining flow: `verify` reads `emulo-out`, not `~/.emulo`.

Whether a rule is vague or generic is still your call.

## 6. Install into an agent

```bash
emulo --install emulo-out/you.md --target claude
emulo --install emulo-out/you.md --target codex
emulo --install emulo-out/you.md --target opencode
emulo --install emulo-out/you.md --target cursor --repo .
emulo --install emulo-out/you.md --target agents --repo .
emulo --install emulo-out/you.md --target gemini --repo .
```

| Target | Where it writes | How |
|---|---|---|
| `claude` | `~/.claude/skills/you/SKILL.md` | Copies the file as a skill |
| `codex` | `~/.codex/skills/you/SKILL.md` | Copies the file as a skill |
| `cursor` | `<repo>/.cursor/rules/you.mdc` | Writes a rule with `alwaysApply: true` and your profile body |
| `agents` | `<repo>/AGENTS.md` | Adds a marked block |
| `gemini` | `<repo>/GEMINI.md` | Adds a marked block |
| `opencode` | `~/.config/opencode/AGENTS.md` | Adds a marked block |

A skill needs `name` and `description` frontmatter. For `claude` and `codex`, if `you.md` has no frontmatter, `--install` adds `name: you` and a default description to the installed copy and prints a note saying so. Your `you.md` is not changed. If `you.md` has frontmatter with `name` and `description`, it is installed as written. If it has frontmatter missing either one, or otherwise malformed, it is refused; fix the two fields or delete the block. Blank lines or an indent before the opening `---` do not hide it. The other four targets drop the frontmatter and install only the body.

`--repo` defaults to the current folder. `--dry-run` prints the destination without writing. The command prints `destination:` and `installed:` with the full path.

For `agents`, `gemini` and `opencode`, Emulo appends this to the end of the file and leaves the rest of the file alone:

```text
<!-- emulo profile:start -->
# emulo profile

<your profile, without its frontmatter>
<!-- emulo profile:end -->
```

If the destination already exists, Emulo stops and asks for `--yes`. With `--yes`, `claude`, `codex` and `cursor` overwrite the whole file, and `agents`, `gemini` and `opencode` replace only the marked block.

OpenClaw and Hermes Agent load the profile as a standard skill: see [OPENCLAW_HERMES.md](OPENCLAW_HERMES.md).

### The MCP server

```bash
emulo mcp
```

It speaks MCP over stdio and exposes one tool, `load_emulo_profile`, with a `domain` of `work` (the default), `design`, `write` or `video`. Add it to your MCP client's config:

```json
{
  "mcpServers": {
    "emulo": { "command": "emulo", "args": ["mcp"] }
  }
}
```

The MCP server only serves a profile activated by the agent mining flow (`run emulo` or `emulo:mine`), stored in `~/.emulo` (or `EMULO_HOME`, or `--emulo-home DIR`). It does not serve a `you.md` from the `RUN_ME.md` path, whether or not you installed it. Until a profile has been activated, the tool returns `no active Emulo profile; run emulo`. If you used the `RUN_ME.md` path, load your profile with `--install` instead.

## 7. Turn it off or remove it

Emulo 0.6.6 has no uninstall command. Removal is deleting what `--install` wrote.

| Target | Delete |
|---|---|
| `claude` | the folder `~/.claude/skills/you/` |
| `codex` | the folder `~/.codex/skills/you/` |
| `cursor` | the file `<repo>/.cursor/rules/you.mdc` |
| `agents` | the marked block in `<repo>/AGENTS.md` |
| `gemini` | the marked block in `<repo>/GEMINI.md` |
| `opencode` | the marked block in `~/.config/opencode/AGENTS.md` |

For a marked block, open the file and delete every line from `<!-- emulo profile:start -->` through `<!-- emulo profile:end -->`, both marker lines included. Nothing else in the file belongs to Emulo. When it added the block, it also trimmed any blank lines at the end of your file and put one blank line above the block, so you may want to remove that line too. If Emulo created the file and it is now empty, delete the file. Installs made before the rename use `<!-- ditto profile:start -->` and `<!-- ditto profile:end -->`; remove those the same way.

Delete both markers or neither. If only one is left, the next `--install` refuses with `existing Emulo block is incomplete; refusing to modify it`.

For the MCP server, remove the `emulo` entry from your client's MCP config. For the native plugin or the skills.sh bootstrap, remove them with your agent's plugin or skill manager. Removing the plugin does not delete `~/.emulo`.

Then delete the output and caches as in section 4.

## 8. Profiles mined before 0.6.5

If you ever sent Emulo's chunks to an agent inside a prompt, instead of letting it open `RUN_ME.md` and the chunk files with its tools, your agent logged that prompt as a message from you. Emulo before 0.6.5 read those messages back as yours, so a profile mined before 0.6.5 may be partly built from Emulo's own earlier output.

Re-mine with 0.6.5 or later. It drops any message that carries Emulo's chunk header. Check your version with `emulo --version`.
