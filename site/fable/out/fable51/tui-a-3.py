#!/usr/bin/env python3
import sys

steps = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

WIDTH = 100
COLOR = sys.stdout.isatty()

def c(code, s):
    return f"\033[{code}m{s}\033[0m" if COLOR else s

BOLD, DIM = "1", "2"
GREEN, RED, YELLOW = "32", "31", "33"

STYLE = {
    "ok":      ("✔", GREEN,  "ok"),
    "failed":  ("✘", RED,    "FAILED"),
    "skipped": ("–", YELLOW, "skipped"),
}

def fmt_secs(secs):
    return f"{secs:5.1f}s" if secs > 0 else "     –"

name_w = max(len(n) for n, _, _ in steps)
total = sum(s for _, _, s in steps)
n_ok = sum(1 for _, s, _ in steps if s == "ok")
n_failed = sum(1 for _, s, _ in steps if s == "failed")
n_skipped = sum(1 for _, s, _ in steps if s == "skipped")
overall = "failed" if n_failed else "ok"

print()
print(c(BOLD, "  Deploy report"))
print(c(DIM, "  " + "─" * (WIDTH - 4)))
print()

for i, (name, status, secs) in enumerate(steps, 1):
    icon, color, label = STYLE[status]
    line = (
        f"  {c(DIM, f'{i}/{len(steps)}')}  "
        f"{c(color, icon)}  "
        f"{name.ljust(name_w)}   "
        f"{c(color, label.ljust(7))}   "
        f"{c(DIM, fmt_secs(secs))}"
    )
    if status == "skipped":
        line += c(DIM, "   (previous step failed)")
    print(line)

print()
print(c(DIM, "  " + "─" * (WIDTH - 4)))
summary = (
    f"{c(GREEN, f'{n_ok} ok')}  ·  "
    f"{c(RED, f'{n_failed} failed')}  ·  "
    f"{c(YELLOW, f'{n_skipped} skipped')}  ·  "
    f"{c(DIM, f'{total:.1f}s total')}"
)
print(f"  {summary}")
print()
if overall == "failed":
    print(f"  {c(BOLD + ';' + RED, '✘ Result: FAILED')}  {c(DIM, '— deploy aborted at "run tests"')}")
else:
    print(f"  {c(BOLD + ';' + GREEN, '✔ Result: ok')}")
print()
