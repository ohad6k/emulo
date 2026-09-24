#!/usr/bin/env python3
"""deploy report — a single pass of terminal output, then exit."""

import sys

steps = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]

RESULT = "failed"

# ---------------------------------------------------------------- style

COLOR = sys.stdout.isatty()

TEXT = "38;5;252"
DIM = "38;5;245"
FAINT = "38;5;240"
HEAD = "1;38;5;255"
RED = "38;5;203"
RED_FAINT = "38;5;131"


def c(s, code):
    """wrap in an ansi color, or return it untouched when piped to a file."""
    if not COLOR or not code:
        return s
    return "\x1b[" + code + "m" + s + "\x1b[0m"


def pad(s, n, right=False):
    s = s[:n]
    return s.rjust(n) if right else s.ljust(n)


# ---------------------------------------------------------------- layout

MARGIN = 2
RULE_W = 84
NAME_W = 22
STATUS_W = 9
DUR_W = 7
BAR_W = 34

PAL = {
    "ok": (TEXT, DIM, DIM, "\u2713"),
    "failed": (RED, RED, RED_FAINT, "\u2715"),
    "skipped": (FAINT, FAINT, FAINT, "\u00b7"),
}

pad_l = " " * MARGIN
longest = max(s for _, _, s in steps) or 1.0
total = sum(s for _, _, s in steps)
counts = {}
for _, status, _ in steps:
    counts[status] = counts.get(status, 0) + 1

stopped_at = next((n for n, st, _ in steps if st == "failed"), None)

# ---------------------------------------------------------------- render

out = []
out.append("")

title = "deploy report"
badge = RESULT
gap = RULE_W - len(title) - len(badge)
out.append(
    pad_l
    + c(title, HEAD)
    + " " * max(gap, 1)
    + c(badge, RED if RESULT == "failed" else TEXT)
)
out.append(pad_l + c("\u2500" * RULE_W, FAINT))
out.append("")

for name, status, secs in steps:
    name_c, status_c, bar_c, glyph = PAL[status]

    filled = 0
    if secs > 0:
        filled = max(1, int(round(secs / longest * BAR_W)))
    bar = c("\u2588" * filled, bar_c) + c("\u2500" * (BAR_W - filled), FAINT)

    out.append(
        pad_l
        + c(glyph, bar_c)
        + "  "
        + c(pad(name, NAME_W), name_c)
        + c(pad(status, STATUS_W), status_c)
        + c(pad("%.1fs" % secs, DUR_W, right=True), status_c)
        + "   "
        + bar
    )

out.append("")
out.append(pad_l + c("\u2500" * RULE_W, FAINT))

tally = "   ".join(
    "%d %s" % (counts[k], k) for k in ("ok", "failed", "skipped") if k in counts
)
elapsed = "%.1fs elapsed" % total
gap = RULE_W - len(tally) - len(elapsed)
out.append(pad_l + c(tally, DIM) + " " * max(gap, 1) + c(elapsed, DIM))
out.append("")

line = c(pad("result", 9), DIM) + c(RESULT, RED if RESULT == "failed" else TEXT)
if stopped_at:
    line += c("   stopped at " + stopped_at, DIM)
out.append(pad_l + line)
out.append("")

print("\n".join(out))
