# Privacy

Emulo reads your private AI coding-session logs. This page traces what that
means back to the code that does it, so every claim here is checkable in this
repository. Where the code does not enforce something, this page says so
instead of reassuring you.

`SECURITY.md` states the trust boundary in one page. This is the file-by-file
version. The hosted Emulo Pro service has its own legal policy at
`site/privacy.html`; that is a different document with a different purpose.

## What Emulo reads

### Session logs

Discovery roots come from the `SOURCES` table at the top of `emulo.py`:

| Source | Paths read |
|---|---|
| Codex | `~/.codex/sessions`, `~/.codex/archived_sessions` (or `$CODEX_HOME/...`) |
| Claude Code | `~/.claude/projects` |
| Copilot CLI | `~/.copilot/session-state` |
| OpenCode | `$XDG_DATA_HOME/opencode`, default `~/.local/share/opencode` |
| Antigravity | `~/.gemini/antigravity/brain` |

With no flags, all five roots are scanned. `--source NAME` narrows to one.
`--path DIR` replaces all of them with a directory you name. The same flags
exist on `emulo.py plugin preflight` and `plugin prepare`.

Inside those roots, `discover_files` collects exactly three things:

- `**/*.jsonl`
- `*/.system_generated/logs/*.jsonl`, the dot-directory Antigravity hides
  transcripts in
- OpenCode sessions: `opencode.db` opened read-only (`sqlite3.connect(...
  ?mode=ro)`), plus the legacy `storage/session/**/*.json` layout

Any path with a `subagents` directory component is dropped before it is
opened, because every user record in those files is agent-to-agent traffic.

No other file type is opened by discovery. Emulo does not read your source
code, your `CLAUDE.md` or `AGENTS.md`, your git history, your shell history, or
your editor state.

### Inside each log, only the turns you typed

`user_messages` keeps records whose role is `user`, then filters them further:

- Claude Code: `is_human_turn` drops `isMeta`, `isSidechain`, `isCompactSummary`,
  anything carrying `toolUseResult`, and headless `promptSource: "sdk"` +
  `entrypoint: "sdk-cli"` records.
- Copilot CLI: `user.message` records with `data.source == "system"` (steering
  and system injections) are dropped.
- Antigravity: only `USER_INPUT` records with `source == "USER_EXPLICIT"`, and
  only the text inside `<USER_REQUEST>` when present.
- OpenCode: only `text` parts of `role: user` messages, and never parts flagged
  `synthetic`.
- Codex: complete `<subagent_notification>`, `<codex_internal_context>`,
  `<codex_delegation>`, `<turn_aborted>` and `<heartbeat>` envelopes are
  stripped out of the text, as are `<image name=".." path="..">` markers, which
  embed local file paths.
- Every source: `is_injected_context` drops messages starting with the known
  harness prefixes (`# AGENTS.md instructions`, `# CLAUDE.md instructions`,
  `<environment_context`, `<command-name`, `<local-command-stdout`, and the rest
  of `INJECTED_CONTEXT_PREFIXES`), and `is_pasted_log` drops messages that are
  more than a quarter stack-trace lines.

Assistant replies and tool output are never kept. They are not part of any
output file and are never sent anywhere.

### Other files it opens

- Its own state under `EMULO_HOME` (see below).
- `--install PROFILE --target ...` reads the destination adapter file so it can
  update the marked block in place, and reads the profile file you point at.
- `--card` reads `<out>/card.json` and, if present, `<out>/stats.json`.

## What it writes, and where

### 1. Extraction output, in your current working directory

`write_outputs` and `write_stats` create `emulo-out/` in whatever directory you
ran the command from. `resolve_out_dir` uses an existing `ditto-out/` from
before the rename if `emulo-out/` does not exist, and `--out DIR` overrides
both.

| File | Contents |
|---|---|
| `emulo-out/you-corpus.txt` | Every message you typed, redacted, concatenated, with `[YYYY-MM-DD]` headers |
| `emulo-out/chunks/chunk-NN.txt` | The same text split on session boundaries |
| `emulo-out/stats.json` | `sessions`, `messages`, `tokens`, `redactions`, `first_date`, `last_date` |
| `emulo-out/card.html` | Written by `--card`, from `card.json` + `stats.json` |

`you-corpus.txt` is the most sensitive file Emulo produces. Session blocks are
headed `===== session:<id> source:<kind> =====`, where the id is
`sha256("<source>:<absolute path>")[:16]` (`stable_session_id`), so the corpus
itself contains no file paths or project directory names. The text of your
messages is untouched apart from redaction.

Nothing in the code stops you committing this directory. This repository's
`.gitignore` covers `emulo-out/`, `ditto-out/`, `you-corpus.txt`, `chunks/`,
`you.md`, and the appendix files. Your own repository almost certainly does
not.

`--dry-run` reads and counts but writes nothing.

### 2. Private state under `EMULO_HOME`

`resolve_emulo_home` picks, in order: `$EMULO_HOME`, `$DITTO_HOME`, `~/.emulo`,
or an existing `~/.ditto` when `~/.emulo` does not exist yet. Nothing is ever
moved between them automatically.

From `private_paths` and the run/profile writers:

| Path | Contents |
|---|---|
| `cache/segments/1/<hash>.txt` | Selected session text, verbatim after redaction |
| `cache/segment-indexes/`, `cache/receipts/`, `cache/salience/`, `cache/packets/` | Segment metadata, per-message receipt ledger, salience scores |
| `cache/reports/`, `cache/scout-reports/`, `cache/domain-drafts/` | Model-produced JSON reports, including short verbatim quotes of your messages |
| `cache/reductions/` | A copy of the activated profile version |
| `runs/<run_id>/segments/<hash>.txt` | A copy of each selected segment, handed to the mining agent |
| `runs/<run_id>/reports/`, `plan.json`, `selected-segments.json` | Per-run plan and worker output |
| `runs/<run_id>/pack/` | The assembled profile before activation |
| `profiles/default/versions/<version>/` | `you.md`, `you-designer.md`, `you-writer.md`, `you-video.md`, `appendix.md`, `card.json`, `draft-manifest.json`, `manifest.json` |
| `profiles/default/current.json`, `active-profile.json` | Which version is active |
| `migrations/`, `legacy/` | Records from the pre-rename cutover |
| `runtime/versions/<version>/` | `emulo.py` and `MINING_PROMPT.md` installed by the bootstrap |
| `autopilot/` | Autopilot generations, review state, and continuity keys |

`appendix.md` is the sharpest file in there: it lists every referenced evidence
id followed by exact dated verbatim quotes from your sessions, plus recorded
contradictions.

**File permissions are a real gap.** `emulo.py` never calls `os.chmod` and
never passes a `mode` to `os.makedirs`, so everything under `EMULO_HOME` is
created with your default umask. The exception is Autopilot:
`AutopilotStore.initialize` creates `autopilot/` with mode `0o700`, and the
continuity key files are created `0o600`. The "permissions are too broad" check
on those files is skipped entirely on Windows (`if os.name != "nt"`).

### 3. Adapter files, only when you ask

`--install PROFILE --target NAME` writes:

| Target | Destination |
|---|---|
| `claude` | `~/.claude/skills/you/SKILL.md` |
| `codex` | `~/.codex/skills/you/SKILL.md` |
| `cursor` | `<repo>/.cursor/rules/you.mdc` |
| `agents` | `<repo>/AGENTS.md` |
| `gemini` | `<repo>/GEMINI.md` |
| `opencode` | `~/.config/opencode/AGENTS.md` |

The last three append or replace a block between
`<!-- emulo profile:start -->` and `<!-- emulo profile:end -->` (pre-rename
`ditto` markers are still recognised). An incomplete existing block makes the
install refuse rather than rewrite the file. Note that `agents` and `gemini`
write into a repository, which is a file you are likely to commit.

## What leaves the machine, and when

### `emulo.py` itself makes no network calls

Its imports are `argparse, base64, glob, hashlib, json, os, re, shutil,
sqlite3, stat, sys, tempfile, time, unicodedata, uuid`, plus `webbrowser`
inside `show_card`. There is no `urllib`, no `http`, no `socket`, no
`subprocess`. The only URLs in the file are a printed link to the GitHub issue
and the card artwork URL described below. `webbrowser.open` is called on a
`file://` path.

### The model calls are made by your agent, not by Emulo

This is the part that actually matters, and Emulo does not control it.

The mining flow is: `plugin preflight` (read-only plan) → your approval →
`plugin prepare` (copies selected segments into `runs/<run_id>/segments/`) →
your agent runs one worker per uncached segment → a reducer over the validated
reports.

- Each worker reads **one segment file**, which is your own redacted messages
  verbatim, and puts it in the model's context. That text goes to whichever
  provider your agent is configured to use.
- Each worker report is bounded: at most 8,192 bytes, at most 12 evidence
  items, quotes at most 200 characters, dated and verbatim from the covered
  session (`MAX_REPORT_BYTES`, `MAX_EVIDENCE_PER_REPORT`, `MAX_QUOTE_CHARS`,
  enforced in `validate_report`).
- The reducer reads the validated reports, not the raw session text.

So the honest statement is: your own words, after redaction, are sent to a
model provider you choose. Segments you did not select are never handed to a
worker. Raw log files, assistant text, and tool output are never sent because
they were dropped at extraction. With a local model, nothing leaves the
machine at all.

Emulo cannot see which provider your agent uses, cannot see that provider's
retention or training settings, and does not attempt to. Check those yourself.

`--no-redact` removes the redaction pass entirely. Selected raw text, including
whatever secrets are in it, is then what the worker sees.

### The bootstrap download

`.agents/skills/emulo/scripts/bootstrap.py` downloads exactly two files,
`emulo.py` and `MINING_PROMPT.md`, from
`https://raw.githubusercontent.com/ohad6k/emulo/<tag>/`, at the exact release
tag in `runtime.json`. The final response host is pinned to
`raw.githubusercontent.com` after redirects, each file has a 4 MB ceiling, and
both must match the SHA-256 in `runtime.json` before the runtime pointer moves.
This happens before any log discovery, so no session data exists yet to send.
The request carries a `User-Agent: emulo-bootstrap/1` header and nothing else.
In a checkout, `--source-root` reads the files locally and no request is made.

### The card HTML fetches a remote image

`render_card_html` embeds
`https://raw.githubusercontent.com/ohad6k/emulo/main/assets/emulo.png` as the
`onerror` fallback for the artwork, and uses that URL directly when a local
`assets/emulo.png` does not sit next to `emulo.py`. `pyproject.toml` ships only
the `emulo` module and the `emulo_autopilot` package, with no asset data, so a
`pip install emulo` or `uvx emulo` card always points at the remote URL.

No profile data is in that request. But opening `card.html` in a browser does
tell githubusercontent.com that you opened it. `--no-open` stops Emulo from
launching the browser; it does not remove the URL from the file. Delete the
`<img>` tag if that matters to you.

### The MCP server and the plugin skills

`mcp_main` reads JSON-RPC from stdin and writes to stdout. There is no network
code in it. It exposes one tool, `load_emulo_profile`, which returns
`you.md` plus the requested domain file (`resolve_profile_paths`) and, if
present, the Autopilot overlay. It never returns `appendix.md`.

That said, the point of the tool is to put your profile text into an MCP
client's context, so your profile reaches whatever model that client talks to.
The plugin skills (`emulo:work`, `emulo:design`, `emulo:write`, `emulo:video`)
do the same thing through a different loader. Neither adds a network call of
its own.

### Emulo Pro continuity (opt-in, and only when you run it)

The `emulo-autopilot continuity-*` commands are the only part of this repo that
uploads anything. There is no daemon, timer, or background sync in the package:
every push and pull is a command you type.

- `continuity-init` generates the keys locally and prints a recovery secret
  once. The master key and device private key live in
  `autopilot/continuity/private-material.json` (mode `0o600`);
  `recovery-kit.json` holds the master key wrapped with your recovery secret.
  Neither the recovery secret nor an unwrapped key is written to the server.
- `continuity-connect` POSTs to `<server>/v1/devices/pair/complete`, default
  `https://emulo-production.ohad1306.workers.dev`, overridable with `--server`.
  It sends the pairing code, the device label you pass, the device X25519
  public key, the master key wrapped to that public key (X25519 + AES-GCM,
  `wrap_master_key_for_device`), and the client version.
- `continuity-push` uploads one envelope: AES-GCM ciphertext of the profile
  bundle, plus these fields **in plaintext**: `schema_version`,
  `generation_id`, `parent_generation_id`, `author_device_id`, `created_at`,
  `nonce`, `ciphertext_sha256`. The server therefore learns your device ids,
  timestamps, and generation graph, but not the content.
- The bundle inside the ciphertext is the generation metadata plus the domain
  profile artifacts, whose names are constrained to `work.md`, `design.md`,
  `write.md`, `video.md` (`_ARTIFACT` in `continuity.py`). Raw session logs,
  the corpus, segments, reports, and `appendix.md` are not in it.
- Transport requires an HTTPS origin with no path, query, fragment, or
  credentials (`validate_https_origin`), refuses redirects (`_NoRedirect`), and
  caps responses at 280 KB.
- Failed uploads are stored locally in the pending list and retried only when
  you run `continuity-retry`.

### One thing this repo cannot prove

`SECURITY.md` states that the skills.sh CLI reports anonymous installation
telemetry by default and that `DISABLE_TELEMETRY=1` opts out. That CLI is not
part of this repository, so that behaviour cannot be verified from this code.
Treat it as a third-party claim.

## What is redacted, and what is not

Redaction runs once, in `mine_files`, before any text is written to disk or
handed to any model. The full pattern list is `REDACTIONS` in `emulo.py`:

| Redacted | Pattern |
|---|---|
| OpenAI-style keys | `sk-...` |
| Stripe live keys | `sk_live_...` |
| Webhook secrets | `whsec_...` |
| Supabase tokens | `sbp_...` |
| GitHub tokens | `ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_` |
| JWTs | `eyJ<header>.<payload>.<signature>` |
| AWS access keys | `AKIA...` |
| Slack tokens | `xoxb-`, `xoxa-`, `xoxp-`, `xoxr-`, `xoxs-` |
| Email addresses | any `user@host.tld` |
| IPv4 addresses | dotted quads |
| Phone numbers | `+CC` international form, or a national trunk `0` form |
| Assignments | `api_key`, `api-key`, `secret`, `token`, `password`, `passwd` followed by `:` or `=` |
| Spoken credentials | `password is X`, `passphrase X`, `psk X`, `passkey X`, `wifi key X`, only when `X` is 12+ chars, contains a digit, or is not purely alphabetic |

Two structural filters reduce exposure without being redaction: repeated
verbatim messages of 200 characters or more are collapsed to the first copy
(`DEDUPE_MIN_LEN`, disable with `--no-dedupe`), and session identity is hashed
rather than stored as a path.

**Not redacted.** Verified by what is absent from `REDACTIONS`:

- names of people, companies, clients, and projects
- credit card, bank account, SSN, and passport or ID numbers
- street addresses
- URLs of any kind, including internal hostnames and signed links, unless the
  token inside one happens to match a pattern above
- file paths, repository names, and directory structure that you typed into a
  message (the ones Emulo constructs itself are hashed, but the ones you typed
  are your text and survive)
- IPv6 addresses
- domestic phone formats with no `+` and no leading `0`; the code comment says
  `415-555-2671` is intentionally not matched, because the older pattern that
  caught it also ate dates and version numbers
- passwords that look like a short plain English word, kept deliberately so
  prose like "the password is wrong" survives
- credentials in any shape not listed in the table, including provider key
  formats that did not exist when the list was written
- PII in languages or formats the patterns do not cover

Redaction is applied at extraction only. Nothing re-redacts later. If a secret
survives that single pass, it is in the corpus, in the chunks, in the cached
segments, in the run segments, in whatever the model saw, and possibly quoted
in `appendix.md`.

There are regression tests for the credential and phone patterns
(`tests/test_emulo.py`), but no test claims coverage of real secrets in a real
history, because that is not a thing a regex list can promise.

## Before you share a profile or a card

Ordered by how much of you is in the file:

| Artifact | What is in it | Share? |
|---|---|---|
| `you-corpus.txt`, `chunks/` | Every message you typed | Never |
| `appendix.md` | Exact dated verbatim quotes behind every rule | Never |
| `cache/segments/`, `runs/*/segments/` | The same text, split | Never |
| `you.md`, `you-designer.md`, `you-writer.md`, `you-video.md` | Paraphrased rules and actions, no quotes, but they describe your work and can name your tools, stack, and projects | Read it first |
| `card.json` / `card.html` | Archetype, up to three law texts with distinct-session counts, session/message/token counts, date range, and one "truth" line | Read it first |

Before anything goes public:

1. Open the card and read every line. Law text is model-written from your own
   rules and can name an employer, a client, a repo, or a stack.
2. Note that `validate_profile_pack` checks the archetype and that each law
   matches a validated work rule with a correct session count. It does **not**
   validate the `truth` field. That line is free text from the reducer.
3. Search the file for your employer, client names, internal hostnames, repo
   names, and anything under NDA. The redaction list does not cover any of
   them.
4. Do not post `appendix.md`, the corpus, the chunks, or a full profile,
   however tempting the screenshot is.
5. If the run used `--no-redact`, treat every artifact from it as raw session
   text.
6. Run `git status` in the directory you ran Emulo from. `emulo-out/` lands in
   your working directory, and your repo probably does not ignore it.

## Known gaps

Stated plainly, because a privacy page that only lists guarantees is not one:

- Nothing in the code prevents you from sharing `appendix.md`, the corpus, or a
  full profile. The protection is this page and `SECURITY.md`, not an
  enforcement path.
- `EMULO_HOME` and `emulo-out/` are created with your default umask.
  `emulo.py` sets no restrictive permissions. Only the Autopilot subtree does,
  and its permission checks are skipped on Windows.
- Redaction is a regex list. It is best-effort by design and will miss
  credential formats it does not know.
- Emulo cannot observe or control what your model provider does with the text
  your agent sends it.
- There is no purge command. Deleting your data means deleting `emulo-out/` and
  `EMULO_HOME` yourself. `emulo.py plugin` offers `status`, `preflight`,
  `prepare`, the `validate-*` and `cache-*` commands, `assemble`, `next-stage`,
  `activate`, `profile-path`, and the `migrate-*` commands. None of them
  removes mined state.
- Uninstalling the plugin does not touch `EMULO_HOME`, which is deliberate, but
  it means your mined history outlives the tool.
