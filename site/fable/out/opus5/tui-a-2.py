#!/usr/bin/env python3
"""Static, single-shot deploy report for a 100-column terminal.

Same facts as the original one-liner loop (five steps, their statuses, their
durations, the final result) — laid out so the eye lands on the failure first.
"""

import os
import sys

STEPS = [
    ("install dependencies", "ok", 12.4),
    ("typecheck", "ok", 8.1),
    ("run tests", "failed", 41.7),
    ("build", "skipped", 0.0),
    ("deploy", "skipped", 0.0),
]
RESULT = "failed"

# ---------------------------------------------------------------- layout ---
GLYPH_W, NAME_W, BAR_W, GAP, TIME_W, STATUS_W = 3, 24, 46, 2, 7, 8
RULE_W = GLYPH_W + NAME_W + BAR_W + GAP + TIME_W + GAP + STATUS_W  # 92
MARGIN = "  "

# ----------------------------------------------------------------- style ---
COLOR = os.environ.get("NO_COLOR") is None and os.environ.get("TERM") != "dumb"


def c(text, *codes):
    if not COLOR or not codes:
        return text
    return "\033[" + ";".join(str(n) for n in codes) + "m" + text + "\033[0m"


BOLD, DIM = 1, 2
RED, GREEN, YELLOW, GREY = 31, 32, 33, 90


def _unicode_ok():
    try:
        "█─·✔✖◦═".encode(sys.stdout.encoding or "ascii")
        return True
    except (UnicodeEncodeError, LookupError):
        return False


UNI = _unicode_ok()
FILL = "█" if UNI else "#"
TRACK = "─" if UNI else "-"
DOTS = "·" if UNI else "."
HRULE = "─" if UNI else "-"
TOPRULE = "═" if UNI else "="
ARROW = "→" if UNI else "->"

# glyph, colour, label
STYLE = {
    "ok": ("✔" if UNI else "+", GREEN, "ok"),
    "failed": ("✖" if UNI else "x", RED, "failed"),
    "skipped": ("◦" if UNI else ".", GREY, "skipped"),
}

# ---------------------------------------------------------------- render ---
lines = []
longest = max((s for _, _, s in STEPS), default=0.0) or 1.0
total = sum(s for _, _, s in STEPS)
tally = {"ok": 0, "failed": 0, "skipped": 0}
for _, st, _ in STEPS:
    tally[st] = tally.get(st, 0) + 1

# header: title left, verdict badge right
verdict_plain = " {} {} ".format(STYLE[RESULT][0], RESULT.upper())
verdict = c(verdict_plain, BOLD, 7, STYLE[RESULT][1])
title = c("DEPLOY REPORT", BOLD)
pad = RULE_W - len("DEPLOY REPORT") - len(verdict_plain)
lines.append("")
lines.append(MARGIN + title + " " * max(pad, 1) + verdict)
lines.append(MARGIN + c(TOPRULE * RULE_W, DIM))

# column captions
caption = (
    " " * GLYPH_W
    + "STEP".ljust(NAME_W)
    + "DURATION".ljust(BAR_W + GAP)
    + "SECS".rjust(TIME_W)
    + " " * GAP
    + "STATUS".ljust(STATUS_W)
)
lines.append(MARGIN + c(caption, DIM))
lines.append("")

# one line per step
for name, status, secs in STEPS:
    glyph, color, label = STYLE[status]
    if secs > 0:
        filled = max(1, int(round(secs / longest * BAR_W)))
        bar = c(FILL * filled, color) + c(TRACK * (BAR_W - filled), DIM)
        name_cell = c(name.ljust(NAME_W), BOLD) if status == "failed" else name.ljust(NAME_W)
        time_cell = c("{:.1f}s".format(secs).rjust(TIME_W), color if status == "failed" else 0)
    else:
        bar = c(DOTS * BAR_W, DIM)
        name_cell = c(name.ljust(NAME_W), GREY)
        time_cell = c("{:.1f}s".format(secs).rjust(TIME_W), GREY)
    lines.append(
        MARGIN
        + c(glyph.ljust(GLYPH_W), color)
        + name_cell
        + bar
        + " " * GAP
        + time_cell
        + " " * GAP
        + c(label.ljust(STATUS_W), color)
    )

lines.append("")
lines.append(MARGIN + c(HRULE * RULE_W, DIM))

# footer: counts left, wall clock right
counts = "{} ok  {}  {} failed  {}  {} skipped".format(
    tally["ok"], DOTS, tally["failed"], DOTS, tally["skipped"]
)
counts_colored = (
    c("{} ok".format(tally["ok"]), GREEN)
    + c("  {}  ".format(DOTS), DIM)
    + c("{} failed".format(tally["failed"]), RED, BOLD)
    + c("  {}  ".format(DOTS), DIM)
    + c("{} skipped".format(tally["skipped"]), GREY)
)
elapsed_plain = "{:.1f}s total".format(total)
lines.append(
    MARGIN
    + counts_colored
    + " " * max(RULE_W - len(counts) - len(elapsed_plain), 1)
    + c(elapsed_plain, DIM)
)

# the one sentence a reader actually needs
failed = [n for n, s, _ in STEPS if s == "failed"]
skipped = [n for n, s, _ in STEPS if s == "skipped"]
if failed:
    detail = "{} failed after {:.1f}s".format(
        failed[0], dict((n, x) for n, _, x in STEPS)[failed[0]]
    )
    if skipped:
        detail += "; {} never ran".format(" and ".join(skipped))
    lines.append("")
    lines.append(MARGIN + c(ARROW + " " + detail, STYLE["failed"][1]))
lines.append("")

print("\n".join(lines))
