#!/usr/bin/env python3
"""
ditto - turn your own AI coding sessions into a model of how you think.

It reads your local session logs (Codex / Claude Code / Copilot CLI jsonl),
keeps ONLY the words you typed, redacts secrets + personal info, and writes one
clean corpus + chunks. You then point a coding agent at the chunks with
MINING_PROMPT.md to produce your `you.md`.

100% local. Your logs never leave your machine. No network calls. Stdlib only.

Usage:
    python ditto.py                     # auto-detect Codex + Claude + Copilot logs
    python ditto.py --dry-run           # preview counts without writing files
    python ditto.py --card              # render your profile card (after mining)
    python ditto.py --install you.md --target codex
    python ditto.py --source codex      # only ~/.codex/sessions
    python ditto.py --source copilot    # only ~/.copilot/session-state
    python ditto.py --path ./logs       # a folder of jsonl you point at
    python ditto.py --chunks 20         # how many chunks to split into
    python ditto.py --no-redact         # DANGER: skip redaction (not recommended)
"""
import argparse, glob, hashlib, json, os, re, shutil, sys, tempfile, time, uuid

HOME = os.path.expanduser("~")
SOURCES = {
    "codex":   [os.path.join(HOME, ".codex", "sessions")],
    "claude":  [os.path.join(HOME, ".claude", "projects")],
    "copilot": [os.path.join(HOME, ".copilot", "session-state")],
}
DITTO_START = "<!-- ditto profile:start -->"
DITTO_END = "<!-- ditto profile:end -->"

EXTRACTION_SCHEMA_VERSION = "1"
SEGMENT_SCHEMA_VERSION = "1"
REPORT_SCHEMA_VERSION = "1"
PROMPT_SCHEMA_VERSION = "1"
REDUCER_SCHEMA_VERSION = "1"

STARTER_CANDIDATES = (
    {"segments": 4, "segment_tokens": 25_000},
    {"segments": 6, "segment_tokens": 20_000},
    {"segments": 8, "segment_tokens": 20_000},
)
STARTER_MAX_SOURCE_TOKENS = 160_000
STARTER_MAX_MODEL_CALLS = 9
DEFAULT_CANDIDATE_INDEX = 0
DEEP_SEGMENT_TOKENS = 20_000
MAX_REPORT_BYTES = 8_192
MAX_EVIDENCE_PER_REPORT = 12
MAX_QUOTE_CHARS = 200

# --- redaction: run BEFORE any of your text is written or seen by an agent ---
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
    (re.compile(r"\+?\d[\d\s\-]{8,}\d"),                 "[PHONE]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),         "[IP]"),
    (re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*\S+"), r"\1=[REDACTED]"),
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
)

def is_injected_context(text):
    stripped = text.lstrip()
    return any(stripped.startswith(prefix) for prefix in INJECTED_CONTEXT_PREFIXES)

def user_messages(path):
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"role"' not in line and '"user"' not in line and "user.message" not in line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                # Copilot CLI: {type:'user.message', data:{content, source}, timestamp}
                if o.get("type") == "user.message":
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
                    if not t or is_injected_context(t):
                        continue
                    if is_pasted_log(t):
                        continue
                    ts = (o.get("timestamp", "") or "")[:10]
                    out.append((ts, t))
    except Exception:
        pass
    return out

def discover_files(roots):
    files = []
    for r in roots:
        files += glob.glob(os.path.join(r, "**", "*.jsonl"), recursive=True)
    return sorted(set(files))

def session_label(path):
    """Label a session block by parent dir + filename.

    Copilot logs are all named events.jsonl under a per-session directory, so
    the bare filename collapses every block header to the same string. Prefix
    the parent directory (the session id for Copilot, the project for Claude)
    to keep sessions distinguishable in the corpus.
    """
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
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
        if quarantine and os.path.exists(path):
            stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            quarantine_path = path + ".corrupt-" + stamp
            if os.path.exists(quarantine_path):
                quarantine_path += "-" + uuid.uuid4().hex[:8]
            os.replace(path, quarantine_path)
        return None

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
    reduction_cache_hit = bool(
        report_set_hash
        and os.path.isdir(
            os.path.join(
                private_paths(ditto_home)["reductions"],
                REDUCER_SCHEMA_VERSION,
                report_set_hash,
            )
        )
    )
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
    hits = {
        value for value in hashes if os.path.isfile(report_cache_path(ditto_home, value))
    }
    worker_calls, reducer_calls = planned_call_counts(hashes, hits, False)
    return {
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
        "report_set_hash": None,
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

def print_card(card):
    stats = card.get("stats", {})
    months = months_between(stats.get("first_date", ""), stats.get("last_date", ""))
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
    <div class="grade"><b>{grade}</b><span>consensus</span></div>
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
    reports = ""
    for law in top_laws:
        c = str(law.get("count", ""))
        if "/" in c:
            reports = c.split("/", 1)[1].strip()
            break
    lawshead = f"ranked by how many of {esc(reports)} agents found each" if reports else "ranked by how many agents found each"
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

def show_card(out_dir, card_path=None, no_open=False):
    card = load_card(out_dir, card_path)
    card["_out_dir"] = os.path.abspath(out_dir)
    print_card(card)
    html_path = os.path.join(out_dir, "card.html")
    with open(html_path, "w", encoding="utf-8") as w:
        w.write(render_card_html(card))
    print(f"\nwrote: {html_path}  (open it, screenshot it, post it)")
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
        if target in ("agents", "gemini"):
            print("dry run: would append or update a marked ditto block")
        else:
            print("dry run: would write profile file")
        return

    os.makedirs(os.path.dirname(dest), exist_ok=True)

    if target in ("agents", "gemini"):
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
    cache_report = sub.add_parser("cache-report")
    cache_report.add_argument("--run-id", required=True)
    cache_report.add_argument("--report", required=True)
    cache_report.add_argument("--ditto-home")
    for name in ("preflight", "prepare"):
        command = sub.add_parser(name)
        command.add_argument("--source", choices=["auto", "codex", "claude", "copilot"], default="auto")
        command.add_argument("--path")
        command.add_argument("--no-redact", action="store_true")
        command.add_argument("--no-dedupe", action="store_true")
        command.add_argument("--ditto-home")
        mode = command.add_mutually_exclusive_group()
        mode.add_argument("--candidate", type=int, choices=range(len(STARTER_CANDIDATES)))
        mode.add_argument("--deep", action="store_true")
        mode.add_argument("--deepen-domain", choices=["work", "design", "write"])
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

def cache_run_report(args):
    home = resolve_ditto_home(args.ditto_home)
    plan_path, plan = load_run_plan(home, args.run_id)
    requested = os.path.abspath(args.report)
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

def plugin_source_result(args):
    if args.path:
        roots = [args.path]
    elif args.source == "auto":
        roots = SOURCES["codex"] + SOURCES["claude"] + SOURCES["copilot"]
    else:
        roots = SOURCES[args.source]
    files = discover_files(roots)
    if not files:
        raise ValueError("no session logs found; use --path or select an available source")
    result = mine_files(files, args.no_redact, dedupe=not args.no_dedupe)
    if result["sessions"] == 0:
        raise ValueError("no valid user sessions remained after parsing and filtering")
    return result

def plugin_plan_for_args(args, write=False):
    result = plugin_source_result(args)
    home = resolve_ditto_home(args.ditto_home)
    if args.deepen_domain:
        raise ValueError(
            "targeted deepening requires an active profile; run bounded Ditto setup first"
        )
    if args.deep:
        return build_deep_preflight(result, home, write=write)
    candidate_index = DEFAULT_CANDIDATE_INDEX if args.candidate is None else args.candidate
    return build_preflight(result, home, candidate_index, write=write)

def prepare_plugin_run(args):
    home = resolve_ditto_home(args.ditto_home)
    plan = plugin_plan_for_args(args, write=True)
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
        "mode": "deep" if args.deep else "starter",
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
            payload = {"status": "missing", "ditto_home": home}
        elif args.command == "preflight":
            payload = plugin_plan_for_args(args, write=False)
        elif args.command == "prepare":
            payload = prepare_plugin_run(args)
        elif args.command == "cache-report":
            payload = cache_run_report(args)
        else:
            raise ValueError("unsupported plugin command")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None
    print(json.dumps(payload, sort_keys=True))

def legacy_main():
    ap = argparse.ArgumentParser(description="mine your AI sessions into a model of you")
    ap.add_argument("--source", choices=["auto", "codex", "claude", "copilot"], default="auto")
    ap.add_argument("--path", help="a folder of .jsonl session logs to read instead")
    ap.add_argument("--out", default="ditto-out")
    ap.add_argument("--chunks", type=int, default=20)
    ap.add_argument("--dry-run", action="store_true", help="show counts and output paths without writing files")
    ap.add_argument("--no-redact", action="store_true", help="skip redaction (NOT recommended)")
    ap.add_argument("--no-dedupe", action="store_true", help="keep verbatim-duplicate long messages (re-pasted specs / injected rules)")
    ap.add_argument("--card", nargs="?", const="", metavar="CARD_JSON",
                    help="render your profile card (terminal + card.html) from ditto-out/card.json")
    ap.add_argument("--no-open", action="store_true", help="don't open card.html in the browser")
    ap.add_argument("--install", metavar="PROFILE", help="install an existing generated you.md profile")
    ap.add_argument("--target", choices=["claude", "codex", "cursor", "agents", "gemini"], help="where to install --install")
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
        show_card(args.out, args.card or None, args.no_open)
        return

    roots = []
    if args.path:
        roots = [args.path]
    elif args.source == "auto":
        roots = SOURCES["codex"] + SOURCES["claude"] + SOURCES["copilot"]
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
    legacy_main()

if __name__ == "__main__":
    main()
