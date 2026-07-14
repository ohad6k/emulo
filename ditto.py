#!/usr/bin/env python3
"""
ditto - turn your own AI coding sessions into a model of how you think.

It reads your local session logs (Codex / Claude Code / Copilot CLI / Antigravity jsonl),
keeps ONLY the words you typed, redacts secrets + personal info, and writes one
clean corpus + chunks. You then point a coding agent at the chunks with
MINING_PROMPT.md to produce your `you.md`.

Extraction and redaction happen locally, and ditto.py makes no network calls.
Selected redacted text is processed by the model provider you choose. Stdlib only.

Usage:
    python ditto.py                     # auto-detect Codex + Claude + Copilot logs
    python ditto.py --dry-run           # preview counts without writing files
    python ditto.py --card              # render your profile card (after mining)
    python ditto.py --install you.md --target codex
    python ditto.py --source codex      # only ~/.codex/sessions
    python ditto.py --source copilot    # only ~/.copilot/session-state
    python ditto.py --source antigravity # only ~/.gemini/antigravity/brain
    python ditto.py --path ./logs       # a folder of jsonl you point at
    python ditto.py --chunks 20         # how many chunks to split into
    python ditto.py --no-redact         # DANGER: skip redaction (not recommended)
"""
import argparse, base64, glob, hashlib, json, os, re, shutil, sqlite3, stat, sys, tempfile, time, unicodedata, uuid

HOME = os.path.expanduser("~")
CODEX_HOME = os.path.expanduser(os.environ.get("CODEX_HOME", os.path.join(HOME, ".codex")))
OPENCODE_DATA = os.path.join(
    os.path.expanduser(os.environ.get("XDG_DATA_HOME", os.path.join(HOME, ".local", "share"))),
    "opencode",
)
SOURCES = {
    "codex":   [
        os.path.join(CODEX_HOME, "sessions"),
        os.path.join(CODEX_HOME, "archived_sessions"),
    ],
    "claude":  [os.path.join(HOME, ".claude", "projects")],
    "copilot": [os.path.join(HOME, ".copilot", "session-state")],
    "opencode": [OPENCODE_DATA],
    "antigravity": [os.path.join(HOME, ".gemini", "antigravity", "brain")],
}
# Separator between a real opencode.db path and a session id inside it. A
# discovered "file" for the SQLite store is one session, so counts, labels,
# and cache identity stay per-session like every other source.
OPENCODE_DB_SESSION_SEP = "::"
DITTO_START = "<!-- ditto profile:start -->"
DITTO_END = "<!-- ditto profile:end -->"

EXTRACTION_SCHEMA_VERSION = "2"
SEGMENT_SCHEMA_VERSION = "1"
REPORT_SCHEMA_VERSION = "2"
PROMPT_SCHEMA_VERSION = "2"
REDUCER_SCHEMA_VERSION = "2"
RECEIPT_SCHEMA_VERSION = "1"
SALIENCE_SCHEMA_VERSION = "1"
PACKET_SCHEMA_VERSION = "1"
SCOUT_REPORT_SCHEMA_VERSION = "3"
DOMAIN_DRAFT_SCHEMA_VERSION = "2"
MAX_SCOUT_REPORT_BYTES = 24_576

STAGE_CONFIGS = {
    "A": {"packets": 6, "packet_tokens": 50_000, "source_tokens": 300_000},
    "B": {"packets": 6, "packet_tokens": 50_000, "source_tokens": 300_000},
}

STARTER_CANDIDATES = (
    {"segments": 4, "segment_tokens": 25_000},
    {"segments": 6, "segment_tokens": 25_000},
    {"segments": 8, "segment_tokens": 25_000},
)
STARTER_MAX_SOURCE_TOKENS = 160_000
STARTER_MAX_MODEL_CALLS = 9
DEFAULT_CANDIDATE_INDEX = 0
QUALITY_DEFAULT_MODE = "full"
QUICK_PREVIEW_NOTICE = (
    "Quick preview creates a starter profile from selected history, not the full profile."
)
FULL_PROFILE_NOTICE = "Full-history quality default; approval is required before model work."
DEEP_SEGMENT_TOKENS = 20_000
MAX_REPORT_BYTES = 8_192
MAX_EVIDENCE_PER_REPORT = 12
MAX_QUOTE_CHARS = 200

# --- redaction: run BEFORE any of your text is written or seen by an agent ---

def _credential_repl(m):
    """Redact `password is hunter2` / `psk hunter2`, but not `password is wrong`.

    Only treat the trailing token as a secret if it looks like one: long, or
    containing a digit or a symbol. Plain short English words are left alone so
    prose about passwords survives.
    """
    value = m.group(2)
    if len(value) >= 12 or any(c.isdigit() for c in value) or not value.isalpha():
        return f"{m.group(1)}=[REDACTED]"
    return m.group(0)

REDACTIONS = [
    (re.compile(r"sk-[A-Za-z0-9]{20,}"),                 "[OPENAI_KEY]"),
    (re.compile(r"sk_live_[A-Za-z0-9]{20,}"),            "[STRIPE_KEY]"),
    (re.compile(r"whsec_[A-Za-z0-9]{20,}"),              "[WEBHOOK_SECRET]"),
    (re.compile(r"sbp_[A-Za-z0-9]{20,}"),                "[SUPABASE_TOKEN]"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),          "[GITHUB_TOKEN]"),
    (re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"), "[JWT]"),
    (re.compile(r"AKIA[0-9A-Z]{16}"),                    "[AWS_KEY]"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"),       "[SLACK_TOKEN]"),
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),         "[IP]"),
    # Phone: an explicit international +CC prefix, or a national trunk 0 plus a
    # valid area/mobile digit, with optional parenthesized area codes. Anchored
    # so it cannot eat dates (2026-06-14), versions (v0.8.0), part numbers
    # (n4500) or URL fragments, while trailing sentence punctuation still
    # matches ("call +972 52-123-4567."). Bare domestic formats with neither
    # marker (415-555-2671) are intentionally not matched: the old pattern
    # caught them only by the same over-matching that ate dates.
    (re.compile(r"(?<![\w.\-/])(?:\+\d{1,3}[\s\-]?(?:\(\d{1,4}\)[\s\-]?)?\d(?:[\s\-]?\d){6,10}"
                r"|\(?0[2-9]\d{0,2}\)?(?:[\s\-]?\d){6,9})(?![\w/]|[.\-]\d)"), "[PHONE]"),
    (re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*\S+"), r"\1=[REDACTED]"),
    # `password is hunter2`, `psk hunter2`, `wifi key hunter2` -- the bare and
    # `is` forms the [:=] rule above misses entirely. The pass- stem requires a
    # suffix so "boarding pass QF12345" stays untouched, and `pwd` is not a
    # keyword: in a coding corpus it is the shell command, and `pwd C:/Users/x`
    # would be eaten.
    (re.compile(r"(?i)\b(pass(?:word|wd|phrase)|psk|passkey|wifi\s+key)\b\s*(?:is\s+|=\s*|:\s*)?['\"]?([^\s'\",;]{6,})"),
     _credential_repl),
]

def redact(text):
    for pat, repl in REDACTIONS:
        text = pat.sub(repl, text)
    return text

def is_pasted_log(t):
    """Drop messages that are pasted stack traces / error dumps, not your prose."""
    lines = t.splitlines()
    if len(lines) < 4:
        return False
    hits = sum(1 for l in lines if re.match(r"\s+at ", l) or "Exception" in l
               or "Traceback" in l or re.search(r"\.(java|py|ts|js|kt):\d", l)
               or re.match(r'\s*File "', l))
    return hits / max(len(lines), 1) > 0.25

def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def source_kind(path):
    normalized = os.path.normcase(os.path.abspath(path))
    if f"{os.sep}.codex{os.sep}" in normalized:
        return "codex"
    if f"{os.sep}.claude{os.sep}" in normalized:
        return "claude"
    if f"{os.sep}.copilot{os.sep}" in normalized:
        return "copilot"
    if f"{os.sep}antigravity{os.sep}" in normalized:
        return "antigravity"
    if "opencode.db" in normalized or f"{os.sep}opencode{os.sep}" in normalized:
        return "opencode"
    return "custom"

def stable_session_id(path):
    source = source_kind(path)
    normalized = os.path.normcase(os.path.abspath(path))
    return sha256_text(f"{source}:{normalized}")[:16]

INJECTED_CONTEXT_PREFIXES = (
    "# AGENTS.md instructions",
    "# CLAUDE.md instructions",
    "<environment_context",
    "<in-app-browser-context",
    "<permissions instructions",
    "<recommended_plugins",
    "<summary>",
    "<command-name",
    "<command-message",
    "<local-command-stdout",
    "<task-notification",
    "<launch-selected-element",
    "[Request interrupted",
)

# Codex writes harness traffic into role:user records, wrapped in control
# envelopes with matching closing tags. Strip complete envelopes and keep any
# human text around them; a message that was only envelopes drops out. Bare
# <skill> is deliberately NOT listed: it appears attribute-less and rarely, and
# is indistinguishable from a human pasting a <skill> XML block.
CODEX_CONTROL_ENVELOPE = re.compile(
    r"<(?P<tag>subagent_notification|codex_internal_context|codex_delegation|"
    r"turn_aborted|heartbeat)"
    r"(?:\s[^>]*)?>.*?</(?P=tag)>",
    re.DOTALL,
)
# Image attachments split across records as `<image name=".." path="..">` and a
# following `</image>`; the attributes embed local file paths. Strip the
# markers, keep the human text around them. ('>' is illegal in Windows file
# names, so [^>]* is safe for the attribute span.)
CODEX_IMAGE_MARKER = re.compile(r"</?image\b[^>]*>?")
# Antigravity (Google) wraps the typed prompt in a <USER_REQUEST> envelope and
# appends a harness-injected <ADDITIONAL_METADATA> block (local time, active
# document). Keep only the text inside the envelope; the metadata drops out.
ANTIGRAVITY_USER_REQUEST = re.compile(
    r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", re.DOTALL
)
USER_LINE_MARKERS = (
    '"role":"user"',
    '"role": "user"',
    '"type":"user"',
    '"type": "user"',
    '"type":"user.message"',
    '"type": "user.message"',
    '"type":"USER_INPUT"',
    '"type": "USER_INPUT"',
)

def is_injected_context(text):
    stripped = text.lstrip()
    return any(stripped.startswith(prefix) for prefix in INJECTED_CONTEXT_PREFIXES)

def _opencode_ts(ms):
    try:
        return time.strftime("%Y-%m-%d", time.gmtime(int(ms) / 1000))
    except Exception:
        return ""

def _opencode_keep(out, ts, text):
    text = (text or "").strip()
    if not text or is_injected_context(text) or is_pasted_log(text):
        return
    out.append((ts, text))

def opencode_db_messages(db_path, session_id):
    """One OpenCode session from the current SQLite store, read-only.

    Human text = part rows of type "text" whose parent message row carries
    role "user". Synthetic parts are harness-injected, never typed.
    """
    out = []
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            rows = con.execute(
                "select m.time_created, m.data, p.data from message m "
                "join part p on p.message_id = m.id "
                "where m.session_id = ? order by m.time_created, m.id, p.time_created, p.id",
                (session_id,),
            ).fetchall()
        finally:
            con.close()
    except Exception:
        return out
    for ts_ms, message_data, part_data in rows:
        try:
            message = json.loads(message_data)
            part = json.loads(part_data)
        except Exception:
            continue
        if message.get("role") != "user":
            continue
        if part.get("type") != "text" or part.get("synthetic"):
            continue
        _opencode_keep(out, _opencode_ts(ts_ms), part.get("text"))
    return out

def opencode_storage_messages(session_json_path):
    """One OpenCode session from the legacy JSON file layout:
    storage/session/{project}/{session}.json with sibling message/ and part/
    directories keyed by session and message ids."""
    out = []
    path = os.path.abspath(session_json_path)
    storage = os.path.dirname(path)
    while os.path.basename(storage) != "storage":
        parent = os.path.dirname(storage)
        if parent == storage:
            return out
        storage = parent
    session_id = os.path.splitext(os.path.basename(path))[0]
    for message_file in sorted(glob.glob(os.path.join(storage, "message", session_id, "*.json"))):
        try:
            with open(message_file, "r", encoding="utf-8", errors="replace") as fh:
                message = json.load(fh)
        except Exception:
            continue
        if message.get("role") != "user":
            continue
        message_id = message.get("id") or os.path.splitext(os.path.basename(message_file))[0]
        ts = _opencode_ts((message.get("time") or {}).get("created"))
        for part_file in sorted(glob.glob(os.path.join(storage, "part", message_id, "*.json"))):
            try:
                with open(part_file, "r", encoding="utf-8", errors="replace") as fh:
                    part = json.load(fh)
            except Exception:
                continue
            if part.get("type") != "text" or part.get("synthetic"):
                continue
            _opencode_keep(out, ts, part.get("text"))
    return out

def discover_opencode_sessions(root):
    """OpenCode entries under a data root: one virtual path per SQLite
    session, plus legacy per-session JSON files."""
    entries = []
    db_path = os.path.join(root, "opencode.db")
    if os.path.isfile(db_path):
        try:
            con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            try:
                rows = con.execute(
                    "select distinct session_id from message"
                ).fetchall()
            finally:
                con.close()
            entries += [f"{db_path}{OPENCODE_DB_SESSION_SEP}{sid}" for (sid,) in rows if sid]
        except Exception:
            pass
    entries += glob.glob(os.path.join(root, "storage", "session", "**", "*.json"), recursive=True)
    return entries

def is_human_turn(record):
    """Claude Code writes harness traffic into role:user records; keep only the
    turns a human actually typed.

    Claude Desktop stamps promptSource="sdk" on prompts the human typed (it
    drives sessions through the Agent SDK), so promptSource alone never
    disqualifies a record — only a headless sdk-cli entrypoint does. Origin
    kind, when present, is authoritative.
    """
    if record.get("isMeta") or record.get("isSidechain"):
        return False
    if "toolUseResult" in record:
        return False
    if record.get("isCompactSummary"):
        return False
    origin = record.get("origin")
    if isinstance(origin, dict):
        return origin.get("kind") == "human"
    if record.get("promptSource") == "sdk" and record.get("entrypoint") == "sdk-cli":
        return False
    return True

def user_messages(path):
    if OPENCODE_DB_SESSION_SEP in path:
        db_path, _, session_id = path.rpartition(OPENCODE_DB_SESSION_SEP)
        if db_path.endswith("opencode.db"):
            return opencode_db_messages(db_path, session_id)
    # Route by layout, not by folder name: .json entries only enter discovery
    # through the storage/session glob, so an exported legacy store under any
    # --path still mines.
    if path.endswith(".json") and f"{os.sep}storage{os.sep}session{os.sep}" in os.path.normpath(os.path.abspath(path)):
        return opencode_storage_messages(path)
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not any(marker in line for marker in USER_LINE_MARKERS):
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                codex_record = o.get("type") == "response_item"
                if o.get("type") == "user" and not is_human_turn(o):
                    continue
                # Antigravity: {type:'USER_INPUT', source:'USER_EXPLICIT',
                # content:'<USER_REQUEST>...</USER_REQUEST>...', created_at}.
                # Any other source value is harness traffic, never typed.
                if o.get("type") == "USER_INPUT":
                    if o.get("source") != "USER_EXPLICIT":
                        continue
                    content = o.get("content", "") or ""
                    wrapped = ANTIGRAVITY_USER_REQUEST.findall(content)
                    texts = wrapped if wrapped else [content]
                # Copilot CLI: {type:'user.message', data:{content, source}, timestamp}
                elif o.get("type") == "user.message":
                    data = o.get("data", {})
                    if data.get("source") == "system":   # steering/system injections
                        continue
                    texts = [data.get("content", "")]
                else:
                    # Codex: {payload:{type:'message',role:'user',content:[{text}]}}
                    # Claude: {type:'user',message:{role:'user',content:'...'|[...]}}
                    p = o.get("payload", o)
                    msg = p.get("message", p)
                    if not ((p.get("type") == "message" or o.get("type") == "user") and
                            (p.get("role") == "user" or msg.get("role") == "user")):
                        continue
                    content = msg.get("content", p.get("content", ""))
                    if isinstance(content, str):
                        texts = [content]
                    elif isinstance(content, list):
                        texts = [c.get("text", "") for c in content if isinstance(c, dict)]
                    else:
                        texts = []
                for t in texts:
                    t = (t or "").strip()
                    if codex_record and t:
                        t = CODEX_CONTROL_ENVELOPE.sub("", t)
                        t = CODEX_IMAGE_MARKER.sub("", t).strip()
                    if not t or is_injected_context(t):
                        continue
                    if is_pasted_log(t):
                        continue
                    ts = (o.get("timestamp") or o.get("created_at") or "")[:10]
                    out.append((ts, t))
    except Exception:
        pass
    return out

def discover_files(roots):
    files = []
    opencode_entries = []
    for r in roots:
        files += glob.glob(os.path.join(r, "**", "*.jsonl"), recursive=True)
        # Antigravity hides transcripts under a dot-directory
        # (brain/<id>/.system_generated/logs/), which "**" never descends
        # into. Glob that exact layout explicitly.
        files += glob.glob(
            os.path.join(r, "*", ".system_generated", "logs", "*.jsonl")
        )
        opencode_entries += discover_opencode_sessions(r)
    # Claude Code stores agent-to-agent transcripts under a `subagents/` path
    # component; every role:user record in them is isSidechain. Skip the files
    # outright (component match, so a `my-subagents-notes/` directory survives).
    files = [f for f in files
             if "subagents" not in os.path.normpath(f).split(os.sep)]
    return sorted(set(files) | set(opencode_entries))

def session_label(path):
    """Label a session block by parent dir + filename.

    Copilot logs are all named events.jsonl under a per-session directory, so
    the bare filename collapses every block header to the same string. Prefix
    the parent directory (the session id for Copilot, the project for Claude)
    to keep sessions distinguishable in the corpus.

    Antigravity buries every transcript at
    brain/<conversation-id>/.system_generated/logs/transcript.jsonl, so the
    parent dir is always "logs"; label with the conversation id instead.
    """
    parts = os.path.normpath(os.path.abspath(path)).split(os.sep)
    if ".system_generated" in parts:
        idx = parts.index(".system_generated")
        if idx > 0:
            return f"{parts[idx - 1]}/{os.path.basename(path)}"
    parent = os.path.basename(os.path.dirname(path))
    name = os.path.basename(path)
    return f"{parent}/{name}" if parent else name

# Messages at/above this length that repeat verbatim are re-pasted specs, logs, or
# injected AGENTS.md/CLAUDE.md boilerplate - not new signal. Collapse them to the first
# copy. Short messages ("yes", "push it live") are kept: their repetition IS the signal.
DEDUPE_MIN_LEN = 200

def mine_files(files, no_redact=False, dedupe=True):
    sessions = msgs = chars = redactions = duplicates = 0
    blocks, records = [], []
    first_date = last_date = ""
    seen_long = set()
    for f in files:
        ums = user_messages(f)
        if not ums:
            continue
        buf = []
        kept_messages = []
        kept_dates = []
        for ts, t in ums:
            if dedupe and len(t) >= DEDUPE_MIN_LEN:
                if t in seen_long:
                    duplicates += 1
                    continue
                seen_long.add(t)
            if not no_redact:
                before = t
                t = redact(t)
                if t != before:
                    redactions += 1
            message_date = ts if re.fullmatch(r"\d{4}-\d{2}-\d{2}", ts) else "undated"
            if message_date != "undated":
                kept_dates.append(message_date)
                if not first_date or message_date < first_date:
                    first_date = message_date
                if message_date > last_date:
                    last_date = message_date
            buf.append(f"[{message_date}]\n{t}")
            kept_messages.append({
                "date": message_date,
                "text": t,
                "ordinal": len(kept_messages),
            })
            msgs += 1
            chars += len(t)
        if not buf:            # every message was a duplicate of an earlier session
            continue
        session_id = stable_session_id(f)
        source = source_kind(f)
        text = "\n".join([f"===== session:{session_id} source:{source} ====="] + buf)
        record = {
            "session_id": session_id,
            "source": source,
            "first_date": min(kept_dates) if kept_dates else "undated",
            "last_date": max(kept_dates) if kept_dates else "undated",
            "tokens": max(1, sum(len(item) for item in buf) // 4),
            "text": text,
            "content_hash": sha256_text(text),
            "messages": kept_messages,
        }
        sessions += 1
        records.append(record)
        blocks.append(text)
    return {
        "sessions": sessions,
        "messages": msgs,
        "chars": chars,
        "redactions": redactions,
        "duplicates": duplicates,
        "blocks": blocks,
        "records": records,
        "first_date": first_date,
        "last_date": last_date,
    }

def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def build_receipt_ledger(records):
    receipts = []
    for record in records:
        for message in record.get("messages", []):
            text = message["text"]
            content_hash = sha256_text(text)
            identity = {
                "schema_version": RECEIPT_SCHEMA_VERSION,
                "session_id": record["session_id"],
                "date": message["date"],
                "ordinal": message["ordinal"],
                "content_hash": content_hash,
            }
            receipts.append({
                "schema_version": RECEIPT_SCHEMA_VERSION,
                "receipt_id": "rcpt-" + sha256_text(canonical_json(identity))[:20],
                "session_id": record["session_id"],
                "source": record["source"],
                "date": message["date"],
                "ordinal": message["ordinal"],
                "text": text,
                "tokens": max(1, len(text) // 4),
                "content_hash": content_hash,
            })
    return sorted(
        receipts,
        key=lambda item: (
            item["source"],
            item["date"],
            item["session_id"],
            item["ordinal"],
            item["receipt_id"],
        ),
    )

SALIENCE_MARKERS = {
    "directive": ("never", "always", "do not", "don't", "must", "make sure", "need to", "remember", "אל ", "תמיד", "חייב"),
    "correction": ("wrong", "not what", "stop", "instead", "fix this", "you missed", "זה לא", "לא נכון"),
    "rejection": ("hate", "reject", "no ", "don't", "do not", "fake", "bad", "שונא", "אל "),
    "preference": ("prefer", "i want", "i like", "i love", "should", "style", "taste", "voice", "אני רוצה", "מעדיף"),
    "verification": ("done", "live", "verify", "verified", "production", "test", "proof", "בדיקה", "מוכן"),
}
DOMAIN_MARKERS = {
    "work": ("done", "verify", "test", "production", "release", "deploy", "plan", "debug", "commit", "proof", "workflow"),
    "design": ("ui", "ux", "design", "visual", "layout", "screenshot", "color", "pixel", "animation", "premium", "gradient", "icon", "figma", "css", "עיצוב", "ממשק", "צבע"),
    "write": ("write", "copy", "tweet", "reddit", "marketing", "title", "tone", "voice", "post", "reply", "launch", "lowercase", "em dash", "wording", "כתיבה", "פוסט", "שיווק"),
}
SALIENCE_WEIGHTS = {"directive": 24, "correction": 20, "rejection": 18, "preference": 12, "verification": 10}

def normalized_salience_tokens(text):
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return re.findall(r"\w+", normalized, flags=re.UNICODE)

def score_receipts(receipts):
    normalized = {}
    sessions_by_fingerprint = {}
    for receipt in receipts:
        tokens = normalized_salience_tokens(receipt["text"])
        fingerprint = " ".join(tokens)
        normalized[receipt["receipt_id"]] = (fingerprint, tokens)
        sessions_by_fingerprint.setdefault(fingerprint, set()).add(receipt["session_id"])

    scored = []
    for receipt in receipts:
        item = dict(receipt)
        fingerprint, tokens = normalized[item["receipt_id"]]
        searchable = f" {fingerprint} "
        families = set()
        salience = 1
        for family, markers in SALIENCE_MARKERS.items():
            if any(marker in searchable for marker in markers):
                families.add(family)
                salience += SALIENCE_WEIGHTS[family]
        recurrence_sessions = len(sessions_by_fingerprint.get(fingerprint, ()))
        if recurrence_sessions > 1:
            families.add("recurrence")
            salience += min(24, (recurrence_sessions - 1) * 6)
        if not families:
            families.add("exploration")

        domain_hints = set(item.get("domain_hints", []))
        for domain, markers in DOMAIN_MARKERS.items():
            if any(marker in searchable for marker in markers):
                domain_hints.add(domain)
        if not domain_hints:
            domain_hints.add("work")
        item.update({
            "salience_schema_version": SALIENCE_SCHEMA_VERSION,
            "salience": salience,
            "signal_families": sorted(families),
            "domain_hints": sorted(domain_hints),
            "recurrence_sessions": recurrence_sessions,
            "normalized_token_count": len(tokens),
        })
        item["salience_hash"] = sha256_text(canonical_json({
            "schema_version": SALIENCE_SCHEMA_VERSION,
            "receipt_id": item["receipt_id"],
            "salience": salience,
            "signal_families": item["signal_families"],
            "domain_hints": item["domain_hints"],
            "recurrence_sessions": recurrence_sessions,
        }))
        scored.append(item)
    return sorted(scored, key=lambda value: value["receipt_id"])

def receipt_quarter(receipt):
    match = re.match(r"(\d{4})-(\d{2})", receipt.get("date", ""))
    if not match:
        return "unknown"
    year, month = match.groups()
    return f"{year}-Q{((int(month) - 1) // 3) + 1}"

def select_salience_stage(receipts, stage, excluded_receipt_ids=None):
    if stage not in STAGE_CONFIGS:
        raise ValueError(f"unknown adaptive stage: {stage}")
    config = STAGE_CONFIGS[stage]
    excluded = set(excluded_receipt_ids or [])
    eligible = [
        item for item in receipts
        if item["receipt_id"] not in excluded and item["tokens"] <= config["packet_tokens"]
    ]
    lanes = {}
    for item in eligible:
        domains = item.get("domain_hints") or ["work"]
        families = item.get("signal_families") or ["exploration"]
        for domain in domains:
            for family in families:
                key = (domain, item.get("source", "unknown"), receipt_quarter(item), family)
                lanes.setdefault(key, []).append(item)
    for queue in lanes.values():
        queue.sort(key=lambda item: (-item.get("salience", 0), item["receipt_id"]))

    selected = []
    selected_ids = set()
    selected_tokens = 0
    lane_keys = sorted(lanes)
    while True:
        progressed = False
        for key in lane_keys:
            queue = lanes[key]
            while queue and queue[0]["receipt_id"] in selected_ids:
                queue.pop(0)
            if not queue:
                continue
            item = queue.pop(0)
            if selected_tokens + item["tokens"] > config["source_tokens"]:
                continue
            selected.append(item)
            selected_ids.add(item["receipt_id"])
            selected_tokens += item["tokens"]
            progressed = True
        if not progressed:
            break

    for item in sorted(eligible, key=lambda value: (-value.get("salience", 0), value["receipt_id"])):
        if item["receipt_id"] in selected_ids:
            continue
        if selected_tokens + item["tokens"] > config["source_tokens"]:
            continue
        selected.append(item)
        selected_ids.add(item["receipt_id"])
        selected_tokens += item["tokens"]
    return selected

def pack_selected_receipts(receipts, packet_limit, packet_token_limit):
    groups = []
    current = []
    current_tokens = 0
    for receipt in receipts:
        if receipt["tokens"] > packet_token_limit:
            raise ValueError(f"receipt exceeds packet token limit: {receipt['receipt_id']}")
        if current and current_tokens + receipt["tokens"] > packet_token_limit:
            groups.append(current)
            current = []
            current_tokens = 0
        if len(groups) >= packet_limit:
            break
        current.append(receipt)
        current_tokens += receipt["tokens"]
    if current and len(groups) < packet_limit:
        groups.append(current)

    packets = []
    for group in groups:
        receipt_ids = [item["receipt_id"] for item in group]
        domain_counts = {
            domain: sum(domain in item.get("domain_hints", []) for item in group)
            for domain in ("work", "design", "write")
        }
        signal_counts = {}
        for item in group:
            for family in item.get("signal_families", ["exploration"]):
                signal_counts[family] = signal_counts.get(family, 0) + 1
        identity = {
            "schema_version": PACKET_SCHEMA_VERSION,
            "receipt_ids": receipt_ids,
            "content_hashes": [item["content_hash"] for item in group],
        }
        packets.append({
            "schema_version": PACKET_SCHEMA_VERSION,
            "packet_hash": sha256_text(canonical_json(identity)),
            "source_tokens": sum(item["tokens"] for item in group),
            "receipt_ids": receipt_ids,
            "receipts": group,
            "domain_counts": domain_counts,
            "signal_counts": dict(sorted(signal_counts.items())),
            "first_date": min(item["date"] for item in group),
            "last_date": max(item["date"] for item in group),
            "sources": sorted({item["source"] for item in group}),
        })
    return packets

def segment_hash(records, target_tokens):
    identity = {
        "schema_version": SEGMENT_SCHEMA_VERSION,
        "extraction_schema_version": EXTRACTION_SCHEMA_VERSION,
        "target_tokens": target_tokens,
        "sessions": [
            {"session_id": record["session_id"], "content_hash": record["content_hash"]}
            for record in records
        ],
    }
    return sha256_text(canonical_json(identity))

def pack_records(records, target_tokens):
    packed, current, current_tokens = [], [], 0
    for record in sorted(records, key=lambda item: (item["source"], item["first_date"], item["session_id"])):
        source_changed = current and current[0]["source"] != record["source"]
        target_exceeded = current and current_tokens + record["tokens"] > target_tokens
        if source_changed or target_exceeded:
            packed.append(current)
            current, current_tokens = [], 0
        current.append(record)
        current_tokens += record["tokens"]
    if current:
        packed.append(current)
    return packed

def seal_records(records, target_tokens):
    sealed = []
    for group in pack_records(records, target_tokens):
        text = "\n".join(record["text"] for record in group)
        dated_first = [record["first_date"] for record in group if record["first_date"] != "undated"]
        dated_last = [record["last_date"] for record in group if record["last_date"] != "undated"]
        source_tokens = sum(record["tokens"] for record in group)
        sealed.append({
            "segment_hash": segment_hash(group, target_tokens),
            "active": True,
            "source": group[0]["source"],
            "first_date": min(dated_first) if dated_first else "undated",
            "last_date": max(dated_last) if dated_last else "undated",
            "source_tokens": source_tokens,
            "text_hash": sha256_text(text),
            "session_versions": [
                {"session_id": record["session_id"], "content_hash": record["content_hash"]}
                for record in group
            ],
            "oversize": len(group) == 1 and source_tokens > target_tokens,
        })
    return sealed

def segment_text_for_metadata(segment, records_by_id):
    records = []
    for version in segment["session_versions"]:
        record = records_by_id.get(version["session_id"])
        if not record or record["content_hash"] != version["content_hash"]:
            raise ValueError("segment metadata references missing session content")
        records.append(record)
    text = "\n".join(record["text"] for record in records)
    if sha256_text(text) != segment["text_hash"]:
        raise ValueError("segment text hash mismatch")
    return text

def segment_file_path(ditto_home, segment_hash_value):
    return os.path.join(
        private_paths(ditto_home)["segments"],
        SEGMENT_SCHEMA_VERSION,
        segment_hash_value + ".txt",
    )

def ensure_segment_file(segment, records_by_id, ditto_home, write=True):
    expected = segment_text_for_metadata(segment, records_by_id)
    path = segment_file_path(ditto_home, segment["segment_hash"])
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8", errors="strict", newline="") as handle:
                existing = handle.read()
        except (OSError, UnicodeError):
            existing = None
        if existing is not None and sha256_text(existing) == segment["text_hash"]:
            return path
        if not write:
            return path
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        quarantine = path + ".corrupt-" + stamp
        if os.path.exists(quarantine):
            quarantine += "-" + uuid.uuid4().hex[:8]
        os.replace(path, quarantine)
    if write:
        atomic_write_text(path, expected)
    return path

def sync_segments(records, ditto_home, target_tokens, write=True):
    ditto_home = resolve_ditto_home(ditto_home)
    index_path = os.path.join(
        private_paths(ditto_home)["segment_indexes"],
        f"v{SEGMENT_SCHEMA_VERSION}-{target_tokens}.json",
    )
    index = None
    if os.path.isfile(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as handle:
                candidate = json.load(handle)
            if (
                candidate.get("schema_version") == SEGMENT_SCHEMA_VERSION
                and candidate.get("extraction_schema_version") == EXTRACTION_SCHEMA_VERSION
                and candidate.get("target_tokens") == target_tokens
                and isinstance(candidate.get("segments"), list)
            ):
                index = candidate
        except (OSError, ValueError, TypeError):
            index = None
    if index is None:
        index = {
            "schema_version": SEGMENT_SCHEMA_VERSION,
            "extraction_schema_version": EXTRACTION_SCHEMA_VERSION,
            "target_tokens": target_tokens,
            "sessions": {},
            "segments": [],
        }

    records_by_id = {record["session_id"]: record for record in records}
    current_sessions = {
        session_id: record["content_hash"] for session_id, record in records_by_id.items()
    }
    represented = set()
    rebuild_ids = set()
    segments = []
    for original in index["segments"]:
        segment = dict(original)
        versions = segment.get("session_versions", [])
        affected = bool(segment.get("active")) and any(
            current_sessions.get(item.get("session_id")) != item.get("content_hash")
            for item in versions
        )
        if affected:
            segment["active"] = False
            rebuild_ids.update(
                item["session_id"] for item in versions if item.get("session_id") in records_by_id
            )
        elif segment.get("active"):
            represented.update(item["session_id"] for item in versions)
        segments.append(segment)

    rebuild_ids.update(set(records_by_id) - represented)
    rebuild_records = [records_by_id[session_id] for session_id in rebuild_ids]
    for sealed in seal_records(rebuild_records, target_tokens):
        existing = next(
            (item for item in segments if item.get("segment_hash") == sealed["segment_hash"]),
            None,
        )
        if existing is None:
            segments.append(sealed)
        else:
            existing.update(sealed)

    result = {
        "schema_version": SEGMENT_SCHEMA_VERSION,
        "extraction_schema_version": EXTRACTION_SCHEMA_VERSION,
        "target_tokens": target_tokens,
        "sessions": current_sessions,
        "segments": segments,
    }
    for segment in result["segments"]:
        if segment.get("active"):
            ensure_segment_file(segment, records_by_id, ditto_home, write=write)
    if write:
        atomic_write_text(index_path, canonical_json(result) + "\n")
    return result

def temporal_queue(items):
    ordered = sorted(items, key=lambda item: (item["first_date"], item["segment_hash"]))
    out = []
    left, right = 0, len(ordered) - 1
    while left <= right:
        out.append(ordered[left])
        left += 1
        if left <= right:
            out.append(ordered[right])
            right -= 1
    return out

def select_segments(segments, count, max_tokens):
    grouped = {}
    for segment in segments:
        if segment.get("active") and not segment.get("oversize"):
            grouped.setdefault(segment["source"], []).append(segment)
    queues = {source: temporal_queue(items) for source, items in grouped.items()}
    selected, total = [], 0
    while len(selected) < count:
        progressed = False
        for source in sorted(queues):
            queue = queues[source]
            while queue:
                candidate = queue.pop(0)
                if total + candidate["source_tokens"] <= max_tokens:
                    selected.append(candidate)
                    total += candidate["source_tokens"]
                    progressed = True
                    break
            if len(selected) >= count:
                break
        if not progressed:
            break
    return sorted(selected, key=lambda item: (item["source"], item["first_date"], item["segment_hash"]))

def candidate_config(index):
    if index not in range(len(STARTER_CANDIDATES)):
        raise ValueError("candidate must be 0, 1, or 2")
    return STARTER_CANDIDATES[index]

def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()

def planned_call_counts(segment_hashes, report_hits, reduction_cache_hit):
    missing = len(set(segment_hashes) - set(report_hits))
    return missing, 0 if missing == 0 and reduction_cache_hit else 1

def compute_report_set_hash(report_paths):
    identity = {
        "prompt_schema_version": PROMPT_SCHEMA_VERSION,
        "reports": [
            {"path": os.path.basename(path), "sha256": sha256_file(path)}
            for path in sorted(report_paths)
        ],
    }
    return sha256_text(canonical_json(identity))

def report_cache_path(ditto_home, segment_hash_value):
    return os.path.join(
        private_paths(ditto_home)["reports"],
        PROMPT_SCHEMA_VERSION,
        segment_hash_value + ".json",
    )

VALID_DOMAINS = {"work", "design", "write"}
VALID_EVIDENCE_KINDS = {"inferred", "explicit"}
VALID_REGISTERS = {"casual", "professional", "shared"}
REGISTER_SECTIONS = (
    ("shared", "## Voice laws"),
    ("casual", "## Casual register"),
    ("professional", "## Professional register"),
)
GENERIC_RULES = {
    "be helpful",
    "be concise",
    "communicate clearly",
    "follow best practices",
    "write clean code",
    "write good code",
}
DOMAIN_FILES = {
    "work": ("you.md", "ditto-work-profile"),
    "design": ("you-designer.md", "ditto-design-profile"),
    "write": ("you-writer.md", "ditto-write-profile"),
}
REQUIRED_PACK_FILES = {"appendix.md", "card.json", "draft-manifest.json"}
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{value}" for value in range(1, 10)),
    *(f"LPT{value}" for value in range(1, 10)),
}

def normalized_rule_text(value):
    return re.sub(r"[^a-z0-9 ]+", "", value.lower()).strip()

def validate_register(domain, register, subject):
    if domain == "write":
        if register not in VALID_REGISTERS:
            raise ValueError(f"write {subject} requires a casual, professional, or shared register")
    elif register is not None:
        raise ValueError(f"register is only valid on write {subject}")

def validate_rule(rule, evidence_by_id, require_cross_strata, domain):
    text = rule.get("text", "").strip()
    implication = rule.get("implication", "").strip()
    if normalized_rule_text(text) in GENERIC_RULES or normalized_rule_text(implication) in GENERIC_RULES:
        raise ValueError("generic rule is not installable evidence")
    if len(text.split()) < 3 or len(implication.split()) < 4:
        raise ValueError("rule requires a specific instruction and operational implication")
    ids = rule.get("evidence_ids", [])
    if not ids or any(evidence_id not in evidence_by_id for evidence_id in ids):
        raise ValueError("rule references missing evidence")
    evidence = [evidence_by_id[evidence_id] for evidence_id in ids]
    register = rule.get("register")
    validate_register(domain, register, "rules")
    if domain == "write":
        evidence_registers = {item.get("register") for item in evidence}
        if None in evidence_registers:
            raise ValueError("write rule requires write evidence that carries a register")
        expected = next(iter(evidence_registers)) if len(evidence_registers) == 1 else "shared"
        if register != expected:
            raise ValueError("write rule register must match its evidence registers")
    sessions = set().union(*(item["sessions"] for item in evidence))
    strata = set().union(*(item["strata"] for item in evidence))
    quote_count = sum(item["quote_count"] for item in evidence)
    contradictions = [value for item in evidence for value in item.get("contradictions", [])]
    if contradictions:
        raise ValueError("rule has an unresolved contradiction")
    if rule.get("kind") == "inferred":
        if any(item["kind"] != "inferred" for item in evidence) or len(sessions) < 2 or quote_count < 2:
            raise ValueError("inferred rule requires two distinct sessions")
        if require_cross_strata and len(strata) < 2:
            raise ValueError("inferred rule requires two source/time strata")
    elif rule.get("kind") == "explicit":
        if (
            any(item["kind"] != "explicit" for item in evidence)
            or quote_count < 1
            or rule.get("confidence") != "low-frequency"
        ):
            raise ValueError("explicit rule requires low-frequency label and no contradiction")
    else:
        raise ValueError("rule kind must be inferred or explicit")

def receipt_stratum(source, date):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date or ""):
        return f"{source}:undated"
    quarter = (int(date[5:7]) - 1) // 3 + 1
    return f"{source}:{date[:4]}-Q{quarter}"

def flatten_report_evidence(reports):
    flattened = {}
    for report in reports:
        sources = report["coverage"]["sources"]
        source = sources[0]
        for item in report["evidence"]:
            evidence_id = item["evidence_id"]
            if evidence_id in flattened:
                raise ValueError("duplicate evidence id across reports")
            quotes = item["quotes"]
            flattened[evidence_id] = {
                "kind": item["kind"],
                "sessions": {receipt["session_id"] for receipt in quotes},
                "strata": {receipt_stratum(source, receipt["date"]) for receipt in quotes},
                "quote_count": len(quotes),
                "quotes": quotes,
                "contradictions": item.get("contradictions", []),
            }
            if item.get("register") is not None:
                flattened[evidence_id]["register"] = item["register"]
    return flattened

def json_safe_evidence(value):
    if isinstance(value, dict):
        return {key: json_safe_evidence(item) for key, item in sorted(value.items())}
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, list):
        return [json_safe_evidence(item) for item in value]
    return value

def compute_domain_evidence_hash(domain, evidence_by_id):
    selected = {
        evidence_id: item for evidence_id, item in evidence_by_id.items()
        if item.get("domain", domain) == domain
    }
    return sha256_text(canonical_json({
        "schema_version": DOMAIN_DRAFT_SCHEMA_VERSION,
        "domain": domain,
        "evidence": json_safe_evidence(selected),
    }))

def validate_domain_draft(draft, domain, evidence_by_id, run_plan):
    if domain not in VALID_DOMAINS or draft.get("domain") != domain:
        raise ValueError("domain draft name mismatch")
    if draft.get("schema_version") != DOMAIN_DRAFT_SCHEMA_VERSION:
        raise ValueError("unsupported domain draft schema")
    if draft.get("evidence_set_hash") != compute_domain_evidence_hash(domain, evidence_by_id):
        raise ValueError("domain draft evidence set hash mismatch")
    status = draft.get("status")
    if status == "inactive":
        if domain == "work":
            raise ValueError("work domain must remain active")
        if draft.get("deepen_instruction") != f"run ditto and deepen {domain}":
            raise ValueError("inactive domain requires exact deepen instruction")
        if draft.get("rules"):
            raise ValueError("inactive domain cannot install rules")
        return draft
    if status != "active":
        raise ValueError("domain draft status must be active or inactive")
    rules = draft.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError("active domain draft requires rules")
    discarded = draft.get("discarded")
    if not isinstance(discarded, list):
        raise ValueError("domain draft discarded conflicts must be a list")
    for rule in rules:
        ids = rule.get("evidence_ids", [])
        if any(
            evidence_id not in evidence_by_id
            or evidence_by_id[evidence_id].get("domain", domain) != domain
            for evidence_id in ids
        ):
            raise ValueError(f"rule must reference only {domain} evidence")
        selected = [evidence_by_id[evidence_id] for evidence_id in ids]
        evidence_scopes = {item.get("scope", "universal") for item in selected}
        if "contextual" in evidence_scopes and rule.get("scope") != "contextual":
            raise ValueError("rule scope cannot broaden contextual evidence")
        if rule.get("scope") == "contextual" and not rule.get("context", "").strip():
            raise ValueError("contextual rule requires context")
        validate_rule(rule, evidence_by_id, require_cross_strata=run_plan.get("adequate_strata", True), domain=domain)
    coverage = draft.get("coverage", {})
    if set(coverage) != {"evidence_items", "distinct_sessions", "strata", "unresolved_contradictions"}:
        raise ValueError("domain draft coverage is incomplete")
    if coverage.get("unresolved_contradictions", 0):
        raise ValueError("domain draft has unresolved contradictions")
    return draft

def domain_draft_cache_path(ditto_home, domain, evidence_set_hash):
    if domain not in VALID_DOMAINS or not re.fullmatch(r"[a-f0-9]{64}", evidence_set_hash or ""):
        raise ValueError("invalid domain draft cache identity")
    return safe_private_child(
        ditto_home, "cache", "domain-drafts", DOMAIN_DRAFT_SCHEMA_VERSION,
        domain, evidence_set_hash + ".json",
    )

def store_domain_draft(draft, domain, evidence_by_id, run_plan, ditto_home):
    validate_domain_draft(draft, domain, evidence_by_id, run_plan)
    path = domain_draft_cache_path(ditto_home, domain, draft["evidence_set_hash"])
    atomic_write_text(path, canonical_json(draft) + "\n")
    return path

def is_link_or_reparse(path):
    info = os.lstat(path)
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return os.path.islink(path) or bool(attributes & reparse_flag)

def validate_profile_pack(pack_dir, evidence_by_id, run_plan):
    pack_root = os.path.realpath(pack_dir)
    if not os.path.isdir(pack_root) or is_link_or_reparse(pack_root):
        raise ValueError("profile pack must be a regular local directory")
    entries = list(os.scandir(pack_root))
    if any(entry.is_dir(follow_symlinks=False) for entry in entries):
        raise ValueError("profile pack contains an unexpected directory")
    for entry in entries:
        if entry.is_symlink() or is_link_or_reparse(entry.path) or not entry.is_file(follow_symlinks=False):
            raise ValueError("profile pack contains an unsafe file")
    names = {entry.name for entry in entries}
    if not REQUIRED_PACK_FILES.issubset(names):
        raise ValueError("profile pack is missing required files")
    try:
        with open(os.path.join(pack_root, "draft-manifest.json"), "r", encoding="utf-8") as handle:
            draft = json.load(handle)
        with open(os.path.join(pack_root, "card.json"), "r", encoding="utf-8") as handle:
            card = json.load(handle)
        with open(os.path.join(pack_root, "appendix.md"), "r", encoding="utf-8") as handle:
            appendix = handle.read()
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError("profile pack metadata is invalid") from exc
    if draft.get("schema_version") != "1":
        raise ValueError("unsupported profile pack schema")
    profile_id = draft.get("profile_id", "")
    if (
        not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", profile_id)
        or profile_id.upper() in WINDOWS_RESERVED_NAMES
    ):
        raise ValueError("invalid profile_id")
    if draft.get("report_set_hash") != run_plan.get("report_set_hash"):
        raise ValueError("profile pack report_set_hash does not match the run")
    domains = draft.get("domains", {})
    if set(domains) != VALID_DOMAINS:
        raise ValueError("profile pack must contain exactly work, design, and write domain states")
    if domains["work"].get("status") != "active":
        raise ValueError("work domain must be active")

    allowed_names = set(REQUIRED_PACK_FILES)
    validated_rules = {}
    for domain in sorted(VALID_DOMAINS):
        state = domains[domain]
        filename, expected_name = DOMAIN_FILES[domain]
        if state.get("status") == "inactive":
            if (
                domain == "work"
                or state.get("reason") != "insufficient evidence"
                or state.get("deepen_instruction") != f"run ditto and deepen {domain}"
                or "file" in state
            ):
                raise ValueError(f"invalid inactive {domain} domain state")
            continue
        if state.get("status") != "active" or state.get("file") != filename:
            raise ValueError(f"unsafe profile path for {domain}")
        candidate = os.path.realpath(os.path.join(pack_root, state["file"]))
        try:
            contained = os.path.commonpath((pack_root, candidate)) == pack_root
        except ValueError:
            contained = False
        if not contained or os.path.basename(candidate) != filename:
            raise ValueError(f"unsafe profile path for {domain}")
        if not os.path.isfile(candidate) or is_link_or_reparse(candidate):
            raise ValueError(f"unsafe profile path for {domain}")
        allowed_names.add(filename)
        with open(candidate, "r", encoding="utf-8") as handle:
            profile = handle.read()
        if not has_skill_frontmatter(profile, expected_name=expected_name):
            raise ValueError(f"active {domain} profile requires exact name: {expected_name}")
        rules = state.get("rules", [])
        if not rules:
            raise ValueError(f"active {domain} domain requires rules")
        sections = write_profile_sections(profile) if domain == "write" else None
        for rule in rules:
            validate_rule(rule, evidence_by_id, require_cross_strata=run_plan["adequate_strata"], domain=domain)
            if rule["text"] not in profile or rule["implication"] not in profile:
                raise ValueError("profile file omits a validated rule or implication")
            if sections is not None:
                section = sections.get(rule["register"], "")
                if rule["text"] not in section or rule["implication"] not in section:
                    raise ValueError("write rule must appear under its own register section")
            for evidence_id in rule["evidence_ids"]:
                evidence = evidence_by_id[evidence_id]
                if evidence_id not in appendix:
                    raise ValueError("appendix is missing a referenced evidence id")
                for receipt in evidence.get("quotes", []):
                    if (
                        escape_private_markdown(receipt["date"]) not in appendix
                        or escape_private_markdown(receipt["text"]) not in appendix
                    ):
                        raise ValueError("appendix is missing an exact private quote receipt")
            validated_rules[rule["text"]] = rule
    if names != allowed_names:
        raise ValueError("profile pack contains an unexpected file")
    if not isinstance(card, dict) or not isinstance(card.get("laws"), list) or not card.get("archetype"):
        raise ValueError("card.json is invalid")
    work_rules = {rule["text"]: rule for rule in domains["work"]["rules"]}
    for law in card["laws"]:
        rule = work_rules.get(law.get("text"))
        if rule is None:
            raise ValueError("card law does not match a validated work rule")
        sessions = set().union(*(evidence_by_id[value]["sessions"] for value in rule["evidence_ids"]))
        if law.get("count") != f"{len(sessions)} sessions":
            raise ValueError("card law count must use distinct supporting sessions")
    return draft

def escape_private_markdown(value):
    return re.sub(r"([\\`*_{}\[\]<>#])", r"\\\1", value)

def write_profile_sections(profile):
    marks = sorted(
        (profile.find(heading), register)
        for register, heading in REGISTER_SECTIONS
        if heading in profile
    )
    sections = {}
    for position, (start, register) in enumerate(marks):
        end = marks[position + 1][0] if position + 1 < len(marks) else len(profile)
        sections[register] = profile[start:end]
    return sections

def render_domain_profile(domain, rules):
    _, skill_name = DOMAIN_FILES[domain]
    lines = [
        "---", f"name: {skill_name}",
        f"description: Evidence-backed Ditto {domain} profile", "---", "",
        f"# Ditto {domain} profile", "",
    ]
    if domain == "write":
        lines.extend([
            "Pick one register per task from the audience in front of you; voice laws always apply.", "",
        ])
        for register, heading in REGISTER_SECTIONS:
            selected = [rule for rule in rules if rule.get("register", "shared") == register]
            if not selected:
                continue
            lines.extend([heading, ""])
            for rule in sorted(selected, key=lambda item: (item["text"], item["implication"])):
                lines.extend([f"- {rule['text']}", f"  - Action: {rule['implication']}"])
            lines.append("")
        return "\n".join(lines).rstrip("\n") + "\n"
    for rule in sorted(rules, key=lambda item: (item["text"], item["implication"])):
        lines.extend([f"- {rule['text']}", f"  - Action: {rule['implication']}"])
    return "\n".join(lines) + "\n"

def assemble_profile_pack(ditto_home, run_plan, domain_drafts):
    if set(domain_drafts) != VALID_DOMAINS:
        raise ValueError("assembly requires exactly three domain drafts")
    evidence = run_plan.get("evidence_by_id") or load_adaptive_evidence(run_plan)
    for domain in sorted(VALID_DOMAINS):
        validate_domain_draft(domain_drafts[domain], domain, evidence, run_plan)
    run_id = run_plan.get("run_id", "")
    expected_run_dir = safe_private_child(ditto_home, "runs", run_id)
    run_dir = os.path.abspath(run_plan.get("run_dir", ""))
    pack_path = os.path.abspath(run_plan.get("pack_path", ""))
    expected_pack_path = os.path.join(run_dir, "pack")
    if (
        os.path.normcase(os.path.realpath(run_dir)) != os.path.normcase(expected_run_dir)
        or os.path.normcase(pack_path) != os.path.normcase(expected_pack_path)
    ):
        raise ValueError("profile pack must stay inside the assigned run directory")
    if os.path.exists(pack_path) and is_link_or_reparse(pack_path):
        raise ValueError("assigned profile pack cannot be a link or reparse point")
    os.makedirs(pack_path, exist_ok=True)
    if is_link_or_reparse(pack_path):
        raise ValueError("assigned profile pack cannot be a link or reparse point")
    for entry in os.scandir(pack_path):
        if entry.is_dir(follow_symlinks=False) or entry.is_symlink():
            raise ValueError("assigned pack contains unsafe existing content")
        os.remove(entry.path)

    domain_states = {}
    referenced_ids = set()
    for domain in sorted(VALID_DOMAINS):
        draft = domain_drafts[domain]
        if draft["status"] == "inactive":
            domain_states[domain] = {
                "status": "inactive", "reason": "insufficient evidence",
                "deepen_instruction": f"run ditto and deepen {domain}",
            }
            continue
        filename, _ = DOMAIN_FILES[domain]
        rules = sorted(draft["rules"], key=lambda item: (item["text"], item["implication"]))
        atomic_write_text(os.path.join(pack_path, filename), render_domain_profile(domain, rules))
        rendered_rules = []
        for rule in rules:
            rendered = {
                key: rule[key] for key in (
                    "text", "implication", "kind", "evidence_ids"
                )
            }
            if "confidence" in rule:
                rendered["confidence"] = rule["confidence"]
            if "register" in rule:
                rendered["register"] = rule["register"]
            rendered_rules.append(rendered)
            referenced_ids.update(rule["evidence_ids"])
        domain_states[domain] = {"status": "active", "file": filename, "rules": rendered_rules}

    appendix = ["# Private evidence receipts", ""]
    for evidence_id in sorted(referenced_ids):
        item = evidence[evidence_id]
        appendix.extend([f"## {escape_private_markdown(evidence_id)}", ""])
        for quote in sorted(item.get("quotes", []), key=lambda value: (
            value.get("date", ""), value.get("session_id", ""), value.get("receipt_id", "")
        )):
            appendix.append(
                f"- {escape_private_markdown(quote.get('session_id', ''))} "
                f"{escape_private_markdown(quote.get('date', ''))}: "
                f"{escape_private_markdown(quote.get('text', ''))}"
            )
        for quote in item.get("contradictions", []):
            appendix.append(
                f"- contradiction {escape_private_markdown(quote.get('session_id', ''))} "
                f"{escape_private_markdown(quote.get('date', ''))}: "
                f"{escape_private_markdown(quote.get('text', ''))}"
            )
        appendix.append("")
    atomic_write_text(os.path.join(pack_path, "appendix.md"), "\n".join(appendix))

    work_rules = domain_states["work"]["rules"]
    ranked_laws = []
    for rule in work_rules:
        sessions = set().union(*(evidence[value]["sessions"] for value in rule["evidence_ids"]))
        ranked_laws.append((len(sessions), rule["text"]))
    ranked_laws.sort(key=lambda item: (-item[0], item[1]))
    card = {
        "archetype": "Evidence-First Builder",
        "laws": [{"text": text, "count": f"{count} sessions"} for count, text in ranked_laws[:3]],
        "truth": "",
    }
    atomic_write_text(os.path.join(pack_path, "card.json"), canonical_json(card) + "\n")
    manifest = {
        "schema_version": "1", "profile_id": "default",
        "report_set_hash": run_plan["report_set_hash"],
        "domains": {domain: domain_states[domain] for domain in sorted(domain_states)},
    }
    atomic_write_text(os.path.join(pack_path, "draft-manifest.json"), canonical_json(manifest) + "\n")
    validate_profile_pack(pack_path, evidence, run_plan)
    return {
        "status": "assembled", "pack_path": pack_path,
        "report_set_hash": run_plan["report_set_hash"],
        "domain_evidence_hashes": {
            domain: domain_drafts[domain]["evidence_set_hash"] for domain in sorted(VALID_DOMAINS)
        },
    }

def file_sha256_map(directory, names):
    return {name: sha256_file(os.path.join(directory, name)) for name in sorted(names)}

def validate_version_directory(directory, expected_report_set_hash=None):
    manifest_path = os.path.join(directory, "manifest.json")
    try:
        with open(manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError) as exc:
        raise ValueError("profile manifest is missing or corrupt") from exc
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != "1"
        or manifest.get("profile_id") != "default"
        or not re.fullmatch(r"[a-f0-9]{20}", manifest.get("profile_version", ""))
        or not isinstance(manifest.get("files"), dict)
    ):
        raise ValueError("profile manifest schema is invalid")
    if expected_report_set_hash and manifest.get("report_set_hash") != expected_report_set_hash:
        raise ValueError("profile manifest report set hash mismatch")
    unsigned_manifest = dict(manifest)
    unsigned_manifest["profile_version"] = ""
    expected_profile_version = sha256_text(canonical_json(unsigned_manifest))[:20]
    if manifest["profile_version"] != expected_profile_version:
        raise ValueError("profile manifest version hash mismatch")
    if expected_report_set_hash:
        domains = manifest.get("domains")
        required_files = {"you.md", "appendix.md", "card.json", "draft-manifest.json"}
        selected_source_tokens = manifest.get("selected_source_tokens")
        segment_hashes = manifest.get("segment_hashes")
        if (
            manifest.get("prompt_schema_version") != PROMPT_SCHEMA_VERSION
            or manifest.get("reducer_schema_version") != REDUCER_SCHEMA_VERSION
            or not isinstance(manifest.get("source_coverage"), dict)
            or isinstance(selected_source_tokens, bool)
            or not isinstance(selected_source_tokens, int)
            or selected_source_tokens < 0
            or not isinstance(segment_hashes, list)
            or not segment_hashes
            or any(not re.fullmatch(r"[a-f0-9]{64}", value or "") for value in segment_hashes)
        ):
            raise ValueError("profile manifest reduction metadata is invalid")
        if (
            not isinstance(domains, dict)
            or set(domains) != VALID_DOMAINS
            or not isinstance(domains.get("work"), dict)
            or domains["work"].get("status") != "active"
        ):
            raise ValueError("profile manifest domains are incomplete")
        for domain, state in domains.items():
            if not isinstance(state, dict) or state.get("status") not in {"active", "inactive"}:
                raise ValueError("profile manifest domain state is invalid")
            if state["status"] == "active":
                filename = state.get("file")
                if filename != DOMAIN_FILES[domain][0]:
                    raise ValueError("profile manifest domain file is invalid")
                required_files.add(filename)
            elif (
                domain == "work"
                or state.get("reason") != "insufficient evidence"
                or state.get("deepen_instruction") != f"run ditto and deepen {domain}"
                or "file" in state
            ):
                raise ValueError("profile manifest inactive domain state is invalid")
        if not required_files.issubset(manifest["files"]):
            raise ValueError("profile manifest files are incomplete")
    for name, expected in manifest["files"].items():
        if not re.fullmatch(r"[a-f0-9]{64}", expected or ""):
            raise ValueError("profile file hash is invalid")
        path = os.path.join(directory, name)
        if not os.path.isfile(path) or is_link_or_reparse(path) or sha256_file(path) != expected:
            raise ValueError("profile file hash mismatch")
    manifest_bytes = (canonical_json(manifest) + "\n").encode("utf-8")
    return manifest, sha256_text(manifest_bytes.decode("utf-8"))

def optional_bytes(path):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as handle:
        return handle.read()

def restore_optional(path, data):
    if data is None:
        if os.path.exists(path):
            os.remove(path)
    else:
        atomic_write_bytes(path, data)

def activate_profile_pack(ditto_home, pack_dir, evidence_by_id, run_plan, fail_after=None):
    home = resolve_ditto_home(ditto_home)
    draft = validate_profile_pack(pack_dir, evidence_by_id, run_plan)
    pack_names = {entry.name for entry in os.scandir(pack_dir) if entry.is_file(follow_symlinks=False)}
    file_hashes = file_sha256_map(pack_dir, pack_names)
    manifest = {
        "schema_version": "1",
        "profile_id": "default",
        "profile_version": "",
        "report_set_hash": draft["report_set_hash"],
        "prompt_schema_version": PROMPT_SCHEMA_VERSION,
        "reducer_schema_version": REDUCER_SCHEMA_VERSION,
        "source_coverage": run_plan["source_coverage"],
        "selected_source_tokens": run_plan["selected_source_tokens"],
        "segment_hashes": sorted(run_plan["segment_hashes"]),
        "domains": draft["domains"],
        "files": file_hashes,
    }
    manifest["profile_version"] = sha256_text(canonical_json(manifest))[:20]
    manifest_bytes = (canonical_json(manifest) + "\n").encode("utf-8")
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    versions = safe_private_child(home, "profiles", "default", "versions")
    os.makedirs(versions, exist_ok=True)
    staged = os.path.join(versions, ".staged-" + manifest["profile_version"] + "-" + uuid.uuid4().hex)
    os.makedirs(staged)
    target = os.path.join(versions, manifest["profile_version"])
    current_path = safe_private_child(home, "profiles", "default", "current.json")
    active_path = safe_private_child(home, "active-profile.json")
    previous_current = optional_bytes(current_path)
    previous_active = optional_bytes(active_path)
    try:
        for name in sorted(pack_names):
            with open(os.path.join(pack_dir, name), "rb") as handle:
                atomic_write_bytes(os.path.join(staged, name), handle.read())
        atomic_write_bytes(os.path.join(staged, "manifest.json"), manifest_bytes)
        validate_version_directory(staged, manifest["report_set_hash"])
        if fail_after == "version-stage":
            raise RuntimeError("injected activation failure after version-stage")
        if os.path.isdir(target):
            existing, _ = validate_version_directory(target, manifest["report_set_hash"])
            if existing != manifest:
                raise ValueError("existing profile version hash mismatch")
            shutil.rmtree(staged)
        else:
            os.replace(staged, target)
        if fail_after == "version-rename":
            raise RuntimeError("injected activation failure after version-rename")
        pointer = {
            "schema_version": "1",
            "profile_id": "default",
            "profile_version": manifest["profile_version"],
            "manifest_hash": manifest_hash,
        }
        atomic_write_text(current_path, canonical_json(pointer) + "\n")
        if fail_after == "pointer-write":
            raise RuntimeError("injected activation failure after pointer-write")
        if previous_active is None:
            atomic_write_text(
                active_path,
                canonical_json({"schema_version": "1", "profile_id": "default"}) + "\n",
            )
        reduction_root = safe_private_child(
            home,
            "cache",
            "reductions",
            REDUCER_SCHEMA_VERSION,
            manifest["report_set_hash"],
        )
        if os.path.isdir(reduction_root):
            cached, _ = validate_version_directory(reduction_root, manifest["report_set_hash"])
            if cached != manifest:
                raise ValueError("existing reduction cache hash mismatch")
        else:
            staged_reduction = reduction_root + ".staged-" + uuid.uuid4().hex
            os.makedirs(os.path.dirname(reduction_root), exist_ok=True)
            shutil.copytree(target, staged_reduction)
            validate_version_directory(staged_reduction, manifest["report_set_hash"])
            os.replace(staged_reduction, reduction_root)
        return {
            "status": "active",
            "profile_id": "default",
            "profile_version": manifest["profile_version"],
            "manifest_hash": manifest_hash,
            "manifest_path": os.path.join(target, "manifest.json"),
            "card_path": os.path.join(target, "card.json"),
        }
    except Exception:
        restore_optional(current_path, previous_current)
        restore_optional(active_path, previous_active)
        raise
    finally:
        if os.path.isdir(staged):
            shutil.rmtree(staged)

def activate_cached_reduction(ditto_home, report_set_hash):
    if not re.fullmatch(r"[a-f0-9]{64}", report_set_hash or ""):
        raise ValueError("invalid report set hash")
    home = resolve_ditto_home(ditto_home)
    cached = safe_private_child(
        home, "cache", "reductions", REDUCER_SCHEMA_VERSION, report_set_hash
    )
    manifest, manifest_hash = validate_version_directory(cached, report_set_hash)
    version_dir = safe_private_child(
        home, "profiles", "default", "versions", manifest["profile_version"]
    )
    existing, _ = validate_version_directory(version_dir, report_set_hash)
    if existing != manifest:
        raise ValueError("cached reduction profile hash mismatch")
    current_path = safe_private_child(home, "profiles", "default", "current.json")
    active_path = safe_private_child(home, "active-profile.json")
    pointer = {
        "schema_version": "1",
        "profile_id": "default",
        "profile_version": manifest["profile_version"],
        "manifest_hash": manifest_hash,
    }
    atomic_write_text(current_path, canonical_json(pointer) + "\n")
    if not os.path.exists(active_path):
        atomic_write_text(active_path, canonical_json({"schema_version": "1", "profile_id": "default"}) + "\n")
    return {
        "status": "active",
        "profile_id": "default",
        "profile_version": manifest["profile_version"],
        "manifest_hash": manifest_hash,
        "manifest_path": os.path.join(version_dir, "manifest.json"),
        "card_path": os.path.join(version_dir, "card.json"),
    }

def select_run_segments(segments, current_segment_hashes, count, max_tokens):
    active = [item for item in segments if item.get("active") and not item.get("oversize")]
    retained = [item for item in active if item["segment_hash"] in current_segment_hashes]
    new = [item for item in active if item["segment_hash"] not in current_segment_hashes]
    work = select_segments(new, count=count, max_tokens=max_tokens)
    work_hashes = {item["segment_hash"] for item in work}
    report = sorted(retained + work, key=lambda item: (item["source"], item["first_date"], item["segment_hash"]))
    return report, work, len([item for item in new if item["segment_hash"] not in work_hashes])

MIGRATION_ID_PATTERN = re.compile(r"^[a-f0-9]{20}$")

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def encode_optional_bytes(data):
    return None if data is None else base64.b64encode(data).decode("ascii")

def decode_optional_bytes(value):
    return None if value is None else base64.b64decode(value.encode("ascii"), validate=True)

def migration_record_path(ditto_home, migration_id):
    if not MIGRATION_ID_PATTERN.fullmatch(migration_id):
        raise ValueError("invalid migration id")
    return safe_private_child(ditto_home, "migrations", migration_id + ".json")

def write_migration_record(ditto_home, record):
    path = migration_record_path(ditto_home, record["migration_id"])
    atomic_write_text(path, canonical_json(record) + "\n")
    return record

def load_migration_record(ditto_home, migration_id):
    path = migration_record_path(ditto_home, migration_id)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, ValueError) as exc:
        raise ValueError("migration record is missing or corrupt") from exc
    if not isinstance(record, dict):
        raise ValueError("migration record is invalid")
    identity = {
        "target": record.get("target"),
        "legacy_path": record.get("legacy_path"),
        "legacy_hash": record.get("legacy_hash"),
    }
    expected_backup = safe_private_child(
        ditto_home, "legacy", record.get("target", ""), migration_id, "you"
    ) if record.get("target") in {"codex", "claude"} else None
    if (
        record.get("migration_id") != migration_id
        or record.get("schema_version") != "1"
        or record.get("target") not in {"codex", "claude"}
        or record.get("status") not in {"staged", "cutover", "rolled-back"}
        or record.get("mode") not in {"legacy-import", "deactivate-legacy-only"}
        or not re.fullmatch(r"[a-f0-9]{64}", record.get("legacy_hash", ""))
        or sha256_text(canonical_json(identity))[:20] != migration_id
        or (record.get("legacy_backup") is not None and record.get("legacy_backup") != expected_backup)
    ):
        raise ValueError("migration record is invalid")
    return record

def stage_legacy_migration(target, home_dir, ditto_home):
    if target not in {"codex", "claude"}:
        raise ValueError("legacy migration target must be codex or claude")
    home = resolve_ditto_home(ditto_home)
    legacy_path = os.path.abspath(
        os.path.join(os.path.expanduser(home_dir), f".{target}", "skills", "you", "SKILL.md")
    )
    try:
        with open(legacy_path, "rb") as handle:
            legacy_bytes = handle.read()
        text = legacy_bytes.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError("legacy profile is missing or not UTF-8") from exc
    fields = parse_frontmatter(text)
    name = fields.get("name") if fields else None
    if name not in {"you", "ditto-work-profile"} or not fields.get("description"):
        raise ValueError("legacy profile requires exact supported frontmatter")
    legacy_origin = "classic-you" if name == "you" else "skills-sh-core"
    legacy_hash = sha256_bytes(legacy_bytes)
    current_path = safe_private_child(home, "profiles", "default", "current.json")
    active_path = safe_private_child(home, "active-profile.json")
    prior_current = optional_bytes(current_path)
    prior_active = optional_bytes(active_path)
    active = active_profile_state(home)
    mode = "deactivate-legacy-only" if active is not None else "legacy-import"
    staged_version = None
    staged_pointer = None
    if mode == "legacy-import":
        manifest = {
            "schema_version": "1",
            "profile_id": "default",
            "profile_version": "",
            "origin": "legacy-migration",
            "legacy_unverified": True,
            "report_set_hash": None,
            "prompt_schema_version": None,
            "reducer_schema_version": None,
            "source_coverage": {},
            "selected_source_tokens": 0,
            "segment_hashes": [],
            "domains": {
                "work": {"status": "active", "file": "you.md", "legacy_unverified": True},
                "design": {"status": "inactive", "reason": "insufficient evidence", "deepen_instruction": "run ditto and deepen design"},
                "write": {"status": "inactive", "reason": "insufficient evidence", "deepen_instruction": "run ditto and deepen write"},
            },
            "files": {"you.md": legacy_hash},
        }
        manifest["profile_version"] = sha256_text(canonical_json(manifest))[:20]
        staged_version = manifest["profile_version"]
        version_dir = safe_private_child(home, "profiles", "default", "versions", staged_version)
        if os.path.exists(version_dir):
            existing, _ = validate_version_directory(version_dir)
            if existing != manifest:
                raise ValueError("existing legacy migration version conflicts")
        else:
            staged = version_dir + ".staged-" + uuid.uuid4().hex
            os.makedirs(staged, exist_ok=False)
            try:
                atomic_write_bytes(os.path.join(staged, "you.md"), legacy_bytes)
                manifest_bytes = (canonical_json(manifest) + "\n").encode("utf-8")
                atomic_write_bytes(os.path.join(staged, "manifest.json"), manifest_bytes)
                validate_version_directory(staged)
                os.makedirs(os.path.dirname(version_dir), exist_ok=True)
                os.replace(staged, version_dir)
            finally:
                if os.path.isdir(staged):
                    shutil.rmtree(staged)
        manifest_bytes = (canonical_json(manifest) + "\n").encode("utf-8")
        staged_pointer = {
            "schema_version": "1",
            "profile_id": "default",
            "profile_version": staged_version,
            "manifest_hash": sha256_bytes(manifest_bytes),
        }
    identity = {"target": target, "legacy_path": legacy_path, "legacy_hash": legacy_hash}
    migration_id = sha256_text(canonical_json(identity))[:20]
    record = {
        "schema_version": "1",
        "migration_id": migration_id,
        "target": target,
        "status": "staged",
        "mode": mode,
        "legacy_origin": legacy_origin,
        "legacy_path": legacy_path,
        "legacy_hash": legacy_hash,
        "staged_version": staged_version,
        "staged_pointer": staged_pointer,
        "prior_current_base64": encode_optional_bytes(prior_current),
        "prior_current_hash": None if prior_current is None else sha256_bytes(prior_current),
        "prior_active_base64": encode_optional_bytes(prior_active),
        "prior_active_hash": None if prior_active is None else sha256_bytes(prior_active),
        "legacy_backup": None,
    }
    return write_migration_record(home, record)

def restore_migration_pointers(home, record):
    current_path = safe_private_child(home, "profiles", "default", "current.json")
    active_path = safe_private_child(home, "active-profile.json")
    restore_optional(current_path, decode_optional_bytes(record["prior_current_base64"]))
    restore_optional(active_path, decode_optional_bytes(record["prior_active_base64"]))

def cutover_legacy_migration(migration_id, ditto_home, fail_after=None):
    home = resolve_ditto_home(ditto_home)
    record = load_migration_record(home, migration_id)
    if record["status"] != "staged":
        raise ValueError("migration is not staged")
    legacy_file = record["legacy_path"]
    if not os.path.isfile(legacy_file) or sha256_file(legacy_file) != record["legacy_hash"]:
        raise ValueError("legacy profile changed after staging")
    source_dir = os.path.dirname(legacy_file)
    backup_dir = safe_private_child(home, "legacy", record["target"], migration_id, "you")
    if os.path.exists(backup_dir):
        raise ValueError("legacy backup destination already exists")
    if os.path.splitdrive(source_dir)[0].lower() != os.path.splitdrive(backup_dir)[0].lower():
        raise ValueError("legacy migration requires the profile and DITTO_HOME on the same volume")
    os.makedirs(os.path.dirname(backup_dir), exist_ok=True)
    moved = False
    try:
        os.replace(source_dir, backup_dir)
        moved = True
        record["legacy_backup"] = backup_dir
        if fail_after == "legacy-move":
            raise RuntimeError("injected migration failure after legacy-move")
        if record["mode"] == "legacy-import":
            current_path = safe_private_child(home, "profiles", "default", "current.json")
            active_path = safe_private_child(home, "active-profile.json")
            atomic_write_text(current_path, canonical_json(record["staged_pointer"]) + "\n")
            if fail_after == "active-write":
                raise RuntimeError("injected migration failure after active-write")
            atomic_write_text(active_path, canonical_json({"schema_version": "1", "profile_id": "default"}) + "\n")
            active_profile_state(home)
        record["status"] = "cutover"
        return write_migration_record(home, record)
    except Exception:
        if moved and os.path.isdir(backup_dir) and not os.path.exists(source_dir):
            os.makedirs(os.path.dirname(source_dir), exist_ok=True)
            os.replace(backup_dir, source_dir)
        restore_migration_pointers(home, record)
        raise

def rollback_legacy_migration(migration_id, ditto_home):
    home = resolve_ditto_home(ditto_home)
    record = load_migration_record(home, migration_id)
    if record["status"] != "cutover":
        raise ValueError("migration is not cut over")
    backup_dir = record.get("legacy_backup")
    source_dir = os.path.dirname(record["legacy_path"])
    if os.path.exists(source_dir):
        raise ValueError("legacy discovery path already exists; refusing to overwrite it")
    if not backup_dir or not os.path.isdir(backup_dir):
        raise ValueError("legacy backup is missing")
    current_path = safe_private_child(home, "profiles", "default", "current.json")
    active_path = safe_private_child(home, "active-profile.json")
    cutover_current = optional_bytes(current_path)
    cutover_active = optional_bytes(active_path)
    os.makedirs(os.path.dirname(source_dir), exist_ok=True)
    os.replace(backup_dir, source_dir)
    try:
        if sha256_file(record["legacy_path"]) != record["legacy_hash"]:
            raise ValueError("restored legacy profile hash mismatch")
        restore_migration_pointers(home, record)
        record["status"] = "rolled-back"
        return write_migration_record(home, record)
    except Exception:
        if os.path.isdir(source_dir) and not os.path.exists(backup_dir):
            os.replace(source_dir, backup_dir)
        for path, data in ((current_path, cutover_current), (active_path, cutover_active)):
            if data is None:
                if os.path.exists(path):
                    os.remove(path)
            else:
                atomic_write_bytes(path, data)
        raise

def migrate_adapter_block(target, repo, ditto_home, mode):
    if target not in {"agents", "gemini"}:
        raise ValueError("adapter target must be agents or gemini")
    if mode not in {"backup-remove", "restore"}:
        raise ValueError("adapter mode must be backup-remove or restore")
    filename = "AGENTS.md" if target == "agents" else "GEMINI.md"
    path = os.path.abspath(os.path.join(repo, filename))
    home = resolve_ditto_home(ditto_home)
    key = sha256_text(f"{target}:{os.path.normcase(path)}")[:20]
    record_path = safe_private_child(home, "migrations", "adapter-" + key + ".json")
    if mode == "restore":
        try:
            with open(record_path, "r", encoding="utf-8") as handle:
                record = json.load(handle)
        except (OSError, ValueError) as exc:
            raise ValueError("adapter migration record is missing or corrupt") from exc
        current = optional_bytes(path) or b""
        if sha256_bytes(current) != record["removed_hash"]:
            raise ValueError("adapter file changed after Ditto block removal")
        with open(record["backup_path"], "rb") as handle:
            original = handle.read()
        if sha256_bytes(original) != record["original_hash"]:
            raise ValueError("adapter backup hash mismatch")
        atomic_write_bytes(path, original)
        record["status"] = "restored"
        atomic_write_text(record_path, canonical_json(record) + "\n")
        return record
    try:
        with open(path, "rb") as handle:
            original = handle.read()
        text = original.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError("adapter file is missing or not UTF-8") from exc
    if text.count(DITTO_START) != 1 or text.count(DITTO_END) != 1:
        raise ValueError("adapter requires one complete Ditto marked block")
    pattern = re.compile(r"(?:\r?\n)*" + re.escape(DITTO_START) + r".*?" + re.escape(DITTO_END) + r"(?:\r?\n)*", re.DOTALL)
    updated = pattern.sub("\n", text).rstrip() + "\n"
    original_hash = sha256_bytes(original)
    backup_path = safe_private_child(home, "legacy", "adapters", original_hash, filename)
    atomic_write_bytes(backup_path, original)
    removed_bytes = updated.encode("utf-8")
    record = {
        "schema_version": "1",
        "adapter_id": key,
        "target": target,
        "repo": os.path.abspath(repo),
        "path": path,
        "status": "staged",
        "original_hash": original_hash,
        "removed_hash": sha256_bytes(removed_bytes),
        "backup_path": backup_path,
    }
    atomic_write_text(record_path, canonical_json(record) + "\n")
    atomic_write_text(path, updated)
    record["status"] = "removed"
    atomic_write_text(record_path, canonical_json(record) + "\n")
    return record

def split_segment_sessions(text):
    marker = re.compile(
        r"^===== session:([A-Za-z0-9_-]+) source:([a-z0-9_-]+) =====$",
        re.MULTILINE,
    )
    matches = list(marker.finditer(text))
    sessions = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sessions[match.group(1)] = text[match.end():end]
    return sessions

def receipt_is_verbatim(receipt, session_text):
    date = receipt.get("date", "")
    quote = receipt.get("text", "").strip()
    if not date or not quote:
        return False
    message = re.compile(
        r"^\[([^\]]+)\]\n(.*?)(?=^\[[^\]]+\]\n|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    return any(found_date == date and quote in body for found_date, body in message.findall(session_text))

def validate_report(report, segment):
    if not isinstance(report, dict):
        raise ValueError("report must be a JSON object")
    if len(canonical_json(report).encode("utf-8")) > MAX_REPORT_BYTES:
        raise ValueError("report byte ceiling exceeded")
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError("unsupported report schema")
    if report.get("segment_hash") != segment["segment_hash"]:
        raise ValueError("report segment hash mismatch")
    coverage = report.get("coverage", {})
    covered = set(coverage.get("session_ids", []))
    allowed = {item["session_id"] for item in segment["session_versions"]}
    if covered != allowed:
        raise ValueError("report coverage must match every segment session")
    expected_coverage = {
        "sources": [segment["source"]],
        "first_date": segment["first_date"],
        "last_date": segment["last_date"],
        "source_tokens": segment["source_tokens"],
    }
    if any(coverage.get(key) != value for key, value in expected_coverage.items()):
        raise ValueError("report coverage metadata mismatch")
    session_texts = split_segment_sessions(segment.get("text", ""))
    if set(session_texts) != allowed:
        raise ValueError("segment text does not match session metadata")
    domain_coverage = report.get("domain_coverage", {})
    if (
        set(domain_coverage) != VALID_DOMAINS
        or any(value not in {"evidence", "no-signal"} for value in domain_coverage.values())
    ):
        raise ValueError("domain coverage must state evidence or no-signal for every domain")
    seen = set()
    evidence_items = report.get("evidence", [])
    if not isinstance(evidence_items, list) or len(evidence_items) > MAX_EVIDENCE_PER_REPORT:
        raise ValueError("evidence count is outside the bounded report contract")
    for item in evidence_items:
        if item.get("domain") not in VALID_DOMAINS or item.get("kind") not in VALID_EVIDENCE_KINDS:
            raise ValueError("invalid evidence domain or kind")
        validate_register(item["domain"], item.get("register"), "evidence")
        evidence_id = item.get("evidence_id", "")
        required_prefix = "ev-" + report["segment_hash"][:8] + "-"
        if (
            not evidence_id.startswith(required_prefix)
            or not re.fullmatch(r"ev-[a-f0-9]{8}-[a-z0-9-]{3,64}", evidence_id)
            or evidence_id in seen
        ):
            raise ValueError("invalid or duplicate evidence id")
        seen.add(evidence_id)
        if not item.get("instruction") or not item.get("implication") or not item.get("quotes"):
            raise ValueError("evidence requires instruction, implication, and quotes")
        contradictions = item.get("contradictions")
        if not isinstance(contradictions, list):
            raise ValueError("contradictions must be a list")
        for receipt in item["quotes"] + contradictions:
            session_id = receipt.get("session_id")
            if session_id not in covered:
                raise ValueError("quote references unknown session")
            if len(receipt.get("text", "")) > MAX_QUOTE_CHARS:
                raise ValueError("quote exceeds the bounded receipt length")
            if not receipt_is_verbatim(receipt, session_texts[session_id]):
                raise ValueError("quote must be verbatim text from the dated session message")
    evidenced_domains = {item["domain"] for item in evidence_items}
    if any(
        (domain_coverage[domain] == "evidence") != (domain in evidenced_domains)
        for domain in VALID_DOMAINS
    ):
        raise ValueError("domain coverage does not match evidence items")
    return report

def validate_scout_report(report, packet):
    if len(canonical_json(report).encode("utf-8")) > MAX_SCOUT_REPORT_BYTES:
        raise ValueError("scout report byte ceiling exceeded")
    if report.get("schema_version") != SCOUT_REPORT_SCHEMA_VERSION:
        raise ValueError("unsupported scout report schema")
    if report.get("packet_hash") != packet.get("packet_hash"):
        raise ValueError("scout report packet hash mismatch")
    coverage = report.get("coverage", {})
    if coverage.get("receipt_ids") != packet.get("receipt_ids"):
        raise ValueError("scout report receipt coverage mismatch")
    if coverage.get("source_tokens") != packet.get("source_tokens"):
        raise ValueError("scout report token coverage mismatch")
    domain_coverage = report.get("domain_coverage", {})
    if (
        set(domain_coverage) != VALID_DOMAINS
        or any(value not in {"evidence", "no-signal"} for value in domain_coverage.values())
    ):
        raise ValueError("scout domain coverage must include work, design, and write")
    packet_receipts = {item["receipt_id"]: item for item in packet.get("receipts", [])}
    evidence_items = report.get("evidence")
    if not isinstance(evidence_items, list):
        raise ValueError("scout evidence must be a list")
    counts = {domain: 0 for domain in VALID_DOMAINS}
    seen_ids = set()
    for item in evidence_items:
        domain = item.get("domain")
        if domain not in VALID_DOMAINS:
            raise ValueError("invalid scout evidence domain")
        counts[domain] += 1
        if counts[domain] > 12:
            raise ValueError(f"{domain} evidence ceiling exceeded")
        evidence_id = item.get("evidence_id", "")
        if not evidence_id or evidence_id in seen_ids:
            raise ValueError("invalid or duplicate scout evidence id")
        seen_ids.add(evidence_id)
        if item.get("kind") not in VALID_EVIDENCE_KINDS:
            raise ValueError("invalid scout evidence kind")
        validate_register(domain, item.get("register"), "evidence")
        scope = item.get("scope")
        if scope not in {"universal", "contextual"}:
            raise ValueError("invalid scout evidence scope")
        if scope == "contextual" and not item.get("context", "").strip():
            raise ValueError("contextual scout evidence requires context")
        if item.get("signal_family") not in {
            "directive", "correction", "rejection", "preference", "recurrence", "exploration", "verification"
        }:
            raise ValueError("invalid scout signal family")
        if not item.get("instruction") or not item.get("implication") or not item.get("quotes"):
            raise ValueError("scout evidence requires instruction, implication, and quotes")
        contradictions = item.get("contradictions")
        if not isinstance(contradictions, list):
            raise ValueError("scout contradictions must be a list")
        for quote in item["quotes"] + contradictions:
            receipt = packet_receipts.get(quote.get("receipt_id"))
            if receipt is None:
                raise ValueError("scout receipt is not in the assigned packet")
            if any(quote.get(key) != receipt.get(key) for key in ("session_id", "date", "text")):
                raise ValueError("scout receipt must match exact packet text and date")
    evidenced = {item["domain"] for item in evidence_items}
    if any((domain_coverage[domain] == "evidence") != (domain in evidenced) for domain in VALID_DOMAINS):
        raise ValueError("scout domain coverage does not match evidence")
    return report

def scout_report_cache_path(ditto_home, packet_hash):
    if not re.fullmatch(r"[a-f0-9]{64}", packet_hash or ""):
        raise ValueError("invalid scout packet hash")
    return safe_private_child(
        ditto_home, "cache", "scout-reports", SCOUT_REPORT_SCHEMA_VERSION, packet_hash + ".json"
    )

def store_scout_report(report, ditto_home, packet):
    validate_scout_report(report, packet)
    path = scout_report_cache_path(ditto_home, packet["packet_hash"])
    atomic_write_text(path, canonical_json(report) + "\n")
    return path

def load_cached_scout_report(ditto_home, packet):
    path = scout_report_cache_path(ditto_home, packet["packet_hash"])
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="strict") as handle:
            report = json.load(handle)
        return validate_scout_report(report, packet)
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
        return None

def hydrate_segment(ditto_home, segment):
    hydrated = dict(segment)
    if "text" not in hydrated:
        path = segment_file_path(ditto_home, segment["segment_hash"])
        with open(path, "r", encoding="utf-8", errors="strict", newline="") as handle:
            hydrated["text"] = handle.read()
    text_hash = hydrated.get("text_hash")
    if text_hash and sha256_text(hydrated["text"]) != text_hash:
        raise ValueError("segment text hash mismatch")
    return hydrated

def store_report(report, ditto_home, segment):
    hydrated = hydrate_segment(ditto_home, segment)
    validate_report(report, hydrated)
    path = report_cache_path(ditto_home, segment["segment_hash"])
    atomic_write_text(path, canonical_json(report) + "\n")
    return path

def load_cached_report(ditto_home, segment, quarantine=True):
    path = report_cache_path(ditto_home, segment["segment_hash"])
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="strict") as handle:
            report = json.load(handle)
        validate_report(report, hydrate_segment(ditto_home, segment))
        return report
    except (OSError, UnicodeError, ValueError, TypeError, AttributeError, json.JSONDecodeError):
        if quarantine and os.path.exists(path):
            stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            quarantine_path = path + ".corrupt-" + stamp
            if os.path.exists(quarantine_path):
                quarantine_path += "-" + uuid.uuid4().hex[:8]
            os.replace(path, quarantine_path)
        return None

def reduction_cache_is_valid(ditto_home, report_set_hash):
    if not re.fullmatch(r"[a-f0-9]{64}", report_set_hash or ""):
        return False
    path = safe_private_child(
        ditto_home, "cache", "reductions", REDUCER_SCHEMA_VERSION, report_set_hash
    )
    try:
        cached_manifest, _ = validate_version_directory(path, report_set_hash)
        version_path = safe_private_child(
            ditto_home, "profiles", "default", "versions", cached_manifest["profile_version"]
        )
        version_manifest, _ = validate_version_directory(version_path, report_set_hash)
        return version_manifest == cached_manifest
    except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError):
        return False

def build_preflight(result, ditto_home, candidate_index, write=False):
    config = candidate_config(candidate_index)
    index = sync_segments(
        result["records"],
        ditto_home,
        config["segment_tokens"],
        write=write,
    )
    selected = select_segments(
        index["segments"],
        count=config["segments"],
        max_tokens=STARTER_MAX_SOURCE_TOKENS,
    )
    if result["sessions"] and not selected:
        raise ValueError(
            "no eligible bounded segment; inspect oversize sessions and explicitly plan deep mode"
        )
    selected_hashes = [segment["segment_hash"] for segment in selected]
    report_hits, report_paths = set(), []
    for segment in selected:
        path = report_cache_path(ditto_home, segment["segment_hash"])
        if load_cached_report(ditto_home, segment, quarantine=write) is not None:
            report_hits.add(segment["segment_hash"])
            report_paths.append(path)
    report_set_hash = (
        compute_report_set_hash(report_paths)
        if selected and len(report_paths) == len(selected)
        else None
    )
    reduction_cache_hit = reduction_cache_is_valid(ditto_home, report_set_hash)
    worker_calls, reducer_calls = planned_call_counts(
        selected_hashes,
        report_hits,
        reduction_cache_hit,
    )
    if worker_calls + reducer_calls > STARTER_MAX_MODEL_CALLS:
        raise ValueError("bounded plan exceeds the model-call ceiling")
    strata = {
        f"{segment['source']}:{segment['first_date'][:7]}"
        for segment in selected
    }
    return {
        "mode": "quick_preview",
        "profile_scope": "starter_profile",
        "quality_default": False,
        "notice": QUICK_PREVIEW_NOTICE,
        "candidate_index": candidate_index,
        "valid_sessions": result["sessions"],
        "post_dedupe_source_tokens": result["chars"] // 4,
        "selected_source_tokens": sum(segment["source_tokens"] for segment in selected),
        "selected_segments": selected,
        "cached_segments": len(report_hits),
        "cached_segment_hashes": sorted(report_hits),
        "uncached_segments": worker_calls,
        "planned_worker_calls": worker_calls,
        "planned_reducer_calls": reducer_calls,
        "remaining_new_segments": 0,
        "oversize_sessions": [
            version["session_id"]
            for segment in index["segments"]
            if segment.get("active") and segment.get("oversize")
            for version in segment["session_versions"]
        ],
        "report_set_hash": report_set_hash,
        "adequate_strata": len(strata) >= 2,
        "deep_mode": {"available": True, "automatic": False, "selected": False},
    }

def build_deep_preflight(result, ditto_home, write=False):
    index = sync_segments(result["records"], ditto_home, DEEP_SEGMENT_TOKENS, write=write)
    selected = sorted(
        (segment for segment in index["segments"] if segment.get("active")),
        key=lambda item: (item["source"], item["first_date"], item["segment_hash"]),
    )
    if result["sessions"] and not selected:
        raise ValueError("no valid segment remained for deep mode")
    hashes = [segment["segment_hash"] for segment in selected]
    hits, report_paths = set(), []
    for segment in selected:
        path = report_cache_path(ditto_home, segment["segment_hash"])
        if load_cached_report(ditto_home, segment, quarantine=write) is not None:
            hits.add(segment["segment_hash"])
            report_paths.append(path)
    report_set_hash = (
        compute_report_set_hash(report_paths)
        if selected and len(report_paths) == len(selected)
        else None
    )
    reduction_cache_hit = reduction_cache_is_valid(ditto_home, report_set_hash)
    worker_calls, reducer_calls = planned_call_counts(hashes, hits, reduction_cache_hit)
    return {
        "mode": "full",
        "profile_scope": "full_profile",
        "quality_default": True,
        "notice": FULL_PROFILE_NOTICE,
        "candidate_index": None,
        "valid_sessions": result["sessions"],
        "post_dedupe_source_tokens": result["chars"] // 4,
        "selected_source_tokens": sum(segment["source_tokens"] for segment in selected),
        "selected_segments": selected,
        "cached_segments": len(hits),
        "cached_segment_hashes": sorted(hits),
        "uncached_segments": worker_calls,
        "planned_worker_calls": worker_calls,
        "planned_reducer_calls": reducer_calls,
        "remaining_new_segments": 0,
        "oversize_sessions": [
            {"session_id": version["session_id"], "source_tokens": segment["source_tokens"]}
            for segment in selected if segment.get("oversize")
            for version in segment["session_versions"]
        ],
        "report_set_hash": report_set_hash,
        "adequate_strata": True,
        "deep_mode": {"available": True, "automatic": False, "selected": True},
    }

def atomic_write_bytes(path, data):
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    fd, staged = tempfile.mkstemp(prefix=".ditto-", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(staged, path)
    except Exception:
        if os.path.exists(staged):
            os.remove(staged)
        raise

def atomic_write_text(path, text):
    atomic_write_bytes(path, text.encode("utf-8"))

def replace_directory(staged, target):
    backup = target + ".ditto-backup-" + uuid.uuid4().hex
    if os.path.exists(target):
        os.replace(target, backup)
    try:
        os.replace(staged, target)
    except Exception:
        if os.path.exists(backup):
            os.replace(backup, target)
        raise
    if os.path.exists(backup):
        try:
            shutil.rmtree(backup)
        except OSError:
            pass

def write_outputs(blocks, out_dir, chunks, stats_result=None):
    os.makedirs(out_dir, exist_ok=True)
    chunks_dir = os.path.join(out_dir, "chunks")
    staged_chunks = tempfile.mkdtemp(prefix=".ditto-chunks-", dir=out_dir)

    corpus = "\n".join(blocks)
    try:
        idx = 1
        if blocks:
            # split on session boundaries into ~N chunks
            n = max(1, chunks)
            target = max(1, len(corpus) // n)
            cur, size = [], 0
            for b in blocks:
                cur.append(b); size += len(b)
                if size >= target:
                    atomic_write_text(
                        os.path.join(staged_chunks, f"chunk-{idx:02d}.txt"),
                        "\n".join(cur),
                    )
                    idx += 1; cur, size = [], 0
            if cur:
                atomic_write_text(
                    os.path.join(staged_chunks, f"chunk-{idx:02d}.txt"),
                    "\n".join(cur),
                )
                idx += 1

        atomic_write_text(os.path.join(out_dir, "you-corpus.txt"), corpus)
        if stats_result is not None:
            write_stats(stats_result, out_dir)
        replace_directory(staged_chunks, chunks_dir)
        staged_chunks = None
        return idx - 1
    finally:
        if staged_chunks and os.path.exists(staged_chunks):
            shutil.rmtree(staged_chunks)

def write_stats(result, out_dir):
    stats = {
        "sessions": result["sessions"],
        "messages": result["messages"],
        "tokens": result["chars"] // 4,
        "redactions": result["redactions"],
        "first_date": result.get("first_date", ""),
        "last_date": result.get("last_date", ""),
    }
    atomic_write_text(
        os.path.join(out_dir, "stats.json"),
        json.dumps(stats, indent=2, sort_keys=True) + "\n",
    )
    return stats

def months_between(first_date, last_date):
    try:
        y1, m1 = int(first_date[:4]), int(first_date[5:7])
        y2, m2 = int(last_date[:4]), int(last_date[5:7])
        return max(1, (y2 - y1) * 12 + (m2 - m1) + 1)
    except (ValueError, IndexError):
        return 0

def fmt_tokens(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n // 1000}K"
    return str(n)

def load_card(out_dir, card_path=None):
    path = card_path or os.path.join(out_dir, "card.json")
    if not os.path.exists(path):
        print(f"no card found at {path}")
        print("the card is written by the mining step: run ditto.py, then paste")
        print("MINING_PROMPT.md into your agent - the reducer emits card.json.")
        sys.exit(1)
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        card = json.load(fh)
    stats_path = os.path.join(out_dir, "stats.json")
    if os.path.exists(stats_path):
        with open(stats_path, "r", encoding="utf-8", errors="replace") as fh:
            card.setdefault("stats", {}).update(json.load(fh))
    return card

def _enable_vt():
    # let legacy Windows consoles interpret ANSI (Windows Terminal already does)
    if os.name != "nt":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False

def _card_colors():
    # ANSI accents when we're on a real terminal and the user hasn't opted out
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty() or not _enable_vt():
        return {"bold": "", "dim": "", "red": "", "yellow": "", "cream": "", "reset": ""}
    return {
        "bold": "\x1b[1m",
        "dim": "\x1b[2m",
        "red": "\x1b[38;5;131m",
        "yellow": "\x1b[38;5;179m",
        "cream": "\x1b[38;5;230m",
        "reset": "\x1b[0m",
    }

# the fixed brand mark — same in every screenshot, like a distro logo in neofetch.
# solid blocks only: every UTF-8 byte here survives cp1252 pipes, unlike ═ and ╝.
_CARD_LOGO = [
    "██████   ██  ████████  ████████   ██████ ",
    "██   ██  ██     ██         ██    ██    ██",
    "██   ██  ██     ██         ██    ██    ██",
    "██   ██  ██     ██         ██    ██    ██",
    "██████   ██     ██         ██     ██████ ",
]

# the engraving, pre-rendered as classic ASCII ramp art at three widths
# (pure ASCII: safe in every terminal, pipe, and wrapper; colored on capable terminals).
_CARD_ARTS = {
    54: [
        "                          .-\\\\*xXXx=*$X***=/;ii--.",
        "                      .-----\\-X=X$x**+xx+x$//i**----.",
        "             .----------$$$*=Xx=/&$*X=ix*--X*=i:ii;:--",
        "           \\---$$$$*+------XXX$x+/x+:;\\x*:::xx*++i;:,.",
        "         -\\\\$Xx\\\\--*| /-----//XX*=*//=|XXXx**|:|i,|:,.",
        "      \\---=+*x\\|;:;+=/:,:-;,--/Xx*/X*i|$\\--/$/;|=i;;,.",
        "     \\\\--x+**=;\\;++i=+++***//.//*;/xX-\\X//.||X|//i:,,.",
        "    \\\\&8\\$XxxXx/.;;+i:;ii++*//:=x*==-/$&8/-\\\\X| /i;:,.",
        "   .\\\\8\\\\-/$|:i----+i;i+\\-**x/-ii==+,//*x$&-X$|-\\\\;:,.",
        "  \\||&\\\\\\.//x-\\xX--//--\\xX--*xxXx*x/**xxXXx$&|\\+|+;:,.",
        "  |||8\\\\|  //-&&&&&$$--xx=::\\-==xXx*;;=xX$$X$//,|/i:,.",
        "   ||\\\\||   --///$X\\-/$X-----8&$=**x$$$XXXX$XX---\\;;,.",
        "  |//\\\\\\.      //-X*i*$&&&$$$$\\\\**x--;+*XX$$XXXx*+i;,.",
        " ., /+/         ///$&X$&$$&$$Xx/i++i-\\&&$$$XXX$-------",
        "  . |\\-----/i;:. ////X8&8&$Xxx&-----$X*x$&&8--\\\\-./-",
        "    |||@8||i,.,,,.://-/&$&&$$xX&$$XX*=\\\\8@\\\\-/*/-----",
        "     ///&|//-----i:--///$&&$xxxX&&&&---8\\\\\\.\\\\**+i;:..",
        "     |///8//*XXx=\\\\  ||xX$8&&&$X$&&$888\\\\\\\\\\-x*=i::,",
        "    i,/--/&|----.    ||*X$-$$xX&8$&888@||-\\$*$*==i;,-.",
        "   i, --//-\\\\-       ||XX\\-/$$$$&888@8@|x\\&x$X*x=+;,..",
        "  ;:     |-\\         ||X*=+|X$8&&88&8&8|xx&XX$**=i;:,.",
        " ;; ... \\i;|       .\\|/Xx*=*x$-X$&$XXx88/*X&xx*==i;:,.",
        "--  -.\\\\;:::       .:///xxXX$x-//$$$x$--&X*x$x**=i;:,.",
        "*+-----=+:,,         ,///x$X\\*++*x$$x--/x$-Xxxx*=i;:,.",
        "---//&\\\\--:          .,||*X\\\\+=+=*x$/i\\\\\\8@8-Xx=+i;:,.",
        "    /\\                .|\\xx\\:;++=X$$8--&8&&88&$X-+i;,-",
        "    |+/---            |||X|i;i++*X$$------/8&$$Xx=+;,.",
        "    /|X/*x/           |||$/--i+=*xX----==*x/&$X**+i;,.",
        "     //+| -:        ..:|/-xX/===*x\\+=+i+==*xX$x=*+i;,.",
        "      /X||        ..-\\;ii+=x$|===-+i+i;i++*XX$X*=+i:,.",
        "       /\\       ..----i++==xX\\++i-ii\\,;ii=x*x$x*=+i:,.",
        "      |+      --------+++++*=i;;:,--..:;;i=**===i;;:,.",
        "       /;-----;;;;i\\-ii-;;;ii::,,.   ..,::/i+;;;;:,,.",
        "         ..--....../:-/:,,,.,,,|.      ....,,,,,,...",
    ],
}

def _law_bar(count, width=26):
    # "18/20" -> a filled evidence bar; anything else -> None
    try:
        num, den = str(count).split("/")
        frac = max(0.0, min(1.0, int(num) / max(1, int(den))))
    except (ValueError, AttributeError):
        return None
    filled = round(frac * width)
    return "█" * filled + "░" * (width - filled)

def _animate_card(build, final_lines, c, stats, card, truth_total):
    # a four-act reveal, played in the terminal's alternate screen so nothing
    # scrolls or tears, then the static card is printed to the real screen:
    #   I.   the read     — your real history flickers past, sessions count up
    #   II.  the etching  — the engraving develops from faint texture to linework
    #   III. the verdict  — archetype and stats land, evidence bars fill
    #   IV.  the confession — the uncomfortable one types itself in red
    import time, shutil, random
    out = sys.stdout
    term = shutil.get_terminal_size((80, 24))
    if term.lines < len(final_lines) + 1 or not sys.stdout.isatty():
        return False

    def frame(lines):
        out.write("\x1b[H" + "\n".join(lines))
        out.flush()

    import math
    ease = lambda t: 0.5 * (1 - math.cos(math.pi * min(1.0, max(0.0, t))))

    def blank_screen():
        return [" " * term.columns for _ in range(term.lines - 1)]

    def centered(screen, text, row=None):
        mid = row if row is not None else (term.lines - 1) // 2
        pad = max(0, (term.columns - len(text)) // 2)
        screen[mid] = (" " * pad + text).ljust(term.columns)[: term.columns]
        return mid

    entered = False
    try:
        out.write("\x1b[?1049h\x1b[?25l\x1b[2J")
        entered = True
        # title card: a studio beat in the dark
        frame([c["dim"] + l + c["reset"] for l in blank_screen()])
        time.sleep(0.5)
        title = blank_screen()
        mid = centered(title, "d i t t o")
        frame([(c["dim"] + l + c["reset"]) if r != mid else (c["cream"] + l + c["reset"]) for r, l in enumerate(title)])
        time.sleep(1.3)
        frame([c["dim"] + l + c["reset"] for l in blank_screen()])
        time.sleep(0.45)
        # act I: the read — fragments of their own mined laws surface from the dark
        rng = random.Random(7)
        frags = [law.get("text", "") for law in card.get("laws", [])[:3] if law.get("text")]
        frags += [card.get("archetype", ""), "reading your sessions", "keeping only the words you typed"]
        frags = [f for f in frags if f]
        sessions = int(stats.get("sessions") or 0)
        rain = []
        for _ in range(16):
            f = frags[rng.randrange(len(frags))]
            col = rng.randrange(2, max(3, term.columns - len(f) - 2))
            row = rng.randrange(1, max(2, term.lines - 2))
            rain.append((row, col, f))
        steps = 26
        for s in range(steps):
            screen = blank_screen()
            visible = int(len(rain) * ease((s + 1) / steps) * 1.2)
            for i, (row, col, f) in enumerate(rain):
                if i < visible and row < len(screen):
                    line = screen[row]
                    screen[row] = (line[:col] + f + line[col + len(f):])[: term.columns]
            n = int(sessions * ease((s + 1) / steps))
            mid = centered(screen, f"reading {n:,} sessions")
            styled = []
            for r, line in enumerate(screen):
                if r == mid:
                    styled.append(c["bold"] + c["yellow"] + line + c["reset"])
                else:
                    styled.append(c["dim"] + line + c["reset"])
            frame(styled)
            time.sleep(0.085)
        time.sleep(0.6)
        # cut to black
        frame([c["dim"] + l + c["reset"] for l in blank_screen()])
        time.sleep(0.4)
        out.write("\x1b[2J")
        # act II: the etching — texture first, ink later, contour strokes last
        for level in range(1, 16):
            frame(build(art_level=level, bar_frac=0.0, truth_n=0, show_data=False))
            time.sleep(0.15)
        time.sleep(0.65)
        # act III: the verdict — archetype and stats land, then each bar fills alone
        frame(build(art_level=99, bar_frac=[0, 0, 0], truth_n=0, show_data=True))
        time.sleep(0.8)
        for b in range(3):
            for s in range(1, 9):
                fracs = [1.0 if i < b else (ease(s / 8) if i == b else 0.0) for i in range(3)]
                frame(build(art_level=99, bar_frac=fracs, truth_n=0, show_data=True))
                time.sleep(0.05)
            time.sleep(0.25)
        time.sleep(0.7)
        # act IV: the confession types itself, one breath first
        for n in range(0, truth_total + 1):
            frame(build(art_level=99, bar_frac=1.0, truth_n=n, show_data=True))
            time.sleep(0.03)
        frame(final_lines)
        time.sleep(1.8)
    except Exception:
        pass
    finally:
        if entered:
            out.write("\x1b[?25h\x1b[?1049l")
            out.flush()
            # land the finished card on the real screen so it stays in scrollback
            try:
                print("\n".join(final_lines))
            except UnicodeEncodeError:
                pass
    return entered

def print_card(card, still=False):
    import textwrap, shutil
    stats = card.get("stats", {})
    months = months_between(stats.get("first_date", ""), stats.get("last_date", ""))
    c = _card_colors()
    term_cols = shutil.get_terminal_size((80, 24)).columns
    inner = max(60, min(term_cols - 3, 126))  # frame interior width
    wide = inner >= 104  # neofetch layout: art left, data right

    def styled_pairs(bar_frac=1.0, truth_n=None, show=True):
        # the data column as (styled, visible) pairs.
        # bar_frac fills the evidence bars partially, truth_n types the
        # confession out character by character, show=False blanks the column
        # while keeping the exact same line count (for animation frames).
        col_w = (inner - 4 - 58) if wide else (inner - 4)
        pairs = []
        archetype = card.get("archetype", "").upper()
        if archetype:
            for part in textwrap.wrap(archetype, col_w) or [""]:
                pairs.append((c["bold"] + c["yellow"] + part + c["reset"], part))
        bits = []
        if stats.get("sessions"):
            bits.append(f"{stats['sessions']:,} sessions")
        if stats.get("tokens"):
            bits.append(f"{fmt_tokens(stats['tokens'])} tokens")
        if months:
            bits.append(f"{months} months")
        if bits:
            joined = " · ".join(bits)
            pairs.append((c["dim"] + joined + c["reset"], joined))
        pairs.append(("", ""))
        numerals = ["I", "II", "III"]
        bar_w = max(18, min(48, col_w - 26))
        for i, law in enumerate(card.get("laws", [])[:3]):
            text = law.get("text", "")
            count = str(law.get("count", "") or "")
            tag = f"LEX {numerals[i]:<4}"
            wrapped = textwrap.wrap(text, col_w - 9) or [""]
            pairs.append((tag + " " + wrapped[0], tag + " " + wrapped[0]))
            for part in wrapped[1:]:
                pairs.append((" " * 9 + part, " " * 9 + part))
            bar = _law_bar(count, width=bar_w)
            if bar:
                frac = bar_frac[i] if isinstance(bar_frac, (list, tuple)) else bar_frac
                filled = bar.count("█")
                k = min(filled, round(filled * frac))
                bar = "█" * k + "░" * (len(bar) - k)
                vis = " " * 9 + bar + f"  {count} sessions"
                sty = " " * 9 + c["yellow"] + bar + c["reset"] + c["dim"] + f"  {count} sessions" + c["reset"]
                pairs.append((sty, vis))
            elif count:
                pairs.append((c["dim"] + " " * 9 + count + c["reset"], " " * 9 + count))
            pairs.append(("", ""))
        truth = card.get("truth", "")
        if truth:
            pairs.append((c["red"] + c["bold"] + "THE UNCOMFORTABLE ONE" + c["reset"], "THE UNCOMFORTABLE ONE"))
            remaining = None if truth_n is None else truth_n
            for part in textwrap.wrap('"' + truth + '"', col_w):
                if remaining is None:
                    shown = part
                elif remaining <= 0:
                    shown = ""
                elif remaining < len(part):
                    shown = part[:remaining] + "▌"  # typing cursor mid-line
                else:
                    shown = part
                if remaining is not None:
                    remaining -= len(part)
                pairs.append((c["red"] + shown + c["reset"], shown))
        if not show:
            pairs = [("", "") for _ in pairs]
        return pairs

    # tier per art character: faint texture first, bright ink later,
    # directional contour strokes last — the etching finishes with linework
    _ramp = " .,:;i+=*xX$&8@"
    def _art_row(row, level):
        if level >= 99:
            return row
        out = []
        for ch in row:
            tier = 15 if ch in "|/\\-" else (_ramp.index(ch) if ch in _ramp else 15)
            out.append(ch if tier <= level else " ")
        return "".join(out).rstrip()

    art = _CARD_ARTS[54]
    tagline = "your working profile, mined from your own sessions"
    footer = "github.com/ohad6k/ditto · run it on your own logs"

    def build(art_level=99, bar_frac=1.0, truth_n=None, show_data=True):
        lines = []

        def fr(text="", style="", visible=None):
            v = visible if visible is not None else text
            pad = " " * max(0, inner - 2 - len(v))
            lines.append(c["dim"] + "│" + c["reset"] + "  " + style + text + c["reset"] + pad + c["dim"] + "│" + c["reset"])

        def divider():
            lines.append(c["dim"] + "├" + "─" * inner + "┤" + c["reset"])

        lines.append("")
        lines.append(c["dim"] + "╭" + "─" * inner + "╮" + c["reset"])
        fr()
        logo_pad = " " * max(0, (inner - 2 - len(_CARD_LOGO[0])) // 2)
        for row in _CARD_LOGO:
            fr(logo_pad + row, style=c["cream"] + c["bold"], visible=logo_pad + row)
        fr()

        if wide:
            # art left, data right
            data = styled_pairs(bar_frac, truth_n, show_data)
            art_w = 56
            n = max(len(art), len(data))
            for i in range(n):
                a = _art_row(art[i], art_level) if i < len(art) else ""
                a_vis = a.ljust(art_w)
                a_sty = c["cream"] + a + c["reset"] + " " * (art_w - len(a))
                d_sty, d_vis = data[i] if i < len(data) else ("", "")
                fr(a_sty + "  " + d_sty, visible=a_vis + "  " + d_vis)
            fr()
            divider()
            combo = tagline + "   " + footer
            if len(combo) <= inner - 4:
                fr(combo, style=c["dim"])
            else:
                fr(tagline, style=c["dim"])
                fr(footer, style=c["dim"])
        else:
            art_pad = " " * max(0, (inner - 2 - max(len(r) for r in art)) // 2)
            for row in art:
                a = _art_row(row, art_level)
                fr(art_pad + a, style=c["cream"], visible=art_pad + a)
            fr()
            fr(tagline, style=c["dim"])
            divider()
            fr()
            for sty, vis in styled_pairs(bar_frac, truth_n, show_data):
                fr(sty, visible=vis)
            fr()
            divider()
            fr(footer, style=c["dim"])
        lines.append(c["dim"] + "╰" + "─" * inner + "╯" + c["reset"])
        lines.append("")
        return lines

    lines = build()
    truth_total = len('"' + card.get("truth", "") + '"') if card.get("truth") else 0
    animate = bool(c["reset"]) and not still and not os.environ.get("DITTO_NO_ANIM")
    try:
        if animate and _animate_card(build, lines, c, stats, card, truth_total):
            pass
        else:
            print("\n".join(lines))
    except UnicodeEncodeError:
        _print_card_plain(card, stats, months)

def _print_card_plain(card, stats, months):
    # fallback for consoles that can't draw the blocks
    width = 62
    line = "+" + "-" * width + "+"
    def row(text=""):
        import textwrap
        for part in textwrap.wrap(text, width - 2) or [""]:
            print("| " + part.ljust(width - 2) + " |")
    print(line)
    row("ditto")
    row()
    row(card.get("archetype", "").upper())
    row()
    bits = []
    if stats.get("sessions"):
        bits.append(f"{stats['sessions']:,} sessions")
    if stats.get("tokens"):
        bits.append(f"{fmt_tokens(stats['tokens'])} tokens")
    if months:
        bits.append(f"{months} months")
    if bits:
        row(" | ".join(bits))
        row()
    for law in card.get("laws", [])[:3]:
        count = law.get("count", "")
        text = law.get("text", "")
        row(f"{text}  [{count}]" if count else text)
    truth = card.get("truth", "")
    if truth:
        row()
        row("the uncomfortable one:")
        row(f'"{truth}"')
    print(line)

CARD_HTML = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ditto card</title>
<style>
  * {{ margin: 0; box-sizing: border-box; }}
  body {{
    background: #cfc9bb; min-height: 100vh; display: grid; place-items: center;
    font-family: Georgia, 'Times New Roman', serif; padding: 40px 16px; color: #17160f;
  }}
  .slab {{
    width: 560px; max-width: 100%;
    background: linear-gradient(160deg, #f2efe6, #e6e2d4);
    border: 1px solid #8f8a7a; border-radius: 14px; padding: 14px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.8), 0 22px 50px rgba(23,22,15,.35);
  }}
  .label {{
    display: flex; border: 1.5px solid #17160f; background: #f8f5ec; margin-bottom: 12px;
  }}
  .label-left {{ flex: 1; padding: 10px 14px; border-right: 1.5px solid #17160f; }}
  .brand {{ font-weight: 700; font-size: 17px; letter-spacing: .28em; }}
  .setline {{ font-size: 10px; letter-spacing: .18em; text-transform: uppercase; margin-top: 3px; color: #444033; }}
  .certline {{ font-size: 10px; letter-spacing: .12em; margin-top: 5px; color: #444033; }}
  .grade {{ width: 116px; display: flex; flex-direction: column; align-items: center; justify-content: center;
    background: #17160f; color: #f2efe6; padding: 8px 6px; }}
  .grade b {{ font-size: 26px; letter-spacing: .02em; font-variant-numeric: tabular-nums; }}
  .grade span {{ font-size: 8.5px; letter-spacing: .3em; text-transform: uppercase; margin-top: 2px; }}
  .card {{
    background: #f8f5ec; border: 1.5px solid #17160f; overflow: hidden;
  }}
  .art {{ position: relative; border-bottom: 1.5px solid #17160f;
    background: repeating-linear-gradient(45deg, #f1eee3 0 6px, #e9e5d6 6px 12px); }}
  .art img {{ display: block; width: 100%; height: 330px; object-fit: cover; object-position: 50% 18%;
    filter: sepia(.12) contrast(1.03); }}
  .art.noart img {{ display: none; }}
  .art.noart {{ height: 140px; }}
  .nameplate {{
    position: absolute; left: 0; right: 0; bottom: 0; text-align: center;
    background: rgba(248,245,236,.94); border-top: 1.5px solid #17160f; padding: 14px 14px 12px;
  }}
  .nameplate b {{ font-size: 22px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; }}
  .nameplate div {{ font-size: 10px; letter-spacing: .3em; text-transform: uppercase; margin-top: 2px; color: #444033; }}
  .stats {{ display: flex; border-bottom: 1.5px solid #17160f; }}
  .stat {{ flex: 1; text-align: center; padding: 12px 4px 10px; }}
  .stat + .stat {{ border-left: 1px solid #b5b0a0; }}
  .stat b {{ display: block; font-size: 22px; font-variant-numeric: tabular-nums; }}
  .stat span {{ font-size: 9px; letter-spacing: .22em; text-transform: uppercase; color: #444033; }}
  .laws {{ padding: 14px 18px 6px; }}
  .laws-head {{ font-size: 9.5px; letter-spacing: .3em; text-transform: uppercase; color: #444033; margin-bottom: 6px; }}
  .law {{ display: flex; align-items: baseline; gap: 10px; padding: 7px 0; }}
  .law + .law {{ border-top: 1px dotted #b5b0a0; }}
  .law i {{ font-style: normal; width: 52px; font-size: 11px; letter-spacing: .12em; }}
  .law p {{ flex: 1; font-size: 14.5px; line-height: 1.35; }}
  .law code {{ font-family: Georgia, serif; font-size: 11px; letter-spacing: .05em;
    border: 1px solid #17160f; padding: 1px 7px; white-space: nowrap; }}
  .truth {{ margin: 10px 18px 16px; border: 1px solid #17160f; padding: 12px 16px; text-align: center;
    background: repeating-linear-gradient(0deg, transparent 0 5px, rgba(23,22,15,.035) 5px 6px); }}
  .truth span {{ display: block; font-size: 9px; letter-spacing: .3em; text-transform: uppercase; margin-bottom: 6px; color: #444033; }}
  .truth p {{ font-size: 14.5px; font-style: italic; line-height: 1.45; }}
  .foot {{
    display: flex; justify-content: space-between; align-items: center;
    font-size: 9.5px; letter-spacing: .16em; text-transform: uppercase; padding: 10px 4px 0; color: #444033;
  }}
  .bars {{ width: 90px; height: 16px;
    background: repeating-linear-gradient(90deg, #17160f 0 2px, transparent 2px 4px, #17160f 4px 5px, transparent 5px 8px); }}
</style>
<div class="slab">
  <div class="label">
    <div class="label-left">
      <div class="brand">DITTO</div>
      <div class="setline">working profile &middot; mined from my own sessions</div>
      <div class="certline">{certline}</div>
    </div>
    <div class="grade"><b>{grade}</b><span>evidence</span></div>
  </div>
  <div class="card">
    <div class="art" id="art">
      <img src="{art_local}" onerror="var a=document.getElementById('art');if(!this.dataset.f){{this.dataset.f=1;this.src='{art_remote}';}}else{{a.className='art noart';}}">
      <div class="nameplate"><b>{archetype}</b><div>{range}</div></div>
    </div>
    <div class="stats">{stats}</div>
    <div class="laws"><div class="laws-head">laws &middot; {lawshead}</div>{laws}</div>
    {truth}
  </div>
  <div class="foot"><div>github.com/ohad6k/ditto &middot; run it on your own logs</div><div class="bars"></div></div>
</div>
"""

def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def render_card_html(card):
    stats = card.get("stats", {})
    months = months_between(stats.get("first_date", ""), stats.get("last_date", ""))
    rng = ""
    if stats.get("first_date") and stats.get("last_date"):
        rng = f"{esc(stats['first_date'][:7])} &rarr; {esc(stats['last_date'][:7])}"
    stat_cells = []
    if stats.get("sessions"):
        stat_cells.append(f"<div class=stat><b>{stats['sessions']:,}</b><span>sessions</span></div>")
    if stats.get("tokens"):
        stat_cells.append(f"<div class=stat><b>{fmt_tokens(stats['tokens'])}</b><span>tokens of me</span></div>")
    if months:
        stat_cells.append(f"<div class=stat><b>{months}</b><span>months</span></div>")
    laws = []
    numerals = ["LEX I", "LEX II", "LEX III"]
    for i, law in enumerate(card.get("laws", [])[:3]):
        count = f"<code>{esc(law['count'])}</code>" if law.get("count") else ""
        laws.append(f"<div class=law><i>{numerals[i]}</i><p>{esc(law.get('text', ''))}</p>{count}</div>")
    truth = ""
    if card.get("truth"):
        truth = (f'<div class="truth"><span>the uncomfortable one</span>'
                 f"<p>&ldquo;{esc(card['truth'])}&rdquo;</p></div>")
    top_laws = card.get("laws", [])
    grade = esc(top_laws[0]["count"]) if top_laws and top_laws[0].get("count") else "&mdash;"
    lawshead = "ranked by distinct session receipts"
    certline = f"no. {stats['messages']:,} messages on record" if stats.get("messages") else "&nbsp;"
    art_remote = "https://raw.githubusercontent.com/ohad6k/ditto/main/assets/ditto.png"
    art_local = art_remote
    local_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ditto.png")
    if os.path.exists(local_png):
        try:
            out_dir = card.get("_out_dir", "")
            art_local = os.path.relpath(local_png, out_dir).replace("\\", "/") if out_dir else art_remote
        except ValueError:
            art_local = art_remote
    return CARD_HTML.format(
        range=rng,
        grade=grade,
        certline=certline,
        art_local=art_local,
        art_remote=art_remote,
        archetype=esc(card.get("archetype", "you")),
        stats="".join(stat_cells),
        laws="".join(laws),
        lawshead=lawshead,
        truth=truth,
    )

def show_card(out_dir, card_path=None, no_open=False, still=False):
    card = load_card(out_dir, card_path)
    card["_out_dir"] = os.path.abspath(out_dir)
    print_card(card, still=still)
    html_path = os.path.join(out_dir, "card.html")
    with open(html_path, "w", encoding="utf-8") as w:
        w.write(render_card_html(card))
    print(f"\nwrote: {html_path}  (open it, screenshot it, post it)")
    print("share what it found: https://github.com/ohad6k/ditto/issues/1")
    if not no_open:
        try:
            import webbrowser
            webbrowser.open("file://" + os.path.abspath(html_path))
        except Exception:
            pass

def print_counts(result, no_redact=False):
    print(f"sessions: {result['sessions']}")
    print(f"your messages: {result['messages']}")
    print(f"tokens (approx): {result['chars'] // 4:,}")
    if result.get("duplicates"):
        print(f"duplicate specs/rules collapsed: {result['duplicates']}  (saves tokens, no signal lost)")
    print(f"secrets/PII redacted: {result['redactions']}" + ("  (redaction OFF)" if no_redact else ""))

def strip_frontmatter(text):
    if not text.startswith("---\n"):
        return text.strip()
    end = text.find("\n---", 4)
    if end == -1:
        return text.strip()
    return text[end + 4:].strip()

def parse_frontmatter(text):
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0] != "---":
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None
    fields = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            return None
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", key) or not value or key in fields:
            return None
        fields[key] = value
    return fields

def has_skill_frontmatter(text, expected_name=None):
    fields = parse_frontmatter(text)
    if not fields or set(("name", "description")) - set(fields):
        return False
    return expected_name is None or fields["name"] == expected_name

def cursor_rule(profile):
    body = strip_frontmatter(profile)
    return f"---\ndescription: ditto user profile\nalwaysApply: true\n---\n\n{body.strip()}\n"

def install_destination(target, repo_dir, home_dir):
    if target == "claude":
        return os.path.join(home_dir, ".claude", "skills", "you", "SKILL.md")
    if target == "codex":
        return os.path.join(home_dir, ".codex", "skills", "you", "SKILL.md")
    if target == "cursor":
        return os.path.join(repo_dir, ".cursor", "rules", "you.mdc")
    if target == "agents":
        return os.path.join(repo_dir, "AGENTS.md")
    if target == "gemini":
        return os.path.join(repo_dir, "GEMINI.md")
    if target == "opencode":
        # OpenCode's global rules file, loaded in every session on every OS
        # (XDG rooted at the home dir, so the same path holds on Windows).
        return os.path.join(home_dir, ".config", "opencode", "AGENTS.md")
    raise ValueError(f"unknown target: {target}")

def install_profile(profile_path, target, repo_dir, home_dir, yes=False, dry_run=False):
    if not os.path.exists(profile_path):
        print(f"profile not found: {profile_path}")
        sys.exit(1)

    with open(profile_path, "r", encoding="utf-8", errors="replace") as fh:
        profile = fh.read()

    if target in ("claude", "codex") and not has_skill_frontmatter(profile):
        print(
            "profile must start with exact name and description frontmatter fields for this target",
            file=sys.stderr,
        )
        sys.exit(1)

    repo_dir = os.path.abspath(repo_dir)
    home_dir = os.path.abspath(os.path.expanduser(home_dir))
    dest = install_destination(target, repo_dir, home_dir)
    print(f"target: {target}")
    print(f"destination: {dest}")

    if dry_run:
        if target in ("agents", "gemini", "opencode"):
            print("dry run: would append or update a marked ditto block")
        else:
            print("dry run: would write profile file")
        return

    os.makedirs(os.path.dirname(dest), exist_ok=True)

    if target in ("agents", "gemini", "opencode"):
        existing = ""
        if os.path.exists(dest):
            with open(dest, "r", encoding="utf-8", errors="replace", newline="") as fh:
                existing = fh.read()
        newline = "\r\n" if "\r\n" in existing else "\n"
        body = strip_frontmatter(profile).replace("\r\n", "\n").replace("\r", "\n")
        body = body.replace("\n", newline)
        block = (
            newline * 2
            + DITTO_START + newline
            + "# ditto profile" + newline * 2
            + body + newline
            + DITTO_END + newline
        )
        has_start = DITTO_START in existing
        has_end = DITTO_END in existing
        if has_start != has_end:
            print("existing Ditto block is incomplete; refusing to modify it", file=sys.stderr)
            sys.exit(1)
        if has_start and has_end:
            if not yes:
                print("ditto profile block already exists. pass --yes to replace it.")
                sys.exit(1)
            pattern = re.compile(
                re.escape(DITTO_START) + r".*?" + re.escape(DITTO_END),
                re.DOTALL,
            )
            updated = pattern.sub(block.strip(), existing)
        else:
            updated = existing.rstrip() + block
        atomic_write_text(dest, updated.lstrip() if not existing else updated)
        print(f"installed: {dest}")
        return

    if target == "cursor":
        profile = cursor_rule(profile)

    if os.path.exists(dest) and not yes:
        print("destination already exists. pass --yes to overwrite it.")
        sys.exit(1)
    atomic_write_text(dest, profile)
    print(f"installed: {dest}")

def configure_console():
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="backslashreplace")
            except (AttributeError, ValueError):
                pass

def resolve_ditto_home(value=None):
    raw = value or os.environ.get("DITTO_HOME") or os.path.join(HOME, ".ditto")
    return os.path.abspath(os.path.expanduser(raw))

def private_paths(ditto_home):
    return {
        "root": ditto_home,
        "active": os.path.join(ditto_home, "active-profile.json"),
        "profiles": os.path.join(ditto_home, "profiles"),
        "segments": os.path.join(ditto_home, "cache", "segments"),
        "segment_indexes": os.path.join(ditto_home, "cache", "segment-indexes"),
        "reports": os.path.join(ditto_home, "cache", "reports"),
        "reductions": os.path.join(ditto_home, "cache", "reductions"),
        "receipts": os.path.join(ditto_home, "cache", "receipts"),
        "salience": os.path.join(ditto_home, "cache", "salience"),
        "packets": os.path.join(ditto_home, "cache", "packets"),
        "scout_reports": os.path.join(ditto_home, "cache", "scout-reports"),
        "domain_drafts": os.path.join(ditto_home, "cache", "domain-drafts"),
        "runs": os.path.join(ditto_home, "runs"),
        "migrations": os.path.join(ditto_home, "migrations"),
        "legacy": os.path.join(ditto_home, "legacy"),
    }

def safe_private_child(ditto_home, *parts):
    if any(".." in re.split(r"[\\/]+", os.fspath(part)) for part in parts):
        raise ValueError("path escapes Ditto private state")
    root = os.path.realpath(resolve_ditto_home(ditto_home))
    candidate = os.path.realpath(os.path.join(root, *parts))
    try:
        contained = os.path.commonpath((root, candidate)) == root
    except ValueError:
        contained = False
    if not contained:
        raise ValueError("path escapes Ditto private state")
    return candidate

def build_plugin_parser():
    parser = argparse.ArgumentParser(prog="ditto.py plugin")
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.add_argument("--ditto-home")
    validate_report_command = sub.add_parser("validate-report")
    validate_report_command.add_argument("--run-id", required=True)
    validate_report_command.add_argument("--report", required=True)
    validate_report_command.add_argument("--ditto-home")
    for name in ("validate-scout", "cache-scout"):
        scout_command = sub.add_parser(name)
        scout_command.add_argument("--run-id", required=True)
        scout_command.add_argument("--packet-hash", required=True)
        scout_command.add_argument("--report", required=True)
        scout_command.add_argument("--ditto-home")
    for name in ("validate-domain", "cache-domain"):
        domain_command = sub.add_parser(name)
        domain_command.add_argument("--run-id", required=True)
        domain_command.add_argument("--domain", required=True, choices=sorted(VALID_DOMAINS))
        domain_command.add_argument("--draft", required=True)
        domain_command.add_argument("--ditto-home")
    validate_pack_command = sub.add_parser("validate-pack")
    validate_pack_command.add_argument("--run-id", required=True)
    validate_pack_command.add_argument("--pack", required=True)
    validate_pack_command.add_argument("--ditto-home")
    assemble_command = sub.add_parser("assemble")
    assemble_command.add_argument("--run-id", required=True)
    assemble_command.add_argument("--ditto-home")
    next_stage_command = sub.add_parser("next-stage")
    next_stage_command.add_argument("--run-id", required=True)
    next_stage_command.add_argument("--ditto-home")
    cache_report = sub.add_parser("cache-report")
    cache_report.add_argument("--run-id", required=True)
    cache_report.add_argument("--report", required=True)
    cache_report.add_argument("--ditto-home")
    activate = sub.add_parser("activate")
    activate.add_argument("--run-id", required=True)
    activation_source = activate.add_mutually_exclusive_group(required=True)
    activation_source.add_argument("--pack")
    activation_source.add_argument("--cached", action="store_true")
    activate.add_argument("--ditto-home")
    profile_path = sub.add_parser("profile-path")
    profile_path.add_argument("--domain", required=True, choices=["work", "design", "write"])
    profile_path.add_argument("--ditto-home")
    migrate_stage = sub.add_parser("migrate-stage")
    migrate_stage.add_argument("--target", required=True, choices=["codex", "claude"])
    migrate_stage.add_argument("--home", default=HOME)
    migrate_stage.add_argument("--ditto-home")
    migrate_cutover = sub.add_parser("migrate-cutover")
    migrate_cutover.add_argument("--migration-id", required=True)
    migrate_cutover.add_argument("--ditto-home")
    migrate_rollback = sub.add_parser("migrate-rollback")
    migrate_rollback.add_argument("--migration-id", required=True)
    migrate_rollback.add_argument("--ditto-home")
    migrate_adapter = sub.add_parser("migrate-adapter")
    migrate_adapter.add_argument("--target", required=True, choices=["agents", "gemini"])
    migrate_adapter.add_argument("--repo", required=True)
    migrate_adapter.add_argument("--mode", required=True, choices=["backup-remove", "restore"])
    migrate_adapter.add_argument("--ditto-home")
    for name in ("preflight", "prepare"):
        command = sub.add_parser(name)
        command.add_argument("--source", choices=["auto", "codex", "claude", "copilot", "opencode", "antigravity"], default="auto")
        command.add_argument("--path")
        command.add_argument("--no-redact", action="store_true")
        command.add_argument("--no-dedupe", action="store_true")
        command.add_argument("--ditto-home")
        mode = command.add_mutually_exclusive_group()
        mode.add_argument("--stage", choices=sorted(STAGE_CONFIGS), help="EXPERIMENTAL adaptive recall stage")
        mode.add_argument("--preview", action="store_true", help="create a bounded starter profile, not the full profile")
        mode.add_argument("--candidate", type=int, choices=range(len(STARTER_CANDIDATES)), help=argparse.SUPPRESS)
        mode.add_argument("--deep", action="store_true")
        mode.add_argument("--deepen-domain", choices=["work", "design", "write"])
        if name == "prepare":
            command.add_argument("--approved-plan-hash")
    return parser

RUN_ID_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}(?:-[0-9]{2})?$")

def load_run_plan(ditto_home, run_id):
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("invalid Ditto run id")
    path = safe_private_child(ditto_home, "runs", run_id, "plan.json")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            plan = json.load(handle)
    except (OSError, ValueError) as exc:
        raise ValueError("Ditto run plan is missing or corrupt") from exc
    if plan.get("run_id") != run_id:
        raise ValueError("Ditto run plan id mismatch")
    return path, plan

def load_assigned_run_report(home, run_id, report_path):
    plan_path, plan = load_run_plan(home, run_id)
    requested = os.path.abspath(report_path)
    selected = next(
        (
            item for item in plan.get("selected_segments", [])
            if os.path.normcase(os.path.abspath(item.get("report_path", "")))
            == os.path.normcase(requested)
        ),
        None,
    )
    if selected is None:
        raise ValueError("report path was not assigned to this Ditto run")
    reports_root = os.path.realpath(os.path.join(plan["run_dir"], "reports"))
    if (
        os.path.realpath(requested) != requested
        or os.path.commonpath((reports_root, requested)) != reports_root
        or not os.path.isfile(requested)
        or os.path.islink(requested)
    ):
        raise ValueError("assigned report must be a regular file inside this Ditto run")
    try:
        with open(requested, "r", encoding="utf-8", errors="strict") as handle:
            report = json.load(handle)
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("assigned report is not valid JSON") from exc
    if report.get("segment_hash") != selected["segment_hash"]:
        raise ValueError("report segment was not selected by this Ditto run")
    segment = dict(selected)
    with open(selected["segment_path"], "r", encoding="utf-8", errors="strict", newline="") as handle:
        segment["text"] = handle.read()
    validate_report(report, segment)
    return plan_path, plan, selected, report, segment

def validate_run_report(args):
    home = resolve_ditto_home(args.ditto_home)
    _, _, selected, _, _ = load_assigned_run_report(home, args.run_id, args.report)
    return {
        "status": "valid",
        "segment_hash": selected["segment_hash"],
    }

def load_run_packet(home, run_id, packet_hash):
    plan_path, plan = load_run_plan(home, run_id)
    try:
        with open(plan["packet_manifest_path"], "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        selected = next(item for item in manifest["packets"] if item["packet_hash"] == packet_hash)
        with open(plan["ledger_path"], "r", encoding="utf-8") as handle:
            ledger = json.load(handle)["receipts"]
    except (OSError, ValueError, KeyError, StopIteration, json.JSONDecodeError) as exc:
        raise ValueError("assigned scout packet is missing or corrupt") from exc
    by_id = {item["receipt_id"]: item for item in ledger}
    try:
        receipts = [by_id[receipt_id] for receipt_id in selected["receipt_ids"]]
    except KeyError as exc:
        raise ValueError("assigned scout packet receipt is missing") from exc
    return plan_path, plan, dict(selected, receipts=receipts)

def validate_run_scout(args, cache=False):
    home = resolve_ditto_home(args.ditto_home)
    plan_path, plan, packet = load_run_packet(home, args.run_id, args.packet_hash)
    try:
        with open(args.report, "r", encoding="utf-8", errors="strict") as handle:
            report = json.load(handle)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("scout report is not valid JSON") from exc
    validate_scout_report(report, packet)
    payload = {"status": "valid", "packet_hash": packet["packet_hash"]}
    if cache:
        cached_path = store_scout_report(report, home, packet)
        paths = set(plan.get("scout_report_paths", []))
        paths.add(cached_path)
        plan["scout_report_paths"] = sorted(paths)
        plan["report_set_hash"] = sha256_text(canonical_json([
            {"path": os.path.basename(path), "sha256": sha256_file(path)}
            for path in plan["scout_report_paths"]
        ]))
        plan["adequate_strata"] = True
        atomic_write_text(plan_path, canonical_json(plan) + "\n")
        payload.update({"status": "cached", "cached_report_path": cached_path})
    return payload

def load_adaptive_evidence(plan):
    try:
        with open(plan["ledger_path"], "r", encoding="utf-8") as handle:
            ledger = json.load(handle)["receipts"]
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("adaptive receipt ledger is missing or corrupt") from exc
    receipts = {item["receipt_id"]: item for item in ledger}
    flattened = {}
    for path in plan.get("scout_report_paths", []):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                report = json.load(handle)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("cached scout report is missing or corrupt") from exc
        if report.get("schema_version") != SCOUT_REPORT_SCHEMA_VERSION:
            raise ValueError("cached scout report uses an outdated schema; run ditto again to re-mine")
        for item in report.get("evidence", []):
            evidence_id = item["evidence_id"]
            if evidence_id in flattened:
                raise ValueError("duplicate evidence id across scout reports")
            quotes = item["quotes"]
            try:
                strata = {
                    receipt_stratum(receipts[quote["receipt_id"]]["source"], quote["date"])
                    for quote in quotes
                }
            except KeyError as exc:
                raise ValueError("scout evidence references missing receipt") from exc
            flattened[evidence_id] = {
                "domain": item["domain"], "kind": item["kind"],
                "scope": item.get("scope", "universal"), "context": item.get("context", ""),
                "sessions": {quote["session_id"] for quote in quotes}, "strata": strata,
                "quote_count": len(quotes), "quotes": quotes,
                "contradictions": item.get("contradictions", []),
                "instruction": item.get("instruction", ""), "implication": item.get("implication", ""),
            }
            if item.get("register") is not None:
                flattened[evidence_id]["register"] = item["register"]
    return flattened

def validate_run_domain(args, cache=False):
    home = resolve_ditto_home(args.ditto_home)
    plan_path, plan = load_run_plan(home, args.run_id)
    evidence = load_adaptive_evidence(plan)
    try:
        with open(args.draft, "r", encoding="utf-8", errors="strict") as handle:
            draft = json.load(handle)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("domain draft is not valid JSON") from exc
    validate_domain_draft(draft, args.domain, evidence, plan)
    payload = {"status": "valid", "domain": args.domain, "evidence_set_hash": draft["evidence_set_hash"]}
    if cache:
        cached_path = store_domain_draft(draft, args.domain, evidence, plan, home)
        paths = dict(plan.get("domain_draft_paths", {}))
        paths[args.domain] = cached_path
        plan["domain_draft_paths"] = dict(sorted(paths.items()))
        atomic_write_text(plan_path, canonical_json(plan) + "\n")
        payload.update({"status": "cached", "cached_draft_path": cached_path,
                        "domain_set_complete": set(paths) == VALID_DOMAINS})
    return payload

def assemble_plugin_run(args):
    home = resolve_ditto_home(args.ditto_home)
    _, plan = load_run_plan(home, args.run_id)
    paths = plan.get("domain_draft_paths", {})
    if set(paths) != VALID_DOMAINS:
        raise ValueError("run requires three validated domain drafts before assembly")
    drafts = {}
    for domain, path in paths.items():
        try:
            with open(path, "r", encoding="utf-8", errors="strict") as handle:
                drafts[domain] = json.load(handle)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("cached domain draft is missing or corrupt") from exc
    return assemble_profile_pack(home, plan, drafts)

def cache_run_report(args):
    home = resolve_ditto_home(args.ditto_home)
    plan_path, plan, selected, report, segment = load_assigned_run_report(
        home,
        args.run_id,
        args.report,
    )
    cached_path = store_report(report, home, segment)

    cached_paths = []
    complete = True
    for item in plan["selected_segments"]:
        if load_cached_report(home, item) is None:
            complete = False
            break
        cached_paths.append(report_cache_path(home, item["segment_hash"]))
    if complete:
        plan["report_paths"] = sorted(cached_paths)
        plan["report_set_hash"] = compute_report_set_hash(plan["report_paths"])
        atomic_write_text(plan_path, canonical_json(plan) + "\n")
    return {
        "status": "cached",
        "segment_hash": selected["segment_hash"],
        "cached_report_path": os.path.abspath(cached_path),
        "report_set_complete": complete,
        "report_set_hash": plan.get("report_set_hash"),
    }

def active_profile_state(ditto_home):
    home = resolve_ditto_home(ditto_home)
    active_path = safe_private_child(home, "active-profile.json")
    if not os.path.exists(active_path):
        return None
    try:
        with open(active_path, "r", encoding="utf-8") as handle:
            active = json.load(handle)
        if active != {"schema_version": "1", "profile_id": "default"}:
            raise ValueError
        current_path = safe_private_child(home, "profiles", "default", "current.json")
        with open(current_path, "r", encoding="utf-8") as handle:
            pointer = json.load(handle)
        version = pointer.get("profile_version", "")
        if (
            pointer.get("schema_version") != "1"
            or pointer.get("profile_id") != "default"
            or not re.fullmatch(r"[a-f0-9]{20}", version)
        ):
            raise ValueError
        version_dir = safe_private_child(home, "profiles", "default", "versions", version)
        manifest, manifest_hash = validate_version_directory(version_dir)
        if manifest["profile_version"] != version or pointer.get("manifest_hash") != manifest_hash:
            raise ValueError
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        raise ValueError("corrupt active profile; run ditto to recover") from None
    return {"home": home, "version_dir": version_dir, "manifest": manifest, "pointer": pointer}

def resolve_profile_paths(ditto_home, domain):
    state = active_profile_state(ditto_home)
    if state is None:
        raise ValueError("no active Ditto profile; run ditto")
    domain_state = state["manifest"]["domains"][domain]
    if domain_state.get("status") != "active":
        raise ValueError(domain_state.get("deepen_instruction") or "run ditto")
    names = [DOMAIN_FILES["work"][0]]
    if domain != "work":
        names.append(DOMAIN_FILES[domain][0])
    paths = [os.path.join(state["version_dir"], name) for name in names]
    for path in paths:
        if not os.path.isfile(path) or sha256_file(path) != state["manifest"]["files"].get(os.path.basename(path)):
            raise ValueError("corrupt active profile; run ditto to recover")
    payload = {
        "status": "active",
        "domain": domain,
        "profile_version": state["manifest"]["profile_version"],
        "paths": paths,
    }
    if state["manifest"].get("origin") == "legacy-migration":
        payload.update({
            "legacy_unverified": True,
            "recovery_instruction": "update ditto to generate an evidence-backed profile",
        })
    return payload

def load_plugin_pack_context(home, run_id, pack_path, quarantine):
    _, plan = load_run_plan(home, run_id)
    expected_pack = os.path.realpath(plan["pack_path"])
    if os.path.realpath(os.path.abspath(pack_path)) != expected_pack:
        raise ValueError("pack path was not assigned to this Ditto run")
    reports = []
    for segment in plan["selected_segments"]:
        report = load_cached_report(home, segment, quarantine=quarantine)
        if report is None:
            raise ValueError("run has an uncached or invalid report")
        reports.append(report)
    evidence = flatten_report_evidence(reports)
    return plan, expected_pack, evidence

def validate_plugin_pack(args):
    home = resolve_ditto_home(args.ditto_home)
    plan, expected_pack, evidence = load_plugin_pack_context(
        home,
        args.run_id,
        args.pack,
        quarantine=False,
    )
    validate_profile_pack(expected_pack, evidence, plan)
    return {"status": "valid", "report_set_hash": plan["report_set_hash"]}

def activate_plugin_run(args):
    home = resolve_ditto_home(args.ditto_home)
    _, plan = load_run_plan(home, args.run_id)
    if args.cached:
        if not plan.get("report_set_hash"):
            raise ValueError("run has no complete cached report set")
        return activate_cached_reduction(home, plan["report_set_hash"])
    plan, expected_pack, evidence = load_plugin_pack_context(
        home,
        args.run_id,
        args.pack,
        quarantine=True,
    )
    return activate_profile_pack(home, expected_pack, evidence, plan)

def plugin_source_result(args):
    if args.path:
        roots = [args.path]
    elif args.source == "auto":
        roots = SOURCES["codex"] + SOURCES["claude"] + SOURCES["copilot"] + SOURCES["opencode"] + SOURCES["antigravity"]
    else:
        roots = SOURCES[args.source]
    files = discover_files(roots)
    if not files:
        raise ValueError("no session logs found; use --path or select an available source")
    result = mine_files(files, args.no_redact, dedupe=not args.no_dedupe)
    if result["sessions"] == 0:
        raise ValueError("no valid user sessions remained after parsing and filtering")
    return result

def build_adaptive_plan(result, stage="A"):
    ledger = build_receipt_ledger(result["records"])
    scored = score_receipts(ledger)
    selected = select_salience_stage(scored, stage)
    config = STAGE_CONFIGS[stage]
    packets = pack_selected_receipts(selected, config["packets"], config["packet_tokens"])
    dates = [item["date"] for item in selected if item["date"] != "undated"]
    return {
        "schema_version": "2",
        "mode": "adaptive",
        "stage": stage,
        "selected_source_tokens": sum(item["tokens"] for item in selected),
        "selected_receipt_ids": [item["receipt_id"] for item in selected],
        "planned_scout_calls": len(packets),
        "planned_domain_reducer_calls": 3,
        "planned_domains": ["design", "work", "write"],
        "corpus_snapshot_hash": sha256_text(canonical_json([
            {"receipt_id": item["receipt_id"], "content_hash": item["content_hash"]}
            for item in ledger
        ])),
        "source_coverage": {
            "sources": sorted({item["source"] for item in selected}),
            "first_date": min(dates) if dates else "undated",
            "last_date": max(dates) if dates else "undated",
        },
        "ledger": scored,
        "packets": packets,
    }

def adaptive_preflight(result, stage="A"):
    plan = build_adaptive_plan(result, stage)
    return {
        key: value for key, value in plan.items()
        if key not in {"ledger", "packets"}
    } | {
        "packet_hashes": [packet["packet_hash"] for packet in plan["packets"]],
        "writes_private_state": False,
    }

def render_receipt_packet(packet):
    sections = []
    for item in packet["receipts"]:
        sections.append(
            f"===== receipt:{item['receipt_id']} session:{item['session_id']} "
            f"source:{item['source']} date:{item['date']} =====\n{item['text']}"
        )
    return "\n\n".join(sections) + "\n"

def prepare_adaptive_run(args):
    home = resolve_ditto_home(args.ditto_home)
    result = plugin_source_result(args)
    stage = args.stage or "A"
    prepared = build_adaptive_plan(result, stage)
    frozen_identity = {key: value for key, value in prepared.items() if key not in {"ledger", "packets"}}
    frozen_identity["packet_hashes"] = [packet["packet_hash"] for packet in prepared["packets"]]
    plan_hash = sha256_text(canonical_json(frozen_identity))
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    base_run_id = f"{timestamp}-{plan_hash[:8]}"
    run_id = base_run_id
    suffix = 1
    while os.path.exists(safe_private_child(home, "runs", run_id)):
        run_id = f"{base_run_id}-{suffix:02d}"
        suffix += 1
    run_dir = safe_private_child(home, "runs", run_id)
    packets_dir = os.path.join(run_dir, "packets")
    pack_dir = os.path.join(run_dir, "pack")
    os.makedirs(packets_dir, exist_ok=False)
    os.makedirs(pack_dir, exist_ok=False)

    ledger_path = os.path.join(run_dir, "ledger.json")
    atomic_write_text(ledger_path, canonical_json({
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "receipts": prepared["ledger"],
    }) + "\n")
    packet_paths = []
    manifest_packets = []
    for packet in prepared["packets"]:
        packet_path = os.path.join(packets_dir, packet["packet_hash"] + ".txt")
        atomic_write_text(packet_path, render_receipt_packet(packet))
        packet_paths.append(packet_path)
        manifest_packets.append({key: value for key, value in packet.items() if key != "receipts"} | {
            "packet_path": packet_path,
        })
    manifest_path = os.path.join(run_dir, "packet-manifest.json")
    atomic_write_text(manifest_path, canonical_json({
        "schema_version": PACKET_SCHEMA_VERSION,
        "packets": manifest_packets,
    }) + "\n")
    plan_path = os.path.join(run_dir, "plan.json")
    run_plan = frozen_identity | {
        "run_id": run_id,
        "run_dir": run_dir,
        "plan_hash": plan_hash,
        "plan_path": plan_path,
        "ledger_path": ledger_path,
        "packet_manifest_path": manifest_path,
        "packet_paths": packet_paths,
        "pack_path": pack_dir,
        "scout_report_paths": [],
        "domain_draft_paths": {},
    }
    atomic_write_text(plan_path, canonical_json(run_plan) + "\n")
    return run_plan

def domain_needs_deepening(draft):
    if draft.get("status") != "active":
        return True
    coverage = draft.get("coverage", {})
    return (
        not draft.get("rules")
        or coverage.get("evidence_items", 0) < 2
        or coverage.get("distinct_sessions", 0) < 2
        or coverage.get("strata", 0) < 2
        or coverage.get("unresolved_contradictions", 0) > 0
    )

def build_next_stage_plan(ditto_home, run_id):
    home = resolve_ditto_home(ditto_home)
    _, prior = load_run_plan(home, run_id)
    if prior.get("stage") != "A":
        raise ValueError("next-stage requires a completed adaptive Stage A run")
    drafts = {}
    for domain, path in prior.get("domain_draft_paths", {}).items():
        try:
            with open(path, "r", encoding="utf-8", errors="strict") as handle:
                drafts[domain] = json.load(handle)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("completed Stage A domain draft is missing or corrupt") from exc
    if set(drafts) != VALID_DOMAINS:
        raise ValueError("complete all three Stage A domain drafts before planning expansion")
    planned_domains = sorted(domain for domain, draft in drafts.items() if domain_needs_deepening(draft))
    if not planned_domains:
        raise ValueError("all adaptive domains are already stable")
    try:
        with open(prior["ledger_path"], "r", encoding="utf-8", errors="strict") as handle:
            ledger_value = json.load(handle)
        ledger = ledger_value.get("receipts", []) if isinstance(ledger_value, dict) else ledger_value
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("frozen adaptive ledger is missing or corrupt") from exc
    eligible = [item for item in ledger if set(item.get("domain_hints", [])) & set(planned_domains)]
    selected = select_salience_stage(eligible, "B", prior.get("selected_receipt_ids", []))
    config = STAGE_CONFIGS["B"]
    packets = pack_selected_receipts(selected, config["packets"], config["packet_tokens"])
    identity = {
        "parent_run_id": run_id, "stage": "B", "planned_domains": planned_domains,
        "selected_receipt_ids": [item["receipt_id"] for item in selected],
        "packet_hashes": [item["packet_hash"] for item in packets],
        "corpus_snapshot_hash": prior["corpus_snapshot_hash"],
    }
    stage_id = "B-" + sha256_text(canonical_json(identity))[:8]
    stage_dir = safe_private_child(home, "runs", run_id, "stages", stage_id)
    packets_dir = os.path.join(stage_dir, "packets")
    os.makedirs(packets_dir, exist_ok=True)
    packet_paths = []
    for packet in packets:
        path = os.path.join(packets_dir, packet["packet_hash"] + ".txt")
        atomic_write_text(path, render_receipt_packet(packet))
        packet_paths.append(path)
    next_plan = {
        "schema_version": "2", "parent_run_id": run_id, "stage": "B", "stage_id": stage_id,
        "stage_dir": stage_dir, "corpus_snapshot_hash": prior["corpus_snapshot_hash"],
        "planned_domains": planned_domains,
        "selected_receipt_ids": [item["receipt_id"] for item in selected],
        "selected_source_tokens": sum(item["tokens"] for item in selected),
        "planned_scout_calls": len(packets), "planned_domain_reducer_calls": len(planned_domains),
        "packet_hashes": [item["packet_hash"] for item in packets], "packet_paths": packet_paths,
        "cached_scout_reports": len(prior.get("scout_report_paths", [])),
        "reused_domain_drafts": sorted(set(VALID_DOMAINS) - set(planned_domains)),
        "full_history_option": "prepare a separate full-history stage with explicit approval",
    }
    plan_path = os.path.join(stage_dir, "plan.json")
    next_plan["plan_path"] = plan_path
    atomic_write_text(plan_path, canonical_json(next_plan) + "\n")
    return next_plan

def plugin_plan_for_args(args, write=False):
    result = plugin_source_result(args)
    home = resolve_ditto_home(args.ditto_home)
    if args.deepen_domain:
        raise ValueError(
            "targeted deepening requires an active profile; run the full Ditto setup first"
        )
    if args.stage is not None:
        return adaptive_preflight(result, args.stage)
    if args.preview or args.candidate is not None:
        candidate_index = DEFAULT_CANDIDATE_INDEX if args.candidate is None else args.candidate
        plan = build_preflight(result, home, candidate_index, write=write)
    else:
        plan = build_deep_preflight(result, home, write=write)
    identity = {key: value for key, value in plan.items() if key != "approval_hash"}
    return dict(plan, approval_hash=sha256_text(canonical_json(identity)))

def prepare_plugin_run(args):
    if args.stage is not None:
        return prepare_adaptive_run(args)
    home = resolve_ditto_home(args.ditto_home)
    approved = plugin_plan_for_args(args, write=False)
    if args.approved_plan_hash != approved["approval_hash"]:
        raise ValueError("prepared plan does not match the approved preflight hash; rerun preflight and reapprove")
    plan = plugin_plan_for_args(args, write=True)
    if args.approved_plan_hash != plan["approval_hash"]:
        raise ValueError("source or cache changed after approval; rerun preflight and reapprove")
    plan_hash = sha256_text(canonical_json(plan))
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    base_run_id = f"{timestamp}-{plan_hash[:8]}"
    run_id = base_run_id
    suffix = 1
    while os.path.exists(safe_private_child(home, "runs", run_id)):
        run_id = f"{base_run_id}-{suffix:02d}"
        suffix += 1
    run_dir = safe_private_child(home, "runs", run_id)
    segments_dir = os.path.join(run_dir, "segments")
    reports_dir = os.path.join(run_dir, "reports")
    pack_dir = os.path.join(run_dir, "pack")
    os.makedirs(segments_dir, exist_ok=False)
    os.makedirs(reports_dir, exist_ok=False)
    os.makedirs(pack_dir, exist_ok=False)

    selected_with_paths = []
    cached_report_paths = []
    for segment in plan["selected_segments"]:
        segment_hash_value = segment["segment_hash"]
        source_path = segment_file_path(home, segment_hash_value)
        assigned_segment = os.path.join(segments_dir, segment_hash_value + ".txt")
        with open(source_path, "rb") as handle:
            atomic_write_bytes(assigned_segment, handle.read())
        assigned_report = os.path.join(reports_dir, segment_hash_value + ".json")
        cached = segment_hash_value in set(plan["cached_segment_hashes"])
        assigned = dict(segment)
        assigned.update({
            "segment_path": assigned_segment,
            "report_path": assigned_report,
            "cached": cached,
        })
        selected_with_paths.append(assigned)
        if cached:
            cached_report_paths.append(report_cache_path(home, segment_hash_value))

    dates = [
        value
        for segment in plan["selected_segments"]
        for value in (segment["first_date"], segment["last_date"])
        if value != "undated"
    ]
    run_plan = {
        "schema_version": "1",
        "run_id": run_id,
        "run_dir": run_dir,
        "plan_hash": plan_hash,
        "mode": plan["mode"],
        "profile_scope": plan["profile_scope"],
        "quality_default": plan["quality_default"],
        "notice": plan["notice"],
        "candidate_index": plan["candidate_index"],
        "target_domain": args.deepen_domain,
        "selected_source_tokens": plan["selected_source_tokens"],
        "planned_worker_calls": plan["planned_worker_calls"],
        "planned_reducer_calls": plan["planned_reducer_calls"],
        "selected_segments": selected_with_paths,
        "segment_hashes": [item["segment_hash"] for item in selected_with_paths],
        "source_coverage": {
            "sources": sorted({segment["source"] for segment in plan["selected_segments"]}),
            "first_date": min(dates) if dates else "undated",
            "last_date": max(dates) if dates else "undated",
        },
        "adequate_strata": plan["adequate_strata"],
        "pack_path": pack_dir,
        "report_paths": sorted(cached_report_paths),
        "report_set_hash": plan["report_set_hash"],
    }
    atomic_write_text(
        os.path.join(run_dir, "selected-segments.json"),
        canonical_json({"segments": selected_with_paths}) + "\n",
    )
    atomic_write_text(os.path.join(run_dir, "plan.json"), canonical_json(run_plan) + "\n")
    return run_plan

def plugin_main(argv):
    parser = build_plugin_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            home = resolve_ditto_home(args.ditto_home)
            active = active_profile_state(home)
            payload = (
                {"status": "missing", "ditto_home": home}
                if active is None
                else {
                    "status": "active",
                    "ditto_home": home,
                    "profile_version": active["manifest"]["profile_version"],
                    "domains": active["manifest"]["domains"],
                    "card_path": (
                        os.path.join(active["version_dir"], "card.json")
                        if "card.json" in active["manifest"].get("files", {})
                        else None
                    ),
                }
            )
            if active is not None and active["manifest"].get("origin") == "legacy-migration":
                payload.update({
                    "legacy_unverified": True,
                    "recovery_instruction": "update ditto to generate an evidence-backed profile",
                })
        elif args.command == "preflight":
            payload = plugin_plan_for_args(args, write=False)
        elif args.command == "prepare":
            payload = prepare_plugin_run(args)
        elif args.command == "validate-report":
            payload = validate_run_report(args)
        elif args.command == "validate-scout":
            payload = validate_run_scout(args, cache=False)
        elif args.command == "cache-scout":
            payload = validate_run_scout(args, cache=True)
        elif args.command == "validate-domain":
            payload = validate_run_domain(args, cache=False)
        elif args.command == "cache-domain":
            payload = validate_run_domain(args, cache=True)
        elif args.command == "validate-pack":
            payload = validate_plugin_pack(args)
        elif args.command == "assemble":
            payload = assemble_plugin_run(args)
        elif args.command == "next-stage":
            payload = build_next_stage_plan(args.ditto_home, args.run_id)
        elif args.command == "cache-report":
            payload = cache_run_report(args)
        elif args.command == "activate":
            payload = activate_plugin_run(args)
        elif args.command == "profile-path":
            payload = resolve_profile_paths(args.ditto_home, args.domain)
        elif args.command == "migrate-stage":
            payload = stage_legacy_migration(args.target, args.home, args.ditto_home)
        elif args.command == "migrate-cutover":
            payload = cutover_legacy_migration(args.migration_id, args.ditto_home)
        elif args.command == "migrate-rollback":
            payload = rollback_legacy_migration(args.migration_id, args.ditto_home)
        elif args.command == "migrate-adapter":
            payload = migrate_adapter_block(args.target, args.repo, args.ditto_home, args.mode)
        else:
            raise ValueError("unsupported plugin command")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None
    print(json.dumps(payload, sort_keys=True))

DITTO_VERSION = "0.3.8"
MCP_PROTOCOL_VERSION = "2025-06-18"

def mcp_tool_definitions():
    return [
        {
            "name": "load_ditto_profile",
            "description": (
                "Load the user's Ditto profile so you act like them instead of starting cold. "
                "Call this before working on their task. domain 'work' covers execution, "
                "debugging, planning, and shipping; 'design' covers UI/UX and visual taste; "
                "'write' covers their writing voice. Returns the mined profile text, or a "
                "recovery instruction if no profile is active yet."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "enum": sorted(VALID_DOMAINS),
                        "description": "Which profile to load. Defaults to work.",
                    }
                },
                "required": [],
            },
        }
    ]

def mcp_load_profile_text(ditto_home, domain):
    payload = resolve_profile_paths(ditto_home, domain)
    parts = []
    for path in payload["paths"]:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read().strip()
        if text:
            parts.append(text)
    header = "# Ditto {0} profile (version {1})".format(domain, payload["profile_version"])
    body = "\n\n".join(parts)
    if payload.get("legacy_unverified"):
        body += "\n\n(legacy-migration profile, unverified: {0})".format(
            payload.get("recovery_instruction", "")
        )
    return header + "\n\n" + body

def mcp_result(msg_id, result):
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}

def mcp_error(msg_id, code, message):
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}

def mcp_tool_text(msg_id, text, is_error=False):
    return mcp_result(msg_id, {"content": [{"type": "text", "text": text}], "isError": is_error})

def mcp_handle(message, ditto_home):
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return mcp_error(None, -32600, "invalid request")
    if "id" not in message:
        return None  # a JSON-RPC notification is never answered
    msg_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}
    if method == "initialize":
        requested = params.get("protocolVersion")
        protocol = requested if isinstance(requested, str) else MCP_PROTOCOL_VERSION
        return mcp_result(msg_id, {
            "protocolVersion": protocol,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "ditto", "version": DITTO_VERSION},
        })
    if method == "ping":
        return mcp_result(msg_id, {})
    if method == "tools/list":
        return mcp_result(msg_id, {"tools": mcp_tool_definitions()})
    if method == "tools/call":
        if params.get("name") != "load_ditto_profile":
            return mcp_error(msg_id, -32602, "unknown tool: {0}".format(params.get("name")))
        domain = (params.get("arguments") or {}).get("domain") or "work"
        if domain not in VALID_DOMAINS:
            return mcp_tool_text(msg_id, "unknown domain: {0}".format(domain), is_error=True)
        try:
            text = mcp_load_profile_text(ditto_home, domain)
        except ValueError as exc:
            return mcp_tool_text(msg_id, str(exc), is_error=True)
        except OSError:
            return mcp_tool_text(msg_id, "corrupt active profile; run ditto to recover", is_error=True)
        return mcp_tool_text(msg_id, text)
    return mcp_error(msg_id, -32601, "method not found: {0}".format(method))

def mcp_main(argv):
    parser = argparse.ArgumentParser(prog="ditto.py mcp")
    parser.add_argument("--ditto-home")
    args = parser.parse_args(argv)
    ditto_home = resolve_ditto_home(args.ditto_home)
    out = sys.stdout
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            out.write(json.dumps(mcp_error(None, -32700, "parse error")) + "\n")
            out.flush()
            continue
        response = mcp_handle(message, ditto_home)
        if response is not None:
            out.write(json.dumps(response) + "\n")
            out.flush()

def legacy_main():
    ap = argparse.ArgumentParser(description="mine your AI sessions into a model of you")
    ap.add_argument("--source", choices=["auto", "codex", "claude", "copilot", "opencode", "antigravity"], default="auto")
    ap.add_argument("--path", help="a folder of .jsonl session logs to read instead")
    ap.add_argument("--out", default="ditto-out")
    ap.add_argument("--chunks", type=int, default=20)
    ap.add_argument("--dry-run", action="store_true", help="show counts and output paths without writing files")
    ap.add_argument("--no-redact", action="store_true", help="skip redaction (NOT recommended)")
    ap.add_argument("--no-dedupe", action="store_true", help="keep verbatim-duplicate long messages (re-pasted specs / injected rules)")
    ap.add_argument("--card", nargs="?", const="", metavar="CARD_JSON",
                    help="render your profile card (terminal + card.html) from ditto-out/card.json")
    ap.add_argument("--no-open", action="store_true", help="don't open card.html in the browser")
    ap.add_argument("--still", action="store_true", help="print the card without the reveal animation")
    ap.add_argument("--install", metavar="PROFILE", help="install an existing generated you.md profile")
    ap.add_argument("--target", choices=["claude", "codex", "cursor", "agents", "gemini", "opencode"], help="where to install --install")
    ap.add_argument("--repo", default=".", help="repo path for cursor/AGENTS.md/GEMINI.md installs")
    ap.add_argument("--yes", action="store_true", help="overwrite/replace an existing install")
    ap.add_argument("--home", default=HOME, help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.install:
        if not args.target:
            print("--install requires --target")
            sys.exit(1)
        install_profile(args.install, args.target, args.repo, args.home, args.yes, args.dry_run)
        return

    if args.card is not None:
        show_card(args.out, args.card or None, args.no_open, still=args.still)
        return

    roots = []
    if args.path:
        roots = [args.path]
    elif args.source == "auto":
        roots = SOURCES["codex"] + SOURCES["claude"] + SOURCES["copilot"] + SOURCES["opencode"] + SOURCES["antigravity"]
    else:
        roots = SOURCES[args.source]

    files = discover_files(roots)
    if not files:
        print("no session logs found. try --path <folder> or --source codex/claude/copilot.")
        print("looked in:", ", ".join(roots))
        sys.exit(1)

    result = mine_files(files, args.no_redact, dedupe=not args.no_dedupe)

    if result["sessions"] == 0:
        print("no valid user sessions remained after parsing and filtering", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print("dry run: no files written")
        print("looked in:", ", ".join(roots))
        print(f"jsonl files: {len(files)}")
        print_counts(result, args.no_redact)
        print(f"would write: {args.out}/you-corpus.txt  +  chunks in {args.out}/chunks/")
        return

    chunk_count = write_outputs(result["blocks"], args.out, args.chunks, stats_result=result)

    print_counts(result, args.no_redact)
    print(f"wrote: {args.out}/you-corpus.txt  +  {chunk_count} chunks in {args.out}/chunks/")
    print(f"\nnext: open your coding agent, paste MINING_PROMPT.md, point it at {args.out}/chunks/, merge into you.md")

def main():
    configure_console()
    if len(sys.argv) > 1 and sys.argv[1] == "plugin":
        plugin_main(sys.argv[2:])
        return
    if len(sys.argv) > 1 and sys.argv[1] == "mcp":
        mcp_main(sys.argv[2:])
        return
    legacy_main()

if __name__ == "__main__":
    main()
