#!/usr/bin/env python3
"""Deploy report."""

import sys

WIDTH = 100

steps = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

use_color = sys.stdout.isatty()


def c(code, text):
    return f"\x1b[{code}m{text}\x1b[0m" if use_color else text


BOLD = "1"
DIM = "2"
GREEN = "32"
RED = "31"
YELLOW = "33"

STATUS = {
    "ok":      ("✓", GREEN,  "ok"),
    "failed":  ("✗", RED,    "failed"),
    "skipped": ("-", YELLOW, "skipped"),
}

NAME_W = 24
STATUS_W = 9
DUR_W = 8
total = sum(s for _, _, s in steps)
failed_step = next((n for n, st, _ in steps if st == "failed"), None)

print()
print(c(BOLD, "deploy report"))
print(c(DIM, "─" * WIDTH))

for i, (name, status, secs) in enumerate(steps, 1):
    icon, color, label = STATUS[status]
    dur = f"{secs:.1f}s" if status != "skipped" else "--"
    line = (
        f"  {c(DIM, f'{i}/{len(steps)}')}  "
        f"{c(color, icon)} {name.ljust(NAME_W)}"
        f"{c(color, label.ljust(STATUS_W))}"
        f"{c(DIM, dur.rjust(DUR_W))}"
    )
    print(line)

print(c(DIM, "─" * WIDTH))

ok_n = sum(1 for _, s, _ in steps if s == "ok")
fail_n = sum(1 for _, s, _ in steps if s == "failed")
skip_n = sum(1 for _, s, _ in steps if s == "skipped")

summary = f"{ok_n} ok, {fail_n} failed, {skip_n} skipped"
print(f"  {c(BOLD + ';' + RED, 'RESULT: FAILED')}   {c(DIM, summary)}   {c(DIM, f'total {total:.1f}s')}")
if failed_step:
    print(f"  {c(DIM, 'failed at:')} {failed_step}")
print()

sys.exit(1)
