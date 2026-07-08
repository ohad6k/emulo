#!/usr/bin/env python3
"""
ditto — turn your own AI coding sessions into a model of how you think.

It reads your local session logs (Codex / Claude Code / Copilot CLI jsonl),
keeps ONLY the words you typed, redacts secrets + personal info, and writes one
clean corpus + chunks. You then point a coding agent at the chunks with
MINING_PROMPT.md to produce your `you.md`.

100% local. Your logs never leave your machine. No network calls. Stdlib only.

Usage:
    python ditto.py                     # auto-detect Codex + Claude + Copilot logs
    python ditto.py --dry-run           # preview counts without writing files
    python ditto.py --install you.md --target codex
    python ditto.py --source codex      # only ~/.codex/sessions
    python ditto.py --source copilot    # only ~/.copilot/session-state
    python ditto.py --path ./logs       # a folder of jsonl you point at
    python ditto.py --chunks 20         # how many chunks to split into
    python ditto.py --no-redact         # DANGER: skip redaction (not recommended)
"""
import argparse, glob, json, os, re, sys

HOME = os.path.expanduser("~")
SOURCES = {
    "codex":   [os.path.join(HOME, ".codex", "sessions")],
    "claude":  [os.path.join(HOME, ".claude", "projects")],
    "copilot": [os.path.join(HOME, ".copilot", "session-state")],
}
DITTO_START = "<!-- ditto profile:start -->"
DITTO_END = "<!-- ditto profile:end -->"

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
                    if not t or t.startswith("<"):        # skip env/system injections
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

def mine_files(files, no_redact=False):
    sessions = msgs = chars = redactions = 0
    blocks = []
    for f in files:
        ums = user_messages(f)
        if not ums:
            continue
        sessions += 1
        buf = [f"\n===== {session_label(f)} ====="]
        for ts, t in ums:
            if not no_redact:
                before = t
                t = redact(t)
                if t != before:
                    redactions += 1
            buf.append(f"[{ts}]\n{t}")
            msgs += 1
            chars += len(t)
        blocks.append("\n".join(buf))
    return {
        "sessions": sessions,
        "messages": msgs,
        "chars": chars,
        "redactions": redactions,
        "blocks": blocks,
    }

def write_outputs(blocks, out_dir, chunks):
    os.makedirs(out_dir, exist_ok=True)
    chunks_dir = os.path.join(out_dir, "chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    corpus = "\n".join(blocks)
    with open(os.path.join(out_dir, "you-corpus.txt"), "w", encoding="utf-8") as w:
        w.write(corpus)

    if not blocks:
        return 0

    # split on session boundaries into ~N chunks
    n = max(1, chunks)
    target = max(1, len(corpus) // n)
    cur, size, idx = [], 0, 1
    for b in blocks:
        cur.append(b); size += len(b)
        if size >= target:
            with open(os.path.join(chunks_dir, f"chunk-{idx:02d}.txt"), "w", encoding="utf-8") as w:
                w.write("\n".join(cur))
            idx += 1; cur, size = [], 0
    if cur:
        with open(os.path.join(chunks_dir, f"chunk-{idx:02d}.txt"), "w", encoding="utf-8") as w:
            w.write("\n".join(cur))
        idx += 1
    return idx - 1

def print_counts(result, no_redact=False):
    print(f"sessions: {result['sessions']}")
    print(f"your messages: {result['messages']}")
    print(f"tokens (approx): {result['chars'] // 4:,}")
    print(f"secrets/PII redacted: {result['redactions']}" + ("  (redaction OFF)" if no_redact else ""))

def strip_frontmatter(text):
    if not text.startswith("---\n"):
        return text.strip()
    end = text.find("\n---", 4)
    if end == -1:
        return text.strip()
    return text[end + 4:].strip()

def has_skill_frontmatter(text):
    if not text.startswith("---\n"):
        return False
    end = text.find("\n---", 4)
    if end == -1:
        return False
    head = text[4:end]
    return "name:" in head and "description:" in head

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
        print("profile must start with skill frontmatter for this target: name + description")
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
        body = strip_frontmatter(profile)
        block = f"\n\n{DITTO_START}\n# ditto profile\n\n{body}\n{DITTO_END}\n"
        existing = ""
        if os.path.exists(dest):
            with open(dest, "r", encoding="utf-8", errors="replace") as fh:
                existing = fh.read()
        if DITTO_START in existing and DITTO_END in existing:
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
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(updated.lstrip() if not existing else updated)
        print(f"installed: {dest}")
        return

    if target == "cursor":
        profile = cursor_rule(profile)

    if os.path.exists(dest) and not yes:
        print("destination already exists. pass --yes to overwrite it.")
        sys.exit(1)
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(profile)
    print(f"installed: {dest}")

def main():
    ap = argparse.ArgumentParser(description="mine your AI sessions into a model of you")
    ap.add_argument("--source", choices=["auto", "codex", "claude", "copilot"], default="auto")
    ap.add_argument("--path", help="a folder of .jsonl session logs to read instead")
    ap.add_argument("--out", default="ditto-out")
    ap.add_argument("--chunks", type=int, default=20)
    ap.add_argument("--dry-run", action="store_true", help="show counts and output paths without writing files")
    ap.add_argument("--no-redact", action="store_true", help="skip redaction (NOT recommended)")
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

    roots = []
    if args.path:
        roots = [args.path]
    elif args.source == "auto":
        roots = SOURCES["codex"] + SOURCES["claude"] + SOURCES["copilot"]
    else:
        roots = SOURCES[args.source]

    files = discover_files(roots)
    if not files:
        print("no session logs found. try --path <folder> or --source codex/claude.")
        print("looked in:", ", ".join(roots))
        sys.exit(1)

    result = mine_files(files, args.no_redact)

    if args.dry_run:
        print("dry run: no files written")
        print("looked in:", ", ".join(roots))
        print(f"jsonl files: {len(files)}")
        print_counts(result, args.no_redact)
        print(f"would write: {args.out}/you-corpus.txt  +  chunks in {args.out}/chunks/")
        return

    chunk_count = write_outputs(result["blocks"], args.out, args.chunks)

    print_counts(result, args.no_redact)
    print(f"wrote: {args.out}/you-corpus.txt  +  {chunk_count} chunks in {args.out}/chunks/")
    print(f"\nnext: open your coding agent, paste MINING_PROMPT.md, point it at {args.out}/chunks/, merge into you.md")

if __name__ == "__main__":
    main()
