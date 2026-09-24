#!/usr/bin/env python3
"""Deploy report."""

import sys

steps = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

WIDTH = 100
USE_COLOR = sys.stdout.isatty()

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"

STATUS_STYLE = {
    "ok": ("✓", GREEN, "ok"),
    "failed": ("✗", RED, "FAILED"),
    "skipped": ("−", DIM, "skipped"),
}


def paint(text, *codes):
    if not USE_COLOR or not codes:
        return text
    return "".join(codes) + text + RESET


def fmt_secs(secs):
    return f"{secs:.1f}s" if secs else "-"


total = sum(secs for _, _, secs in steps)
failed = [name for name, status, _ in steps if status == "failed"]
skipped = [name for name, status, _ in steps if status == "skipped"]
result = "failed" if failed else "ok"

name_w = max(len(name) for name, _, _ in steps)
label_w = max(len(label) for _, _, label in STATUS_STYLE.values())

print(paint("deploy report", BOLD))
print(paint("─" * WIDTH, DIM))

for i, (name, status, secs) in enumerate(steps, 1):
    icon, color, label = STATUS_STYLE[status]
    line = (
        f"  {i}. "
        f"{paint(icon, color)} "
        f"{name.ljust(name_w)}   "
        f"{paint(label.ljust(label_w), color, BOLD if status == 'failed' else '')}   "
        f"{fmt_secs(secs).rjust(6)}"
    )
    print(line)

print(paint("─" * WIDTH, DIM))

if result == "failed":
    print(
        f"  {paint('result: failed', RED, BOLD)}"
        f"  at step \"{failed[0]}\", {len(skipped)} step(s) not run"
        f"  {paint(f'({total:.1f}s)', DIM)}"
    )
else:
    print(f"  {paint('result: ok', GREEN, BOLD)}  {paint(f'({total:.1f}s)', DIM)}")

sys.exit(1 if result == "failed" else 0)
