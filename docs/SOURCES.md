# Session sources

Every session-log source Emulo reads today, and the ones planned. Groundwork for
[issue #3](https://github.com/ohad6k/emulo/issues/3). Every path and record shape below traces to code
in `emulo.py` or to a test; anything unproven is marked unverified.

Emulo only ever extracts the turns you typed. Assistant replies, tool output, reasoning, and
harness-injected traffic never enter the corpus, in every source. That filter lives in
`user_messages()` and its per-source helpers in `emulo.py`.

## Supported today

| Source | Root | Format | Selected by |
|---|---|---|---|
| Codex | `$CODEX_HOME/sessions`, `$CODEX_HOME/archived_sessions` (default `~/.codex`) | jsonl | `--source codex` |
| Claude Code | `~/.claude/projects` | jsonl | `--source claude` |
| Copilot CLI | `~/.copilot/session-state` | jsonl | `--source copilot` |
| OpenCode | `$XDG_DATA_HOME/opencode` (default `~/.local/share/opencode`) | SQLite + legacy json | `--source opencode` |
| Google Antigravity | `~/.gemini/antigravity/brain` | jsonl | `--source antigravity` |
| Any folder | whatever you point at | jsonl | `--path <folder>` |

`--source auto` (the default) reads all five. The roots are the `SOURCES` dict at the top of
`emulo.py`; the CLI choices are on the `--source` argument in `legacy_main()`.

One note on operating systems: the code expands `~` and reads the same relative paths everywhere.
There is no per-OS branch in the source layer, so a macOS-only or Windows-only install location for
any of these products would not be found today. Only `CODEX_HOME` and `XDG_DATA_HOME` shift a root.

### Codex

Roots come from `CODEX_HOME` if set, otherwise `~/.codex`, and both `sessions/` and
`archived_sessions/` are read (`SOURCES` in `emulo.py`; covered by
`tests/test_codex_control_envelopes.py::CodexLogRootsTest`).

Records look like `{"type": "response_item", "payload": {"type": "message", "role": "user",
"content": [{"text": ...}]}}`. Codex also writes harness traffic into `role:user` records, so
complete `<subagent_notification>`, `<codex_internal_context>`, `<codex_delegation>`,
`<turn_aborted>`, and `<heartbeat>` envelopes are stripped and any human text around them is kept
(`CODEX_CONTROL_ENVELOPE`). Image attachment markers are stripped with their embedded local file
paths (`CODEX_IMAGE_MARKER`). A bare `<skill>` tag is deliberately kept: it is indistinguishable
from a human pasting XML.

Evidence: `tests/test_codex_control_envelopes.py`.

### Claude Code

Root is `~/.claude/projects`, recursive `*.jsonl`. Records look like `{"type": "user", "message":
{"role": "user", "content": "..." | [...]}}`.

Claude Code also routes harness traffic through `role:user`, so `is_human_turn()` drops records
carrying `isMeta`, `isSidechain`, `toolUseResult`, or `isCompactSummary`. When `origin` is present
its `kind` is authoritative and only `human` is kept; otherwise a record is dropped only when
`promptSource == "sdk"` *and* `entrypoint == "sdk-cli"`, because Claude Desktop stamps
`promptSource: "sdk"` on prompts a human actually typed.

Agent-to-agent transcripts are skipped by path: any file with a `subagents` path component is
dropped in `discover_files()` (component match, so `my-subagents-notes/` survives).

Evidence: `tests/test_claude_human_turns.py`.

### Copilot CLI

Root is `~/.copilot/session-state`, recursive `*.jsonl`. Records look like `{"type":
"user.message", "data": {"content": ..., "source": ...}, "timestamp": ...}`, and anything with
`data.source == "system"` is dropped as steering or system injection (`user_messages()`).

Logs are all named `events.jsonl` under a per-session directory, so `session_label()` prefixes the
parent directory (the session id) to keep session blocks distinguishable in the corpus.

Evidence: no dedicated test file. The record shape and the `session-state` layout are documented in
`emulo.py` comments and exercised only through the shared `user_messages()` path. Treat this one as
the least covered adapter.

### OpenCode

Root is `$XDG_DATA_HOME/opencode`, defaulting to `~/.local/share/opencode` (`OPENCODE_DATA`).
Two layouts are read, both by `discover_opencode_sessions()`:

**Current SQLite store.** `opencode.db` in the root, opened read-only through
`file:...?mode=ro`. Discovery lists `select distinct session_id from message`, and each session
becomes one virtual entry `<db path>::<session id>` (`OPENCODE_DB_SESSION_SEP`), so counts, labels,
and cache identity stay per-session like every other source. Extraction joins `part` to `message`
and keeps `part` rows of type `text` whose parent message has `role: "user"` and which are not
`synthetic` (`opencode_db_messages()`).

**Legacy JSON layout.** `storage/session/{project}/{session}.json` with sibling `message/` and
`part/` directories keyed by session and message ids (`opencode_storage_messages()`). Routing is by
layout, not folder name, so an exported legacy store under any `--path` still mines.

Evidence: `tests/test_opencode_source.py`.

### Google Antigravity

Root is `~/.gemini/antigravity/brain`. Transcripts sit at
`brain/<conversation-id>/.system_generated/logs/*.jsonl`. `**` never descends into a dot-directory,
so `discover_files()` globs that exact layout explicitly, and `session_label()` labels blocks with
the conversation id (the parent dir is always `logs`).

Records look like `{"type": "USER_INPUT", "source": "USER_EXPLICIT", "content":
"<USER_REQUEST>...</USER_REQUEST>...", "created_at": ...}`. Only `source == "USER_EXPLICIT"` is
kept; any other source value is harness traffic. The typed prompt is taken from inside the
`<USER_REQUEST>` envelope, which drops the harness-appended `<ADDITIONAL_METADATA>` block (local
time, active document). Content with no envelope is kept verbatim.

Antigravity only writes transcripts when interaction logging is enabled in its privacy settings
(README support matrix).

Evidence: `tests/test_antigravity_source.py`.

### Any folder

`--path <folder>` replaces the built-in roots with one directory and reads `**/*.jsonl` from it. The
same parsers apply; `source_kind()` returns `custom` unless the path happens to match a known
layout.

## Planned

Tracked in [issue #3](https://github.com/ohad6k/emulo/issues/3) and in
[ROADMAP.md](../ROADMAP.md#more-session-sources). Adapter code lands after the `emulo.py` rewrite,
so none of the below is readable today.

**Hermes Agent.** The storage spec is complete. Read its SQLite `state.db` read-only and WAL-aware,
resolve `HERMES_HOME` overrides and per-profile databases, and extract user messages only. The other
direction (installing a mined profile *into* Hermes and OpenClaw) already works and is documented in
[OPENCLAW_HERMES.md](OPENCLAW_HERMES.md); that guide is the reference for the runtime layout, not
duplicated here.

**OpenClaw.** Same issue. No storage spec written up in this repo yet, so its session layout is
unverified.

**Cursor and Windsurf.** Storage docs in progress per ROADMAP.md. Locations and formats unverified.

## How to add a source

An adapter has to provide four things:

1. **A root**, added to `SOURCES` in `emulo.py`, plus the same string in the `--source` choices in
   both argument parsers and in the `auto` root list.
2. **Discovery**, if the layout is not plain recursive `*.jsonl`. See
   `discover_opencode_sessions()` for a store that needs virtual per-session entries, and the
   Antigravity glob in `discover_files()` for a hidden directory.
3. **Extraction**, returning `[(date, text), ...]` of typed turns only, either as a branch in
   `user_messages()` or as its own helper. Harness traffic written into user-role records must be
   filtered, not mined. Add any new record marker to `USER_LINE_MARKERS`, which is the cheap
   line-level prefilter.
4. **Identity**, if the path shape is new: `source_kind()` needs a branch so session ids, counts,
   and labels attribute correctly, and `session_label()` may need one if the parent directory is not
   distinguishing.

Templates: copy `tests/test_opencode_source.py` for a SQLite or multi-file store, or
`tests/test_antigravity_source.py` for a jsonl transcript with envelopes. Both build a real fixture
tree in a temp directory, load `emulo.py` by path, and assert on `discover_files()` and
`user_messages()` output.

A PR adding a source should show:

- The tests, passing under `python -m unittest discover -s tests` (what CI runs, see
  `.github/workflows/tests.yml`).
- A real local run against a real install of that product: the product version, `--dry-run` output
  with the session and message counts, and confirmation that assistant text, tool output, and
  harness injections did not land in the corpus.
- The exact record shape you relied on, quoted from a real log with your own text removed.

No adapter is claimed as supported on a fixture alone. Mining verified live against a real install
is the bar the existing sources were held to.
