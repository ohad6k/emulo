#!/usr/bin/env python3
"""deploy report — single-shot terminal summary."""

import sys

steps = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]
result = "failed"

WIDTH = 84
NAME_W = 26
BAR_W = 28
TIME_W = 8
STATUS_W = 8

color = sys.stdout.isatty()


def sgr(code):
    return "\x1b[" + code + "m" if color else ""


RESET = sgr("0")
BOLD = sgr("1")
DIM = sgr("2")
GREEN = sgr("38;5;71")
RED = sgr("38;5;167")
GREY = sgr("38;5;244")
FAINT = sgr("38;5;238")

STYLE = {
    "ok": (GREEN, "\u2713"),
    "failed": (RED, "\u2717"),
    "skipped": (GREY, "\u00b7"),
}

longest = max(s for _, _, s in steps) or 1.0
total = sum(s for _, _, s in steps)
counts = {}
for _, st, _ in steps:
    counts[st] = counts.get(st, 0) + 1

failed_at = next(
    (i for i, (_, st, _) in enumerate(steps, 1) if st == "failed"), None
)

out = []
out.append("")
out.append(BOLD + "deploy" + RESET + DIM + "  report" + RESET)
out.append(FAINT + "\u2500" * WIDTH + RESET)

for i, (name, status, secs) in enumerate(steps, 1):
    tint, mark = STYLE[status]

    index = DIM + str(i).rjust(2) + RESET
    glyph = tint + mark + RESET

    if len(name) > NAME_W:
        name = name[: NAME_W - 1] + "\u2026"
    label = name.ljust(NAME_W)
    if status == "skipped":
        label = GREY + label + RESET
    else:
        label = label + RESET if not color else label

    if secs > 0:
        filled = max(1, round(secs / longest * BAR_W))
        bar = tint + "\u2501" * filled + RESET + FAINT + "\u2501" * (BAR_W - filled) + RESET
    else:
        bar = FAINT + "\u2501" * BAR_W + RESET

    stamp = ("%.1fs" % secs).rjust(TIME_W)
    stamp = (DIM if status == "skipped" else GREY) + stamp + RESET

    word = tint + status.ljust(STATUS_W) + RESET

    out.append("  ".join([index, glyph, label, bar, stamp, word]))

out.append(FAINT + "\u2500" * WIDTH + RESET)

tint = STYLE[result][0]
summary = "%.1fs total" % total
tally = ", ".join(
    "%d %s" % (counts[k], k) for k in ("ok", "failed", "skipped") if k in counts
)

line = (
    "  " + BOLD + tint + "result " + result + RESET
    + DIM + "   " + summary + "   " + tally + RESET
)
out.append(line)

if failed_at:
    out.append(
        "  " + DIM + "stopped at step %d of %d \u00b7 %s" % (
            failed_at, len(steps), steps[failed_at - 1][0]
        ) + RESET
    )

out.append("")
print("\n".join(out))
