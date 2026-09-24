#!/usr/bin/env python3
"""Deploy report — prints a formatted summary of pipeline steps to stdout."""

import os
import sys

WIDTH = 100

steps = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

RESULT = "failed"


def use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty() and os.environ.get("TERM", "") != "dumb"


COLOR = use_color()


def paint(text: str, *codes: str) -> str:
    if not COLOR or not codes:
        return text
    return "\033[" + ";".join(codes) + "m" + text + "\033[0m"


BOLD, DIM = "1", "2"
GREEN, RED, YELLOW, CYAN = "32", "31", "33", "36"

STATUS_STYLE = {
    "ok":      ("✔", "ok",      (GREEN,)),
    "failed":  ("✘", "FAILED",  (RED, BOLD)),
    "skipped": ("–", "skipped", (DIM,)),
}


def fmt_secs(secs: float) -> str:
    if secs <= 0:
        return "—"
    if secs >= 60:
        m, s = divmod(secs, 60)
        return f"{int(m)}m {s:04.1f}s"
    return f"{secs:.1f}s"


def line(text: str = "", indent: int = 2) -> None:
    print(" " * indent + text)


# ---------------------------------------------------------------- header
total = sum(s for _, _, s in steps)
n_ok = sum(1 for _, st, _ in steps if st == "ok")
n_failed = sum(1 for _, st, _ in steps if st == "failed")
n_skipped = sum(1 for _, st, _ in steps if st == "skipped")

print()
line(paint("DEPLOY REPORT", BOLD))
line(paint("─" * (WIDTH - 4), DIM))
print()

# ---------------------------------------------------------------- steps
name_w = max(len(n) for n, _, _ in steps)
label_w = max(len(lbl) for _, lbl, _ in STATUS_STYLE.values())
secs_w = max(len(fmt_secs(s)) for _, _, s in steps)

for i, (name, status, secs) in enumerate(steps, 1):
    icon, label, style = STATUS_STYLE.get(status, ("?", status, ()))
    num = paint(f"{i}/{len(steps)}", DIM)
    name_col = name.ljust(name_w)
    if status == "skipped":
        name_col = paint(name_col, DIM)
    status_col = paint(f"{icon} {label.ljust(label_w)}", *style)
    secs_col = fmt_secs(secs).rjust(secs_w)
    secs_col = paint(secs_col, DIM) if secs <= 0 else secs_col
    line(f"{num}  {name_col}   {status_col}   {secs_col}")

print()

# ---------------------------------------------------------------- summary
first_failure = next((n for n, st, _ in steps if st == "failed"), None)

counts = []
if n_ok:
    counts.append(paint(f"{n_ok} ok", GREEN))
if n_failed:
    counts.append(paint(f"{n_failed} failed", RED))
if n_skipped:
    counts.append(paint(f"{n_skipped} skipped", DIM))

line(paint("─" * (WIDTH - 4), DIM))
if RESULT == "failed":
    result_text = paint("✘ RESULT: FAILED", RED, BOLD)
else:
    result_text = paint("✔ RESULT: OK", GREEN, BOLD)
line(f"{result_text}   {paint('·', DIM)}   {'  '.join(counts)}   {paint('·', DIM)}   total {fmt_secs(total)}")

if first_failure:
    line(paint(f"pipeline stopped at \"{first_failure}\"; later steps were not run", DIM))
print()

sys.exit(1 if RESULT == "failed" else 0)
