#!/usr/bin/env python3
"""
ditto — turn your own AI coding sessions into a model of how you think.

It reads your local session logs (Codex / Claude Code / Cursor jsonl), keeps
ONLY the words you typed, redacts secrets + personal info, and writes one
clean corpus + chunks. You then point a coding agent at the chunks with
MINING_PROMPT.md to produce your `you.md`.

100% local. Your logs never leave your machine. No network calls. Stdlib only.

Usage:
    python ditto.py                     # auto-detect Codex + Claude logs
    python ditto.py --dry-run           # preview counts without writing files
    python ditto.py --card              # render your profile card (after mining)
    python ditto.py --install you.md --target codex
    python ditto.py --source codex      # only ~/.codex/sessions
    python ditto.py --path ./logs       # a folder of jsonl you point at
    python ditto.py --chunks 20         # how many chunks to split into
    python ditto.py --no-redact         # DANGER: skip redaction (not recommended)
"""
import argparse, glob, json, os, re, sys

HOME = os.path.expanduser("~")
SOURCES = {
    "codex":  [os.path.join(HOME, ".codex", "sessions")],
    "claude": [os.path.join(HOME, ".claude", "projects")],
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
                if '"role"' not in line and '"user"' not in line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                # Codex: {payload:{type:'message',role:'user',content:[{text}]}}
                # Claude: {type:'user',message:{role:'user',content:'...'|[...]}}
                p = o.get("payload", o)
                msg = p.get("message", p)
                if (p.get("type") == "message" or o.get("type") == "user") and \
                   (p.get("role") == "user" or msg.get("role") == "user"):
                    content = msg.get("content", p.get("content", ""))
                    texts = []
                    if isinstance(content, str):
                        texts = [content]
                    elif isinstance(content, list):
                        texts = [c.get("text", "") for c in content if isinstance(c, dict)]
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

def mine_files(files, no_redact=False):
    sessions = msgs = chars = redactions = 0
    blocks = []
    first_date = last_date = ""
    for f in files:
        ums = user_messages(f)
        if not ums:
            continue
        sessions += 1
        buf = [f"\n===== {os.path.basename(f)} ====="]
        for ts, t in ums:
            if ts:
                if not first_date or ts < first_date:
                    first_date = ts
                if ts > last_date:
                    last_date = ts
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
        "first_date": first_date,
        "last_date": last_date,
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

def write_stats(result, out_dir):
    stats = {
        "sessions": result["sessions"],
        "messages": result["messages"],
        "tokens": result["chars"] // 4,
        "redactions": result["redactions"],
        "first_date": result.get("first_date", ""),
        "last_date": result.get("last_date", ""),
    }
    with open(os.path.join(out_dir, "stats.json"), "w", encoding="utf-8") as w:
        json.dump(stats, w, indent=2)
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
        print("MINING_PROMPT.md into your agent — the reducer emits card.json.")
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
    <div class="laws"><div class="laws-head">laws &middot; ranked by how many of the 20 agents found each</div>{laws}</div>
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
    ap.add_argument("--source", choices=["auto", "codex", "claude"], default="auto")
    ap.add_argument("--path", help="a folder of .jsonl session logs to read instead")
    ap.add_argument("--out", default="ditto-out")
    ap.add_argument("--chunks", type=int, default=20)
    ap.add_argument("--dry-run", action="store_true", help="show counts and output paths without writing files")
    ap.add_argument("--no-redact", action="store_true", help="skip redaction (NOT recommended)")
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
        roots = SOURCES["codex"] + SOURCES["claude"]
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
    write_stats(result, args.out)

    print_counts(result, args.no_redact)
    print(f"wrote: {args.out}/you-corpus.txt  +  {chunk_count} chunks in {args.out}/chunks/")
    print(f"\nnext: open your coding agent, paste MINING_PROMPT.md, point it at {args.out}/chunks/, merge into you.md")

if __name__ == "__main__":
    main()
